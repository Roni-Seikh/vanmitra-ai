"""Buyer-offer comparison on a transparent net-return basis."""
from utils.calculations import offer_net


def compare_offers(offers, criterion="net_per_kg", batch_kg=None):
    """offers: list of dicts with offer fields (optionally 'id'). criterion: 'net_per_kg' or 'net'.
    Returns dict(rows, best, reasons, warnings, assumptions)."""
    if not offers:
        return {"rows": [], "best": None, "reasons": [], "warnings": [], "assumptions": []}
    rows = []
    for o in offers:
        r = offer_net(o)
        rows.append({"buyer": o["buyer"], "grade": o["grade"], "qty_kg": r["kg"], "gross": r["gross"],
                     "deductions": r["deduction"], **{f"cost_{k}": v for k, v in r["costs"].items()},
                     "total_costs": r["total_costs"], "net": r["net"], "net_per_kg": r["net_per_kg"],
                     "is_sample": o.get("is_sample", 0)})
    key = "net_per_kg" if criterion == "net_per_kg" else "net"
    rows.sort(key=lambda r: r[key], reverse=True)
    best = rows[0]
    warnings, assumptions = [], ["All quantities converted to kg for comparison.",
                                 "Price is per the unit stated on each offer; costs are totals in ₹ for that offer."]
    grades = {r["grade"] for r in rows}
    if len(grades) > 1:
        warnings.append(f"Offers specify different grades ({', '.join(sorted(grades))}). Rankings mix grades and "
                        "may not be like-for-like; check whether your stock actually meets each grade.")
    qtys = {round(r["qty_kg"], 3) for r in rows}
    if len(qtys) > 1 and criterion == "net":
        warnings.append("Offered quantities differ, so total net is not like-for-like; net per kg is fairer.")
    if batch_kg:
        for r in rows:
            if r["qty_kg"] > batch_kg * 1.0001:
                warnings.append(f"{r['buyer']}: offered quantity ({r['qty_kg']:g} kg) exceeds the batch "
                                f"({batch_kg:g} kg).")
            elif r["qty_kg"] < batch_kg * 0.9999:
                warnings.append(f"{r['buyer']}: covers only {r['qty_kg']:g} of {batch_kg:g} kg; the rest "
                                "would need another buyer.")
    if all(r["total_costs"] == 0 and r["deductions"] == 0 for r in rows):
        assumptions.append("No costs or deductions were entered; every offer is treated as cost-free.")
    if any(r["is_sample"] for r in rows):
        warnings.append("Some offers are SAMPLE/illustrative; they are not market quotations.")
    reasons = [f"{best['buyer']} has the highest {'net return per kg' if key == 'net_per_kg' else 'total net return'} "
               f"among the recorded offers (₹{best[key]:,.2f}{'/kg' if key == 'net_per_kg' else ''})."]
    if len(rows) > 1:
        s = rows[1]
        reasons.append(f"It beats the next option ({s['buyer']}) by ₹{best[key] - s[key]:,.2f}"
                       f"{'/kg' if key == 'net_per_kg' else ''}.")
        top_gross = max(rows, key=lambda r: r["gross"] / r["qty_kg"])
        if top_gross["buyer"] != best["buyer"]:
            reasons.append(f"Note: {top_gross['buyer']} quotes the highest headline price per kg, but costs/"
                           "deductions reduce its net return.")
    return {"rows": rows, "best": best, "reasons": reasons, "warnings": warnings, "assumptions": assumptions,
            "criterion": key}
