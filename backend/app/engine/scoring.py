"""Field Shift deterministic rotation evaluation engine (Section 14 & 23.2).
Pure Python logic implementing hard filters, factor scoring, and card ranking.
"""
import csv

TOL = {"L": 0, "M": 1, "H": 2}
IRRIGATION_SHARE = {"rainfed": 0.0, "borewell": 0.6, "canal": 0.8, "unknown": 0.0}
EFFECTIVE_RAIN = 0.75
MARKET = {"high_demand": 85, "msp": 80, "medium": 60, "variable": 50, "limited": 30}
BASE_W = {"water": 30, "rotation": 25, "temp": 15, "soil": 15, "market": 10, "timing": 5}
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
    return max(lo, min(hi, x))

def get_weights(dry_outlook: bool = False, toggle: str | None = None) -> dict[str, float]:
    w = dict(BASE_W)
    if dry_outlook:
        w["water"] += 10
        w["market"] -= 5
        w["soil"] -= 5
    if toggle == "earn_more":
        w["market"] += 10
        w["water"] -= 5
        w["rotation"] -= 5
    elif toggle == "play_safe":
        w["market"] -= 5
        w["water"] += 5
    w = {k: max(v, 3) for k, v in w.items()}
    total = sum(w.values())
    return {k: v * 100.0 / total for k, v in w.items()}

def week_dist(w: int, a: int, b: int) -> int:
    inside = (a <= w <= b) if a <= b else (w >= a or w <= b)
    if inside:
        return 0
    d = lambda x, y: min((x - y) % 52, (y - x) % 52)
    return min(d(w, a), d(w, b))

def overlap_days(crop: dict, start_week: int, next_week: int) -> int:
    nxt = next_week if next_week > start_week else next_week + 52
    return max(0, crop["duration_days"] - (nxt - start_week) * 7)

def window_ctx(crop: dict, normals: dict, start_week: int, sc: dict, outlook_factor: float) -> dict:
    n = max(1, round(crop["duration_days"] / 7))
    idx = [(start_week - 1 + i) % 52 for i in range(n)]
    rain = sum(normals["rain"][i] for i in idx) * outlook_factor * sc["rain"] * EFFECTIVE_RAIN
    return {
        "rain": rain,
        "tmean": [normals["tmean"][i] for i in idx],
        "tmax": [normals["tmax"][i] for i in idx],
    }

def hard_filter(crop: dict, field: dict, start_week: int, next_week: int, tmean: list[float]) -> tuple[str, list[str]]:
    reasons, cls = [], "suitable"
    if not (crop["elev_min"] <= field["elevation_m"] <= crop["elev_max"]):
        return "not_suitable", ["elevation outside crop range"]
    avg_t = sum(tmean) / len(tmean)
    gap = max(crop["t_min"] - avg_t, avg_t - crop["t_max"], 0)
    if gap > 3:
        return "not_suitable", ["temperature outside crop range"]
    if gap > 0:
        cls = "marginal"
        reasons.append("temperature slightly outside range")
    dist = min(week_dist(start_week, a, b) for a, b in crop["start_windows"])
    if dist > 4:
        return "not_suitable", ["start week outside crop season"]
    if dist > 0:
        cls = "marginal"
        reasons.append("start week near the edge of the season")
    ov = 0 if crop.get("long_duration") else overlap_days(crop, start_week, next_week)
    if ov > 30:
        return "not_suitable", ["does not finish before the next season"]
    if ov > 0:
        cls = "marginal"
        reasons.append("overlaps the next season slightly")
    return cls, reasons

def water_score(crop: dict, field: dict, eff_rain: float, rain_factor: float, stored_mm: float = 0.0) -> float:
    need = crop["need_mm"]
    avail = eff_rain + stored_mm
    gap = max(0.0, need - avail)
    water_source = field.get("water_source", "rainfed")
    irr_share = IRRIGATION_SHARE.get(water_source, 0.0)
    supply = avail + irr_share * gap
    ratio = supply / need * (1 + 0.15 * TOL.get(crop["drought_tol"], 0))
    score = clamp((ratio - 0.3) / 0.5 * 100)
    if rain_factor >= 1.15 and field.get("flood_prone") and crop["waterlog_tol"] == "L":
        score -= 25
    if field.get("water_quality") == "saline":
        score -= {"L": 20, "M": 10, "H": 0}.get(crop.get("salinity_tol", "M"), 10)
    return clamp(score)

def rotation_score(crop: dict, history: list[dict], dry_outlook: bool) -> float:
    s = 80.0
    if history:
        last = history[0]
        streak = 0
        for h in history:
            if h.get("crop") == last.get("crop"):
                streak += 1
            else:
                break
        if crop["name"] == last.get("crop"):
            s -= crop.get("repeat_penalty", 25)
            if streak >= 2:
                s -= 15
        elif crop["family"] == last.get("family"):
            s -= 25
        elif len(history) > 1 and crop["family"] == history[1].get("family"):
            s -= 10
        if last.get("n_effect") == "heavy" and crop.get("n_effect") == "heavy":
            s -= 20
        elif last.get("n_effect") == "heavy" and crop.get("n_effect") == "fixer":
            s += 15
        elif last.get("n_effect") == "fixer" and crop.get("n_effect") == "heavy":
            s += 10
        if (
            last.get("outcome") in ("poor", "failed")
            and last.get("cause_approved")
            and crop["family"] == last.get("family")
            and last.get("cause") in ("pest", "disease")
        ):
            s -= 20
        if (
            last.get("cause_approved")
            and last.get("cause") == "water_stress"
            and crop.get("water_need") in ("high", "very_high")
            and dry_outlook
        ):
            s -= 10
    return clamp(s)

def temp_score(crop: dict, tmean: list[float], tmax: list[float], offset: float) -> float:
    n = len(tmean)
    ok = sum(1 for t in tmean if crop["t_min"] <= t + offset <= crop["t_max"])
    score = 100.0 * ok / n
    a, b = crop["flower_frac"]
    flower = range(int(a * n), max(int(b * n), int(a * n) + 1))
    if any(tmax[i] + offset > crop["t_flower_max"] for i in flower if i < n):
        score -= 30
    return clamp(score)

def soil_score(crop: dict, field: dict, bare_gap_days: int) -> float:
    ph = field.get("ph")
    if ph is None:
        ph = field.get("soil_ph")
    if ph is None:
        ph_fit = 60.0
    else:
        d = max(crop["ph_min"] - ph, ph - crop["ph_max"], 0)
        ph_fit = 100.0 if d == 0 else 70.0 if d <= 0.5 else 40.0
    drain_fit = 100.0
    if field.get("flood_prone") or field.get("drainage") == "poor":
        drain_fit = {"L": 40.0, "M": 70.0, "H": 100.0}.get(crop["waterlog_tol"], 70.0)
    fit = (ph_fit + drain_fit) / 2.0
    benefit = {"fixer": 100.0, "neutral": 60.0, "heavy": 30.0}.get(crop["n_effect"], 60.0)
    if crop.get("om_bonus"):
        benefit += 10
    slope = field.get("slope")
    if crop.get("erosion_cover") and slope is not None and slope != "low":
        benefit += 10
    if bare_gap_days >= 40 and crop["duration_days"] <= bare_gap_days:
        benefit += 10
    return clamp(0.5 * fit + 0.5 * clamp(benefit))

def evaluate(crop: dict, env: dict, scenario: dict | None = None) -> dict:
    sc = scenario or env["scenario"]
    ctx = window_ctx(crop, env["normals"], env["start_week"], sc, env["outlook_factor"])
    cls, reasons = hard_filter(crop, env["field"], env["start_week"], env["next_week"], ctx["tmean"])
    ov = 0 if crop.get("long_duration") else overlap_days(crop, env["start_week"], env["next_week"])
    f = {
        "water": water_score(crop, env["field"], ctx["rain"], sc["rain"], env.get("stored_mm", 0.0)),
        "rotation": rotation_score(crop, env["history"], env.get("dry_outlook", False)),
        "temp": temp_score(crop, ctx["tmean"], ctx["tmax"], sc["temp"]),
        "soil": soil_score(crop, env["field"], env.get("bare_gap_days", 0)),
        "market": MARKET.get(crop["market"], 60),
        "timing": 100.0 if ov == 0 else 60.0 if ov <= 14 else 30.0,
    }
    w = env["weights"]
    total = sum(w[k] * f[k] / 100.0 for k in w)
    
    colors = {}
    for k, v in f.items():
        if v >= 65:
            colors[k] = "green"
        elif v >= 40:
            colors[k] = "amber"
        else:
            colors[k] = "red"

    return {
        "crop": crop["name"],
        "family": crop["family"],
        "cls": cls,
        "reasons": reasons,
        "factors": f,
        "colors": colors,
        "total": round(total, 1),
        "red": [k for k, v in f.items() if v < 40],
        "amber": [k for k, v in f.items() if 40 <= v < 65],
    }

def verdict(e: dict) -> str:
    if e["cls"] == "not_suitable" or e["total"] < 45:
        return "Not suited this season"
    if e["cls"] == "marginal" or e["total"] < 70 or e["red"]:
        return "Possible with risk"
    return "Feasible"

def pick_three(crops: list[dict], env: dict, existing_name: str) -> list[dict]:
    ev = {c["name"]: evaluate(c, env) for c in crops}
    for c in crops:
        ev[c["name"]]["worst"] = min(evaluate(c, env, s)["total"] for s in STRESS)

    existing = ev.get(existing_name)
    if not existing:
        existing = ev[crops[0]["name"]]

    pool = [e for n, e in ev.items() if n != existing["crop"] and e["cls"] != "not_suitable" and not e["red"]]
    pool.sort(key=lambda e: (round(e["total"] / 5), e["worst"]), reverse=True)

    chosen, fams = [], {existing["family"]}
    for e in pool:
        if e["family"] not in fams:
            chosen.append(e)
            fams.add(e["family"])
        if len(chosen) == 2:
            break

    for e in pool:
        if len(chosen) == 2:
            break
        if e not in chosen:
            chosen.append(e)

    cards = [existing] + chosen
    
    # Check robustness "holds up best"
    if cards:
        best_worst = max(c.get("worst", 0) for c in cards)
        top_robust = [c for c in cards if c.get("worst", 0) == best_worst and not c.get("red")]
        for c in cards:
            c["holds_up_best"] = bool(top_robust and c == top_robust[0] and len(cards) > 1 and (best_worst - min(x.get("worst", 0) for x in cards) >= 5))
            
    return cards

def _windows(text: str) -> list[tuple[int, int]]:
    return [tuple(int(x) for x in w.split("-")) for w in text.split(";")] if text else []

def load_crops(path: str = "data/crops.csv") -> list[dict]:
    out = []
    with open(path, "r", encoding="utf-8") as f:
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
