from app.engine.scoring import (
    load_crops,
    get_weights,
    water_score,
    rotation_score,
    evaluate,
    pick_three,
    verdict,
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
