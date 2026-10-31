"""Transparent, product-specific preliminary SCREENING rules (no trained model).

Why rules and not ML: no labelled public dataset of NTFP post-harvest outcomes was verified during this build,
so training a model would only reproduce invented labels. Thresholds below are team-set screening heuristics,
NOT validated cut-offs; they are editable in RULES and must be reviewed with a domain expert / the relevant
food-safety authority before field use. The output is a screening level, not a spoilage prediction.
"""
from datetime import date, datetime

# each list = [(threshold, points)] checked from the highest threshold down; first match wins
RULES = {
    "Tamarind": dict(age=[(60, 2), (30, 1)], humidity=[(75, 2), (65, 1)], temp=[(35, 1)], moisture=[(15, 3), (12, 1)],
                     key=("moisture_pct", "storage_humidity_pct", "storage_temp_c"),
                     note="Tamarind moisture lines (>12% / >15%) follow buyer-specification guidance published by an "
                          "Indian exporter (botanikabharat.com/tamarind.php, accessed 28 Oct 2026: export grade <=10-12%, "
                          ">15% promotes mould) - a commercial, non-regulatory source. Humidity lines reflect the "
                          "widely reported ~65% RH mould-growth threshold for stored produce (PMC3989759, a grain/"
                          "peanut review). Confirm with a food-technology expert before field use."),
    "Honey": dict(age=[(365, 1)], humidity=[(70, 1)], temp=[(30, 1)], moisture=[(20, 3), (18, 1)],
                  key=("moisture_pct", "storage_humidity_pct", "storage_temp_c"),
                  note="The 20% moisture line is the general honey limit cited in a Croatian quality-monitoring study "
                       "(Foods 2026, doi:10.3390/foods15132311); confirm against the applicable FSSAI/buyer "
                       "specification and use a calibrated refractometer."),
    "Other NTFP": dict(age=[(30, 1)], humidity=[(75, 1)], temp=[(35, 1)], moisture=None,
                       key=("storage_humidity_pct", "storage_temp_c"),
                       note="Generic rules only: product-specific thresholds are not available."),
}
STORAGE_POINTS = {"Open air / uncovered": 2, "Ground-level room": 1}
PACKAGING_POINTS = {"Open / loose": 2, "Jute sack": 1}
FIELD_LABELS = {"storage_humidity_pct": "storage humidity", "storage_temp_c": "storage temperature",
                "moisture_pct": "product moisture reading"}
LIMITATIONS = ("Preliminary screening based on user-entered values and team-set heuristic rules. Not validated "
               "against field outcomes, not a laboratory test, not a spoilage prediction, and not a food-safety "
               "or quality certification.")


def _tier(value, tiers):
    for thr, pts in tiers:
        if value > thr:
            return pts, thr
    return 0, None


def _age_days(batch, today):
    d = batch["collection_date"]
    d = datetime.strptime(d, "%Y-%m-%d").date() if isinstance(d, str) else d
    return max((today - d).days, 0)


def assess(batch, today=None):
    today = today or date.today()
    # pandas hands back NaN for NULLs; treat NaN as "missing" exactly like None
    batch = {k: (None if isinstance(v, float) and v != v else v) for k, v in batch.items()}
    rules = RULES.get(batch["product"], RULES["Other NTFP"])
    factors, steps, score = [], [], 0

    def add(name, value, pts, why, step=None):
        nonlocal score
        score += pts
        factors.append({"factor": name, "value": value, "points": pts, "why": why})
        if step and pts:
            steps.append(step)

    age = _age_days(batch, today)
    p, thr = _tier(age, rules["age"])
    add("Time since collection", f"{age} days", p, f"Longer storage raises exposure (rule: >{thr} days)" if p
        else "Within the screening window", "Prioritise selling or inspecting older stock first.")
    for field, key, label, unit, step in [
            ("storage_humidity_pct", "humidity", "Storage humidity", "%", "Reduce humidity: ventilate, raise stock off the floor, keep dry."),
            ("storage_temp_c", "temp", "Storage temperature", "°C", "Move stock to a cooler, shaded place.")]:
        v = batch.get(field)
        if v is None:
            continue
        p, thr = _tier(v, rules[key])
        add(label, f"{v:g}{unit}", p, f"Above screening line of {thr}{unit}" if p else "Within screening line", step)
    if rules["moisture"] and batch.get("moisture_pct") is not None:
        v = batch["moisture_pct"]
        p, thr = _tier(v, rules["moisture"])
        add("Product moisture", f"{v:g}%", p, f"Above screening line of {thr}%" if p else "Within screening line",
            "Re-measure with a calibrated instrument; consider drying/handling guidance before sale.")
    sp = STORAGE_POINTS.get(batch["storage_type"], 0)
    add("Storage type", batch["storage_type"], sp, "Exposure to damp/ground contact" if sp else "No concern flagged",
        "Use a raised, ventilated or sealed dry storage option.")
    pp = PACKAGING_POINTS.get(batch["packaging_type"], 0)
    add("Packaging", batch["packaging_type"], pp, "Limited moisture/pest barrier" if pp else "No concern flagged",
        "Consider lined or airtight packaging.")

    mold, pests = bool(batch.get("visible_mold")), bool(batch.get("pest_signs"))
    if pests:
        add("Pest signs reported", "yes", 3, "User reported pest signs", "Separate affected stock and inspect the rest.")
    if mold:
        add("Visible mould reported", "yes", 4, "Visible mould is a serious warning sign",
            "Do not sell or consume affected stock without expert/lab advice; isolate it.")

    missing = [FIELD_LABELS[k] for k in rules["key"] if batch.get(k) is None]
    if mold or score >= 6:
        level = "Elevated"
    elif score >= 3:
        level = "Moderate"
    else:
        level = "Low"
    if len(missing) == len(rules["key"]) and level == "Low":
        level = "Insufficient data"
    if level == "Low" and missing:
        steps.append("Add the missing measurements to make the screening more reliable.")
    return {"level": level, "score": score, "factors": factors, "missing": missing,
            "next_steps": list(dict.fromkeys(steps)) or ["Keep monitoring and recording storage conditions."],
            "method": "rule-based screening v1 (not machine learning)", "rule_note": rules["note"],
            "limitations": LIMITATIONS, "assessed_on": today.isoformat()}
