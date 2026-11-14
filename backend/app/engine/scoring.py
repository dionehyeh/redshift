"""Field Shift deterministic rotation evaluation engine (Section 14 & 23.2).
Pure Python logic implementing hard filters, factor scoring, and card ranking.
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

TOL = {"L": 0, "LOW": 0, "M": 1, "MED": 1, "MEDIUM": 1, "H": 2, "HIGH": 2}
IRRIGATION_SHARE = {"rainfed": 0.0, "borewell": 0.6, "canal": 0.8, "unknown": 0.0}
EFFECTIVE_RAIN = 0.75

MARKET = {
    "high_demand": 85.0,
    "high": 85.0,
    "high_local_demand": 85.0,
    "msp": 80.0,
    "msp_supported": 80.0,
    "medium": 60.0,
    "medium_demand": 60.0,
    "few_buyers": 60.0,
    "variable": 50.0,
    "unknown": 50.0,
    "limited": 30.0,
    "limited_buyers": 30.0,
}

BASE_W = {
    "water": 30.0,
    "rotation": 25.0,
    "temp": 15.0,
    "soil": 15.0,
    "market": 10.0,
    "timing": 5.0,
}

STRESS = [
    {"rain": 0.8, "temp": 0.0},
    {"rain": 1.2, "temp": 0.0},
    {"rain": 1.0, "temp": 2.0},
    {"rain": 0.8, "temp": 2.0},
]

FACTOR_TO_MESSAGE = {
    "water": "arrange_irrigation",
    "rotation": "rotate_family",
    "temp": "shift_planting",
    "soil": "test_soil",
    "market": "check_price",
    "timing": "check_overlap",
}


def clamp(x: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, float(x)))


def _tol_val(val: Any, default: int = 1) -> int:
    if isinstance(val, (int, float)):
        return int(val)
    if isinstance(val, str):
        return TOL.get(val.strip().upper(), default)
    return default


def get_weights(dry_outlook: bool = False, toggle: str | None = None) -> dict[str, float]:
    w = dict(BASE_W)
    if dry_outlook:
        w["water"] += 10.0
        w["market"] -= 5.0
        w["soil"] -= 5.0
    if toggle:
        t = toggle.lower().replace("-", "_").strip()
        if t == "earn_more":
            w["market"] += 10.0
            w["water"] -= 5.0
            w["rotation"] -= 5.0
        elif t == "play_safe":
            w["market"] -= 5.0
            w["water"] += 5.0
    w = {k: max(v, 3.0) for k, v in w.items()}
    total = sum(w.values())
    return {k: round(v * 100.0 / total, 2) for k, v in w.items()}


def week_dist(w: int, a: int, b: int) -> int:
    inside = (a <= w <= b) if a <= b else (w >= a or w <= b)
    if inside:
        return 0
    d = lambda x, y: min((x - y) % 52, (y - x) % 52)
    return min(d(w, a), d(w, b))


def overlap_days(crop: dict, start_week: int, next_week: int) -> int:
    if crop.get("long_duration"):
        return 0
    nxt = next_week if next_week > start_week else next_week + 52
    duration = int(crop.get("duration_days", 90))
    return max(0, duration - (nxt - start_week) * 7)


def window_ctx(crop: dict, normals: dict, start_week: int, sc: dict, outlook_factor: float) -> dict:
    duration = int(crop.get("duration_days", 90))
    n = max(1, round(duration / 7))
    idx = [(start_week - 1 + i) % 52 for i in range(n)]
    rain_list = normals.get("rain", [50.0] * 52)
    tmean_list = normals.get("tmean", [27.0] * 52)
    tmax_list = normals.get("tmax", [32.0] * 52)

    rain = sum(rain_list[i] for i in idx) * float(outlook_factor) * float(sc.get("rain", 1.0)) * EFFECTIVE_RAIN
    return {
        "rain": rain,
        "tmean": [tmean_list[i] for i in idx],
        "tmax": [tmax_list[i] for i in idx],
    }


def hard_filter(crop: dict, field: dict, start_week: int, next_week: int, tmean: list[float]) -> tuple[str, list[str]]:
    reasons: list[str] = []
    is_not_suitable = False
    is_marginal = False

    # Elevation filter
    elev = field.get("elevation_m")
    if elev is not None and "elev_min" in crop and "elev_max" in crop:
        elev_val = float(elev)
        if not (float(crop["elev_min"]) <= elev_val <= float(crop["elev_max"])):
            is_not_suitable = True
            reasons.append("elevation outside crop range")

    # Temperature filter
    if tmean and "t_min" in crop and "t_max" in crop:
        avg_t = sum(tmean) / len(tmean)
        t_min = float(crop["t_min"])
        t_max = float(crop["t_max"])
        gap = max(t_min - avg_t, avg_t - t_max, 0.0)
        if gap > 3.0:
            is_not_suitable = True
            reasons.append("temperature outside crop range")
        elif gap > 0.0:
            is_marginal = True
            reasons.append("temperature slightly outside range")

    # Start Window filter
    windows = crop.get("start_windows", [])
    if windows:
        dist = min(week_dist(start_week, a, b) for a, b in windows)
        if dist > 4:
            is_not_suitable = True
            reasons.append("start week outside crop season")
        elif dist > 0:
            is_marginal = True
            reasons.append("start week near the edge of the season")

    # Overlap / Duration filter
    if not crop.get("long_duration"):
        ov = overlap_days(crop, start_week, next_week)
        if ov > 30:
            is_not_suitable = True
            reasons.append("does not finish before the next season")
        elif ov > 0:
            is_marginal = True
            reasons.append("overlaps the next season slightly")

    if is_not_suitable:
        return "not_suitable", reasons
    if is_marginal:
        return "marginal", reasons
    return "suitable", reasons


def water_score(crop: dict, field: dict, eff_rain: float, rain_factor: float = 1.0, stored_mm: float = 0.0) -> float:
    need = max(1.0, float(crop.get("need_mm", 1)))
    avail = max(0.0, float(eff_rain)) + max(0.0, float(stored_mm))
    gap = max(0.0, need - avail)
    water_source = field.get("water_source", "rainfed")
    irr_share = IRRIGATION_SHARE.get(water_source, 0.0)
    supply = avail + (irr_share * gap)
    d_tol = _tol_val(crop.get("drought_tol", "M"), 1)
    ratio = (supply / need) * (1.0 + 0.15 * d_tol)
    score = clamp((ratio - 0.3) / 0.5 * 100.0)

    # Waterlogging penalty: -25 if slider rain >= 1.15, flood-prone, low tolerance
    w_tol = str(crop.get("waterlog_tol", "M")).strip().upper()
    is_flood = bool(field.get("flood_prone"))
    if float(rain_factor) >= 1.15 and is_flood and (w_tol == "L" or w_tol.startswith("LOW")):
        score -= 25.0

    # Salinity penalty: -20 for Low tolerance, -10 for Medium tolerance if water quality is saline
    w_qual = str(field.get("water_quality", "unknown")).strip().lower()
    if w_qual == "saline":
        s_tol = str(crop.get("salinity_tol", "M")).strip().upper()
        if s_tol == "L" or s_tol.startswith("LOW"):
            score -= 20.0
        elif s_tol == "M" or s_tol.startswith("MED"):
            score -= 10.0

    return clamp(score)


def rotation_score(crop: dict, history: list[dict], dry_outlook: bool = False) -> float:
    s = 80.0
    if not history:
        return clamp(s)

    last = history[0]
    last_crop = last.get("crop") or last.get("crop_name") or last.get("name")
    last_fam = last.get("family") or last.get("crop_family")
    crop_name = crop.get("name")
    crop_fam = crop.get("family")

    # Repeat crop vs family penalties
    if crop_name and last_crop and crop_name == last_crop:
        s -= float(crop.get("repeat_penalty", 25))
        streak = 0
        for h in history:
            h_crop = h.get("crop") or h.get("crop_name") or h.get("name")
            if h_crop == crop_name:
                streak += 1
            else:
                break
        if streak >= 2:
            s -= 15.0
    elif crop_fam and last_fam and crop_fam == last_fam:
        s -= 25.0

    # Same family as 2nd-to-last season
    if len(history) > 1:
        prev2 = history[1]
        prev2_fam = prev2.get("family") or prev2.get("crop_family")
        if crop_fam and prev2_fam and crop_fam == prev2_fam:
            s -= 10.0

    # Nitrogen feeder/fixer interactions
    last_n = last.get("n_effect")
    crop_n = crop.get("n_effect")
    if last_n == "heavy" and crop_n == "heavy":
        s -= 20.0
    elif last_n == "heavy" and crop_n == "fixer":
        s += 15.0
    elif last_n == "fixer" and crop_n == "heavy":
        s += 10.0

    # Pest/disease & water stress failure checks
    is_approved = (last.get("cause_approved") is True) or (last.get("approval_status") in ("approved", "corrected"))
    cause = str(last.get("approved_cause") or last.get("cause") or (last.get("suspected_cause") if is_approved else "")).lower()
    is_failed = (
        (last.get("outcome") in ("poor", "failed"))
        or (last.get("loss_percent") is not None and float(last.get("loss_percent")) >= 40)
        or (last.get("outcome") is None and is_approved)
    )

    if is_failed and is_approved:
        if crop_fam and last_fam and crop_fam == last_fam and any(k in cause for k in ("pest", "disease")):
            s -= 20.0
        if (
            ("water_stress" in cause or "drought" in cause or cause == "water")
            and dry_outlook
            and (crop.get("water_need") in ("high", "very_high", None) or crop.get("need_mm", 0) > 600)
        ):
            s -= 10.0

    return clamp(s)


def temp_score(crop: dict, tmean: list[float], tmax: list[float], offset: float = 0.0) -> float:
    if not tmean:
        return 100.0
    n = len(tmean)
    t_min = float(crop.get("t_min", 15.0))
    t_max = float(crop.get("t_max", 38.0))
    ok = sum(1 for t in tmean if t_min <= (t + offset) <= t_max)
    score = 100.0 * ok / n

    frac = crop.get("flower_frac")
    if frac:
        a, b = frac
    else:
        a = float(crop.get("flower_frac_start", 0.4))
        b = float(crop.get("flower_frac_end", 0.6))
    start_idx = int(a * n)
    end_idx = max(int(b * n) + 1, start_idx + 1)
    t_flower_max = float(crop.get("t_flower_max", t_max))

    if any((tmax[i] + offset) > t_flower_max for i in range(start_idx, min(end_idx, len(tmax)))):
        score -= 30.0

    return clamp(score)


def soil_score(crop: dict, field: dict, bare_gap_days: int = 0) -> float:
    ph = field.get("ph") if field.get("ph") is not None else field.get("soil_ph")
    if ph is None:
        ph_fit = 60.0
    else:
        ph_val = float(ph)
        ph_min = float(crop.get("ph_min", 6.0))
        ph_max = float(crop.get("ph_max", 7.5))
        d = max(ph_min - ph_val, ph_val - ph_max, 0.0)
        if d == 0.0:
            ph_fit = 100.0
        elif d <= 0.5:
            ph_fit = 70.0
        else:
            ph_fit = 40.0

    drain_fit = 100.0
    is_flood = bool(field.get("flood_prone"))
    drainage = str(field.get("drainage", "")).lower()
    if is_flood or drainage in ("poor", "very_poor"):
        w_tol = str(crop.get("waterlog_tol", "M")).strip().upper()
        if w_tol == "H" or w_tol.startswith("HIGH"):
            drain_fit = 100.0
        elif w_tol == "L" or w_tol.startswith("LOW"):
            drain_fit = 40.0
        else:
            drain_fit = 70.0

    fit = (ph_fit + drain_fit) / 2.0

    n_effect = str(crop.get("n_effect", "neutral")).lower()
    if n_effect == "fixer":
        benefit = 100.0
    elif n_effect == "heavy":
        benefit = 30.0
    else:
        benefit = 60.0

    if crop.get("om_bonus"):
        benefit += 10.0

    slope = field.get("slope", "low")
    on_slope = False
    if isinstance(slope, (int, float)):
        on_slope = slope > 3.0
    elif isinstance(slope, str):
        on_slope = slope.lower() not in ("low", "flat", "none", "0", "")
    if crop.get("erosion_cover") and on_slope:
        benefit += 10.0

    dur = int(crop.get("duration_days", 90))
    if bare_gap_days >= 40 and dur <= bare_gap_days:
        benefit += 10.0

    benefit = clamp(benefit, 0.0, 100.0)
    return clamp(0.5 * fit + 0.5 * benefit)


def market_score(crop: dict) -> float:
    m = str(crop.get("market", "variable")).lower().strip()
    return float(MARKET.get(m, 50.0))


def timing_score(crop: dict, start_week: int, next_week: int) -> float:
    if crop.get("long_duration"):
        return 100.0
    ov = overlap_days(crop, start_week, next_week)
    if ov == 0:
        return 100.0
    if ov <= 14:
        return 60.0
    if ov <= 30:
        return 30.0
    return 0.0


def evaluate(crop: dict, env: dict, scenario: dict | None = None) -> dict:
    sc = scenario or env.get("scenario") or {"rain": 1.0, "temp": 0.0}
    start_w = env.get("start_week", 1)
    next_w = env.get("next_week", 20)
    outlook_factor = float(env.get("outlook_factor", 1.0))
    normals = env.get("normals") or {
        "rain": [50.0] * 52,
        "tmean": [27.0] * 52,
        "tmax": [32.0] * 52,
    }

    ctx = window_ctx(crop, normals, start_w, sc, outlook_factor)
    cls, reasons = hard_filter(crop, env.get("field", {}), start_w, next_w, ctx["tmean"])

    stored_mm = float(env.get("stored_mm", 0.0))
    dry_outlook = bool(env.get("dry_outlook", (outlook_factor < 0.9)))
    bare_gap = int(env.get("bare_gap_days", 0))

    f = {
        "water": round(water_score(crop, env.get("field", {}), ctx["rain"], float(sc.get("rain", 1.0)), stored_mm), 1),
        "rotation": round(rotation_score(crop, env.get("history", []), dry_outlook), 1),
        "temp": round(temp_score(crop, ctx["tmean"], ctx["tmax"], float(sc.get("temp", 0.0))), 1),
        "soil": round(soil_score(crop, env.get("field", {}), bare_gap), 1),
        "market": round(market_score(crop), 1),
        "timing": round(timing_score(crop, start_w, next_w), 1),
    }

    w = env.get("weights") or get_weights(dry_outlook=dry_outlook, toggle=env.get("toggle"))
    total = sum(w[k] * f[k] / 100.0 for k in w)

    colors = {}
    for k, v in f.items():
        if v >= 65:
            colors[k] = "green"
        elif v >= 40:
            colors[k] = "amber"
        else:
            colors[k] = "red"

    red_flags = [k for k, v in f.items() if v < 40]
    amber_flags = [k for k, v in f.items() if 40 <= v < 65]

    return {
        "crop": crop["name"],
        "family": crop.get("family", "Unknown"),
        "cls": cls,
        "reasons": reasons,
        "factors": f,
        "colors": colors,
        "total": round(total, 1),
        "red": red_flags,
        "amber": amber_flags,
    }


def verdict(e: dict) -> str:
    if e.get("cls") == "not_suitable" or e.get("total", 0.0) < 45.0:
        return "Not suited this season"
    if e.get("cls") == "marginal" or e.get("total", 0.0) < 70.0 or e.get("red"):
        return "Possible with risk"
    return "Feasible"


def pick_three(crops: list[dict], env: dict, existing_name: str) -> list[dict]:
    # 1. Evaluate all crops under baseline and the 4 stress scenarios
    ev: dict[str, dict] = {}
    for c in crops:
        base_eval = evaluate(c, env)
        worst_score = min(evaluate(c, env, s)["total"] for s in STRESS)
        base_eval["worst"] = round(worst_score, 1)
        ev[c["name"]] = base_eval

    # Card 1: Customary / Existing Rotation crop
    existing = ev.get(existing_name)
    if not existing:
        for c in crops:
            if c["name"].lower() == existing_name.lower():
                existing = ev[c["name"]]
                break
    if not existing and crops:
        existing = ev[crops[0]["name"]]

    existing["is_existing_rotation"] = True

    # Card Pool for Cards 2 & 3:
    # - Exclude Card 1
    # - Pass Stage 1 hard filters (cls != "not_suitable")
    # - Red Flag Veto: strictly zero red factors (all f_i >= 40)
    pool = [
        e for n, e in ev.items()
        if n != existing["crop"] and e["cls"] != "not_suitable" and not e["red"]
    ]

    # Worst-Case Robustness Ranking within 5-point total score band:
    chosen: list[dict] = []
    used_families = {existing["family"]}

    def pick_best_candidate(candidates: list[dict], required_diff_family: bool = True) -> dict | None:
        valid = [c for c in candidates if (c["family"] not in used_families)] if required_diff_family else candidates
        if not valid:
            return None
        max_total = max(c["total"] for c in valid)
        band = [c for c in valid if c["total"] >= max_total - 5.0]
        band.sort(key=lambda c: (c["worst"], c["total"]), reverse=True)
        return band[0]

    # Pick Card 2 (different botanical family from Card 1)
    card2 = pick_best_candidate(pool, required_diff_family=True)
    if card2:
        chosen.append(card2)
        used_families.add(card2["family"])

    # Pick Card 3 (different botanical family from Card 1 and Card 2)
    card3 = pick_best_candidate(pool, required_diff_family=True)
    if card3:
        chosen.append(card3)
        used_families.add(card3["family"])

    # Fallback to pool if family diversity exhausted available families
    if len(chosen) < 2:
        for c in pool:
            if c not in chosen:
                chosen.append(c)
            if len(chosen) == 2:
                break

    cards = [existing] + chosen

    # "Holds Up Best" Badge:
    # Awarded to the card with highest worst-case score across 4 stress scenarios
    # if it leads the runner-up by >= 5 points and has no red factor.
    worst_scores = [c.get("worst", 0.0) for c in cards]
    if len(cards) > 1 and worst_scores:
        sorted_worst = sorted(worst_scores, reverse=True)
        best_worst = sorted_worst[0]
        second_best_worst = sorted_worst[1]
        lead = best_worst - second_best_worst

        for c in cards:
            c["holds_up_best"] = bool(
                c.get("worst", 0.0) == best_worst
                and not c.get("red")
                and lead >= 5.0
            )
    else:
        for c in cards:
            c["holds_up_best"] = False

    return cards


def _windows(text: str) -> list[tuple[int, int]]:
    return [tuple(int(x) for x in w.split("-")) for w in text.split(";")] if text else []


def load_crops(path: str = "data/crops.csv") -> list[dict]:
    p = Path(path)
    if not p.exists():
        alt1 = Path(__file__).resolve().parents[2] / "data/crops.csv"
        if alt1.exists():
            p = alt1
        else:
            alt2 = Path(__file__).resolve().parents[3] / "backend/data/crops.csv"
            if alt2.exists():
                p = alt2
    out = []
    with open(p, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            out.append(
                {
                    "name": r["name"],
                    "family": r["family"],
                    "duration_days": int(r["duration_days"]),
                    "need_mm": int(r["need_mm"]),
                    "water_need": r["water_need"],
                    "drought_tol": r["drought_tol"],
                    "waterlog_tol": r["waterlog_tol"],
                    "n_effect": r["n_effect"],
                    "ph_min": float(r["ph_min"]),
                    "ph_max": float(r["ph_max"]),
                    "t_min": float(r["t_min"]),
                    "t_max": float(r["t_max"]),
                    "t_flower_max": float(r["t_flower_max"]),
                    "flower_frac": (float(r["flower_frac_start"]), float(r["flower_frac_end"])),
                    "start_windows": _windows(r["start_windows"]),
                    "long_duration": int(r["long_duration"]),
                    "watch_for": [x.strip() for x in r["watch_for"].split(";") if x.strip()],
                    "elev_min": float(r["elev_min"]),
                    "elev_max": float(r["elev_max"]),
                    "repeat_penalty": int(r["repeat_penalty"]),
                    "om_bonus": bool(int(r["om_bonus"])),
                    "erosion_cover": bool(int(r["erosion_cover"])),
                    "market": r["market"],
                    "salinity_tol": r["salinity_tol"],
                    "good_next": [x.strip() for x in r["good_next"].split(";") if x.strip()],
                }
            )
    return out
