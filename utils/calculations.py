"""Unit normalisation and net-return maths (pure functions)."""
import config


def to_kg(quantity, unit):
    if unit not in config.UNIT_TO_KG:
        raise ValueError(f"Unsupported unit: {unit}")
    return float(quantity) * config.UNIT_TO_KG[unit]


def offer_net(o):
    """Net return = gross revenue - deductions - selling costs. Price is per the offer's own unit."""
    gross = o["price_per_unit"] * o["quantity"]
    deduction = gross * (o.get("deduction_pct") or 0) / 100.0 + (o.get("deduction_flat") or 0)
    costs = {k: o.get(k) or 0 for k in ("transport", "packaging", "processing", "other")}
    total_costs = sum(costs.values())
    net = gross - deduction - total_costs
    kg = to_kg(o["quantity"], o["unit"])
    return {"gross": gross, "deduction": deduction, "costs": costs, "total_costs": total_costs,
            "net": net, "kg": kg, "net_per_kg": net / kg, "gross_per_kg": gross / kg}
