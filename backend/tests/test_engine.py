from app.engine.scoring import (
    get_weights,
    hard_filter,
    load_crops,
    pick_three,
    rotation_score,
    soil_score,
    temp_score,
    water_score,
)


def test_rotation_fixer_after_heavy_feeder():
    heavy_crop = {"name": "paddy", "family": "Poaceae", "n_effect": "heavy", "repeat_penalty": 15}
    fixer_crop = {"name": "green_gram", "family": "Fabaceae", "n_effect": "fixer", "repeat_penalty": 40}

    history = [{"crop": "paddy", "family": "Poaceae", "n_effect": "heavy"}]
    score_heavy = rotation_score(heavy_crop, history, dry_outlook=False)
    score_fixer = rotation_score(fixer_crop, history, dry_outlook=False)

    assert score_fixer > score_heavy


def test_water_score_dry_vs_wet():
    crop = {"need_mm": 1200, "drought_tol": "L", "waterlog_tol": "H"}
    field = {"water_source": "rainfed", "flood_prone": False}

    score_dry = water_score(crop, field, eff_rain=200.0, rain_factor=0.8)
    score_wet = water_score(crop, field, eff_rain=1000.0, rain_factor=1.0)

    assert score_wet > score_dry


def test_weights_sum_to_100():
    w = get_weights(dry_outlook=True, toggle="earn_more")
    assert round(sum(w.values()), 1) == 100.0


def test_red_flag_veto_rule():
    """Verify red flag veto rule: crops with any factor < 40 are excluded from Cards 2 & 3,
    while Card 1 preserves the customary crop regardless of red flags.
    """
    # Crop 1: Customary crop with a red flag (water score < 40)
    crop1 = {
        "name": "paddy",
        "family": "Poaceae",
        "duration_days": 135,
        "need_mm": 1500,
        "drought_tol": "L",
        "waterlog_tol": "H",
        "n_effect": "heavy",
        "ph_min": 5.0,
        "ph_max": 6.5,
        "t_min": 20.0,
        "t_max": 38.0,
        "t_flower_max": 35.0,
        "flower_frac": (0.5, 0.7),
        "start_windows": [(1, 52)],
        "elev_min": -10.0,
        "elev_max": 1500.0,
        "repeat_penalty": 15,
        "market": "msp",
    }
    # Crop 2: High scoring overall, but has a RED FLAG on rotation (e.g. repeated vegetable)
    crop2 = {
        "name": "chili",
        "family": "Solanaceae",
        "duration_days": 90,
        "need_mm": 400,
        "drought_tol": "H",
        "waterlog_tol": "M",
        "n_effect": "heavy",
        "ph_min": 5.0,
        "ph_max": 7.0,
        "t_min": 20.0,
        "t_max": 38.0,
        "t_flower_max": 36.0,
        "flower_frac": (0.4, 0.6),
        "start_windows": [(1, 52)],
        "elev_min": -10.0,
        "elev_max": 1500.0,
        "repeat_penalty": 45,  # 80 - 45 = 35 -> Red Flag (< 40)
        "market": "high_demand",
    }
    # Crop 3: Moderate scoring, NO red flags
    crop3 = {
        "name": "green_gram",
        "family": "Fabaceae",
        "duration_days": 70,
        "need_mm": 400,
        "drought_tol": "H",
        "waterlog_tol": "M",
        "n_effect": "fixer",
        "ph_min": 5.0,
        "ph_max": 7.5,
        "t_min": 20.0,
        "t_max": 38.0,
        "t_flower_max": 38.0,
        "flower_frac": (0.4, 0.6),
        "start_windows": [(1, 52)],
        "elev_min": -10.0,
        "elev_max": 1500.0,
        "repeat_penalty": 40,
        "market": "msp",
    }
    # Crop 4: Moderate scoring, NO red flags, different family
    crop4 = {
        "name": "sesame",
        "family": "Pedaliaceae",
        "duration_days": 85,
        "need_mm": 450,
        "drought_tol": "H",
        "waterlog_tol": "M",
        "n_effect": "neutral",
        "ph_min": 5.0,
        "ph_max": 8.0,
        "t_min": 20.0,
        "t_max": 38.0,
        "t_flower_max": 36.0,
        "flower_frac": (0.4, 0.6),
        "start_windows": [(1, 52)],
        "elev_min": -10.0,
        "elev_max": 1500.0,
        "repeat_penalty": 30,
        "market": "medium",
    }

    env = {
        "field": {"elevation_m": 4.0, "flood_prone": False, "soil_ph": 6.0, "water_source": "rainfed"},
        "history": [{"crop": "chili", "family": "Solanaceae", "n_effect": "heavy"}],
        "normals": {
            "rain": [35.0] * 52,  # paddy water score < 40 (red flag), pulses have adequate rain
            "tmean": [27.0] * 52,
            "tmax": [32.0] * 52,
        },
        "start_week": 2,
        "next_week": 25,
        "outlook_factor": 0.8,
        "dry_outlook": True,
        "weights": get_weights(),
    }

    crops = [crop1, crop2, crop3, crop4]
    cards = pick_three(crops, env, existing_name="paddy")

    # Card 1 is customary crop (paddy) despite poor/red score
    assert cards[0]["crop"] == "paddy"
    assert cards[0]["factors"]["water"] < 40  # verified red flag
    assert "water" in cards[0]["red"]

    # Crop 2 (chili) has rotation factor < 40 (red flag) -> strictly barred from Cards 2 & 3
    card_crops = [c["crop"] for c in cards[1:]]
    assert "chili" not in card_crops
    assert "green_gram" in card_crops
    assert "sesame" in card_crops


def test_slider_rainfall_monotonicity():
    """Verify that as rainfall increases under normal conditions, water score increases monotonically."""
    crop = {"need_mm": 600, "drought_tol": "M", "waterlog_tol": "M"}
    field = {"water_source": "rainfed", "flood_prone": False, "water_quality": "good"}

    eff_rains = [50.0, 100.0, 150.0, 200.0, 300.0, 450.0, 600.0, 800.0, 1200.0]
    scores = [water_score(crop, field, eff_rain=r, rain_factor=1.0) for r in eff_rains]

    for i in range(1, len(scores)):
        assert scores[i] >= scores[i - 1], f"Monotonicity violated: {scores[i]} < {scores[i-1]} at rain={eff_rains[i]}"


def test_waterlogging_and_salinity_penalties():
    crop = {"need_mm": 500, "drought_tol": "M", "waterlog_tol": "L", "salinity_tol": "L"}
    field_flood = {"water_source": "rainfed", "flood_prone": True, "water_quality": "good"}

    score_normal = water_score(crop, field_flood, eff_rain=400.0, rain_factor=1.0)
    score_flood_high_rain = water_score(crop, field_flood, eff_rain=400.0, rain_factor=1.2)
    # 25-point penalty under rain_factor >= 1.15 in flood-prone field with Low tolerance
    assert score_normal - score_flood_high_rain == 25.0

    field_saline = {"water_source": "rainfed", "flood_prone": False, "water_quality": "saline"}
    score_saline_low_tol = water_score(crop, field_saline, eff_rain=400.0, rain_factor=1.0)
    assert score_normal - score_saline_low_tol == 20.0


def test_rotation_history_penalties():
    crop = {
        "name": "paddy",
        "family": "Poaceae",
        "repeat_penalty": 15,
        "n_effect": "heavy",
        "water_need": "high",
    }

    # Base score without history
    assert rotation_score(crop, []) == 80.0

    # Repeat penalty (paddy = 15)
    hist_one = [{"crop": "paddy", "family": "Poaceae", "n_effect": "heavy"}]
    # 80 - 15 (repeat) - 20 (heavy after heavy) = 45
    assert rotation_score(crop, hist_one) == 45.0

    # Streak: 3 times in a row -> additional -15
    hist_three = [
        {"crop": "paddy", "family": "Poaceae", "n_effect": "heavy"},
        {"crop": "paddy", "family": "Poaceae", "n_effect": "heavy"},
    ]
    # 80 - 15 (repeat) - 15 (streak) - 20 (heavy after heavy) - 10 (same family 2nd-to-last) = 20
    assert rotation_score(crop, hist_three) == 20.0

    # Failure due to verified pest/disease in same family: -20
    hist_failed_pest = [{
        "crop": "maize",
        "family": "Poaceae",
        "n_effect": "heavy",
        "outcome": "failed",
        "approval_status": "approved",
        "approved_cause": "stem borer pest",
    }]
    # 80 - 25 (same family last season) - 20 (heavy after heavy) - 20 (verified pest failure) = 15
    assert rotation_score(crop, hist_failed_pest) == 15.0

    # Failure due to water stress with dry outlook: -10
    hist_failed_water = [{
        "crop": "sesame",
        "family": "Pedaliaceae",
        "n_effect": "neutral",
        "outcome": "failed",
        "cause_approved": True,
        "cause": "water_stress",
    }]
    # 80 - 10 (water stress failure with dry outlook) = 70
    assert rotation_score(crop, hist_failed_water, dry_outlook=True) == 70.0


def test_stage1_hard_filters():
    crop = {
        "name": "tapioca",
        "duration_days": 300,
        "elev_min": 0.0,
        "elev_max": 800.0,
        "t_min": 20.0,
        "t_max": 35.0,
        "start_windows": [(15, 25)],
        "long_duration": 1,
    }

    # Elevation outside range
    field_high = {"elevation_m": 1200.0}
    cls, reasons = hard_filter(crop, field_high, start_week=18, next_week=40, tmean=[25.0] * 10)
    assert cls == "not_suitable"
    assert "elevation outside crop range" in reasons

    # Temperature outside range by > 3 °C -> not_suitable
    field_ok = {"elevation_m": 100.0}
    cls, reasons = hard_filter(crop, field_ok, start_week=18, next_week=40, tmean=[15.0] * 10)
    assert cls == "not_suitable"
    assert "temperature outside crop range" in reasons

    # Temperature outside range by <= 3 °C -> marginal
    cls, reasons = hard_filter(crop, field_ok, start_week=18, next_week=40, tmean=[18.0] * 10)
    assert cls == "marginal"
    assert "temperature slightly outside range" in reasons

    # Start week distance > 4 weeks -> not_suitable
    cls, reasons = hard_filter(crop, field_ok, start_week=35, next_week=40, tmean=[25.0] * 10)
    assert cls == "not_suitable"
    assert "start week outside crop season" in reasons

    # Long duration crop skips next season overlap check
    cls, reasons = hard_filter(crop, field_ok, start_week=18, next_week=22, tmean=[25.0] * 10)
    assert cls == "suitable"


def test_temperature_flowering_heat_penalty():
    crop = {
        "t_min": 18.0,
        "t_max": 36.0,
        "t_flower_max": 33.0,
        "flower_frac": (0.4, 0.6),
    }
    tmean = [25.0] * 10
    tmax_cool = [30.0] * 10
    tmax_heat = [30.0] * 10
    tmax_heat[5] = 35.0  # week 5 is in flowering window (4..6)

    score_cool = temp_score(crop, tmean, tmax_cool, offset=0.0)
    score_heat = temp_score(crop, tmean, tmax_heat, offset=0.0)

    assert score_cool == 100.0
    assert score_heat == 70.0  # -30 penalty


def test_soil_fit_and_benefit():
    crop = {
        "ph_min": 6.0,
        "ph_max": 7.0,
        "waterlog_tol": "H",
        "n_effect": "fixer",
        "om_bonus": True,
        "erosion_cover": True,
        "duration_days": 60,
    }

    field = {
        "soil_ph": 6.5,
        "flood_prone": True,
        "drainage": "poor",
        "slope": "medium",
    }

    # pH fit = 100, drainage fit = 100 (High tol in flood) -> fit = 100
    # Benefit: fixer = 100, capped at 100
    # Final = 0.5 * 100 + 0.5 * 100 = 100
    score = soil_score(crop, field, bare_gap_days=70)
    assert score == 100.0

    # Test heavy feeder with pH outside by 0.4
    crop_heavy = {
        "ph_min": 6.0,
        "ph_max": 7.0,
        "waterlog_tol": "L",
        "n_effect": "heavy",
        "om_bonus": False,
        "erosion_cover": False,
        "duration_days": 120,
    }
    field_acidic = {"soil_ph": 5.6, "flood_prone": False, "drainage": "good"}
    # pH fit = 70 (outside by 0.4 <= 0.5), drain_fit = 100 -> fit = 85
    # benefit = 30
    # Final = 0.5 * 85 + 0.5 * 30 = 57.5
    assert soil_score(crop_heavy, field_acidic, bare_gap_days=0) == 57.5


def test_worst_case_robustness_ranking_in_5pt_band():
    """Verify that within a 5-point total score band, crops are ranked by their lowest score across 4 stress scenarios."""
    # Crop A: total score ~82, but very resilient (worst ~78)
    cropA = {
        "name": "resilient_pulse",
        "family": "Fabaceae",
        "duration_days": 70,
        "need_mm": 400,
        "drought_tol": "H",
        "waterlog_tol": "H",
        "n_effect": "fixer",
        "ph_min": 5.0,
        "ph_max": 7.5,
        "t_min": 15.0,
        "t_max": 42.0,
        "t_flower_max": 40.0,
        "flower_frac": (0.4, 0.6),
        "start_windows": [(1, 52)],
        "elev_min": -10.0,
        "elev_max": 1500.0,
        "repeat_penalty": 30,
        "market": "msp",
    }
    # Crop B: total score ~84, but vulnerable to heat stress (worst ~62)
    cropB = {
        "name": "vulnerable_crop",
        "family": "Pedaliaceae",
        "duration_days": 70,
        "need_mm": 400,
        "drought_tol": "M",
        "waterlog_tol": "M",
        "n_effect": "neutral",
        "ph_min": 5.0,
        "ph_max": 7.5,
        "t_min": 15.0,
        "t_max": 42.0,
        "t_flower_max": 33.0,  # Heat stress penalty in temp + 2.0 scenario!
        "flower_frac": (0.4, 0.6),
        "start_windows": [(1, 52)],
        "elev_min": -10.0,
        "elev_max": 1500.0,
        "repeat_penalty": 30,
        "market": "high_demand",
    }
    crop_customary = {
        "name": "customary_paddy",
        "family": "Poaceae",
        "duration_days": 120,
        "need_mm": 1200,
        "drought_tol": "L",
        "waterlog_tol": "H",
        "n_effect": "heavy",
        "ph_min": 5.0,
        "ph_max": 7.0,
        "t_min": 20.0,
        "t_max": 38.0,
        "t_flower_max": 36.0,
        "flower_frac": (0.5, 0.7),
        "start_windows": [(1, 52)],
        "elev_min": -10.0,
        "elev_max": 1500.0,
        "repeat_penalty": 15,
        "market": "msp",
    }

    env = {
        "field": {"elevation_m": 4.0, "flood_prone": False, "soil_ph": 6.5, "water_source": "canal"},
        "history": [],
        "normals": {
            "rain": [80.0] * 52,
            "tmean": [27.0] * 52,
            "tmax": [32.0] * 52,  # in temp + 2 scenario, tmax becomes 34.0 > 33.0
        },
        "start_week": 2,
        "next_week": 20,
        "outlook_factor": 1.0,
        "dry_outlook": False,
        "weights": get_weights(),
    }

    cards = pick_three([crop_customary, cropB, cropA], env, existing_name="customary_paddy")
    # Card 2 should be resilient_pulse because within 5 points of vulnerable_crop, its worst score is higher
    assert cards[1]["crop"] == "resilient_pulse"
    assert cards[1]["worst"] > cards[2]["worst"]


def test_holds_up_best_badge():
    """Verify holds_up_best badge is awarded when worst-case score leads runner-up by >= 5 points and has no red flag."""
    crops = load_crops()
    env = {
        "field": {"elevation_m": 4.0, "flood_prone": False, "soil_ph": 6.0, "water_source": "borewell"},
        "history": [{"crop": "paddy", "family": "Poaceae", "n_effect": "heavy"}],
        "normals": {
            "rain": [60.0] * 52,
            "tmean": [26.0] * 52,
            "tmax": [31.0] * 52,
        },
        "start_week": 2,
        "next_week": 20,
        "outlook_factor": 1.0,
        "dry_outlook": False,
        "weights": get_weights(),
    }

    cards = pick_three(crops, env, existing_name="paddy")
    assert len(cards) == 3

    # Ensure at most one card has holds_up_best == True
    robust_cards = [c for c in cards if c.get("holds_up_best")]
    assert len(robust_cards) <= 1
    if robust_cards:
        badge_card = robust_cards[0]
        other_cards = [c for c in cards if c != badge_card]
        assert not badge_card.get("red")
        assert badge_card["worst"] - max(c["worst"] for c in other_cards) >= 5.0
