import re

NUM = re.compile(r"\d+(?:[.,]\d+)?")

def _flat_numbers(obj, acc: set[str]) -> set[str]:
    if isinstance(obj, dict):
        for v in obj.values():
            _flat_numbers(v, acc)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            _flat_numbers(v, acc)
    elif isinstance(obj, bool):
        pass
    elif isinstance(obj, (int, float)):
        acc.add(f"{obj:g}")
        acc.add(str(round(obj)))
    elif isinstance(obj, str):
        for m in NUM.findall(obj):
            acc.add(m.replace(",", "."))
    return acc

def validate_explanation(
    text: str,
    source_json: dict,
    banned: tuple[str, ...] = ("guarantee", "will definitely", "best crop", "100% yield"),
) -> tuple[bool, dict]:
    allowed = _flat_numbers(source_json, set())
    found = [m.replace(",", ".") for m in NUM.findall(text)]
    bad = [n for n in found if n not in allowed and n.rstrip("0").rstrip(".") not in allowed]
    words = [w for w in banned if w in text.lower()]
    is_valid = (not bad and not words)
    return is_valid, {"unknown_numbers": bad, "banned_words": words}

def get_template_narrative(crop_name: str, verdict: str, factors: dict, language: str = "en") -> dict:
    if language == "ml":
        return {
            "why": f"{crop_name} ഈ കാലാവസ്ഥയിൽ കൃഷി ചെയ്യാൻ അനുയോജ്യമായ ഘടകങ്ങളുണ്ട്.",
            "risks": "കൂടിയ മഴയുള്ള സമയങ്ങളിൽ നീർവാർച്ച ശ്രദ്ധിക്കുക.",
            "previous_crop_effect": "മുൻ വിളയ്ക്ക് ശേഷം മണ്ണിലെ നൈട്രജൻ അളവ് മെച്ചപ്പെടുത്താൻ സഹായിക്കും.",
            "next_step": "വിത്ത് ലഭ്യതയും പ്രാദേശിക വിപണി വിലയും അന്വേഷിക്കുക.",
            "watch_for": "ആദ്യ മൂന്നാഴ്ചകളിലെ ഇലകളുടെ വളർച്ച നിരീക്ഷിക്കുക.",
            "after_this": "ഇതിനുശേഷം നെല്ല് കൃഷി ചെയ്യുമ്പോൾ വളം കുറച്ചു മതിയാകും.",
        }
    
    return {
        "why": f"{crop_name.replace('_', ' ').title()} fits the seasonal planting window and soil conditions.",
        "risks": "Watch for waterlogging if intense rainfall occurs during establishment.",
        "previous_crop_effect": "Balances soil nutrient depletion from the previous crop cycle.",
        "next_step": "Check certified seed availability with local agricultural officer.",
        "watch_for": "Monitor leaf development and soil moisture in the first 3 weeks.",
        "after_this": "Following with monsoon paddy will require reduced nitrogen application.",
    }
