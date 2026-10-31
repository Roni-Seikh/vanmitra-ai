"""Input validation. Returns (cleaned_dict, list_of_error_strings)."""
import math
from datetime import date, datetime
import config


def _num(v, name, lo, hi, errors, required=False):
    if v is None or (isinstance(v, str) and not v.strip()):
        if required:
            errors.append(f"{name} is required.")
        return None
    try:
        x = float(v)
    except (TypeError, ValueError):
        errors.append(f"{name} must be a number.")
        return None
    if math.isnan(x) or math.isinf(x) or x < lo or x > hi:
        errors.append(f"{name} must be between {lo:g} and {hi:g}.")
        return None
    return x


def validate_batch(d, today=None):
    today = today or date.today()
    e, c = [], {}
    c["product"] = d.get("product")
    if c["product"] not in config.PRODUCTS:
        e.append("Choose a supported product.")
    c["region"] = (d.get("region") or "").strip()
    if not c["region"]:
        e.append("Collection region is required (district/state level is enough; do not enter exact "
                 "coordinates of sensitive or protected resources).")
    elif len(c["region"]) > 120:
        e.append("Region is too long (max 120 characters).")
    cd = d.get("collection_date")
    if isinstance(cd, str):
        try:
            cd = datetime.strptime(cd, "%Y-%m-%d").date()
        except ValueError:
            cd = None
    if not isinstance(cd, date):
        e.append("Collection date is required (YYYY-MM-DD).")
    elif cd > today:
        e.append("Collection date cannot be in the future.")
    elif (today - cd).days > 365 * 5:
        e.append("Collection date is more than 5 years ago; please check it.")
    c["collection_date"] = cd.isoformat() if isinstance(cd, date) else None
    c["quantity"] = _num(d.get("quantity"), "Quantity", 0.001, 1_000_000, e, required=True)
    c["unit"] = d.get("unit")
    if c["unit"] not in config.UNIT_TO_KG:
        e.append("Choose a valid unit.")
    c["storage_type"] = d.get("storage_type")
    if c["storage_type"] not in config.STORAGE_TYPES:
        e.append("Choose a storage type.")
    c["packaging_type"] = d.get("packaging_type")
    if c["packaging_type"] not in config.PACKAGING_TYPES:
        e.append("Choose a packaging type.")
    c["storage_temp_c"] = _num(d.get("storage_temp_c"), "Storage temperature (°C)", -20, 60, e)
    c["storage_humidity_pct"] = _num(d.get("storage_humidity_pct"), "Storage humidity (%)", 0, 100, e)
    c["moisture_pct"] = _num(d.get("moisture_pct"), "Product moisture (%)", 0, 100, e)
    c["visible_mold"] = int(bool(d.get("visible_mold")))
    c["pest_signs"] = int(bool(d.get("pest_signs")))
    for k, n, m in [("handling_notes", "Handling notes", 1000), ("producer_group", "Producer group", 80),
                    ("provenance_ref", "Provenance reference", 200), ("verifier", "Verifier", 120),
                    ("sustainability_doc_ref", "Sustainability document reference", 200)]:
        c[k] = (d.get(k) or "").strip()
        if len(c[k]) > m:
            e.append(f"{n} is too long (max {m} characters).")
    for k, n in [("provenance_status", "Provenance status"), ("sustainability_doc_status", "Sustainability doc status")]:
        c[k] = d.get(k, "unavailable")
        if c[k] not in config.PROVENANCE_STATUSES:
            e.append(f"{n} is invalid.")
    if c["provenance_status"] == "verified" and not c["verifier"]:
        e.append("'verified' requires naming who verified it. Otherwise use 'documented' or 'user-reported'.")
    c["is_sample"] = int(bool(d.get("is_sample", 0)))
    return c, e


def validate_offer(d):
    e, c = [], {}
    c["buyer"] = (d.get("buyer") or "").strip()
    if not c["buyer"]:
        e.append("Buyer name or identifier is required.")
    c["price_per_unit"] = _num(d.get("price_per_unit"), "Price per unit (₹)", 0.0001, 10_000_000, e, True)
    c["quantity"] = _num(d.get("quantity"), "Offered quantity", 0.001, 1_000_000, e, True)
    c["unit"] = d.get("unit")
    if c["unit"] not in config.UNIT_TO_KG:
        e.append("Choose a valid unit.")
    c["grade"] = d.get("grade") or "Ungraded"
    for k, n in [("transport", "Transport cost"), ("packaging", "Packaging cost"), ("processing", "Processing cost"),
                 ("other", "Other costs"), ("deduction_flat", "Flat deduction")]:
        c[k] = _num(d.get(k), n + " (₹)", 0, 100_000_000, e) or 0.0
    c["deduction_pct"] = _num(d.get("deduction_pct"), "Deduction (%)", 0, 100, e) or 0.0
    c["is_sample"] = int(bool(d.get("is_sample", 0)))
    return c, e
