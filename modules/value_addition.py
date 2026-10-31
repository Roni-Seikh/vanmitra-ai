"""Illustrative value-addition economics. Defaults are PLACEHOLDER assumptions, not data: users must replace them."""
CAUTION = ("Processing food products may need food-business registration/licensing and hygiene compliance "
           "(verify with FSSAI / local authority). Results are illustrative, not a profit guarantee.")
PATHWAYS = {
    "Tamarind": [
        dict(name="Grading and sorting", cost_per_kg=2.0, loss_pct=3.0, uplift_pct=8.0,
             why="Separates quality classes so better lots can target buyers who pay for grade."),
        dict(name="Improved packaging (lined bags)", cost_per_kg=3.0, loss_pct=0.0, uplift_pct=3.0,
             why="Limits moisture uptake during storage/transport; may support buyer acceptance."),
        dict(name="Aggregation through producer group", cost_per_kg=1.5, loss_pct=0.0, uplift_pct=5.0,
             why="Larger combined lots can improve bargaining and cut per-kg transport."),
        dict(name="Cleaning / de-seeding (manual)", cost_per_kg=6.0, loss_pct=30.0, uplift_pct=45.0,
             why="Sells a cleaner product; weight loss depends on method, so enter your measured value."),
    ],
    "Honey": [
        dict(name="Straining and hygienic packaging", cost_per_kg=8.0, loss_pct=2.0, uplift_pct=10.0,
             why="Cleaner presentation in food-grade containers; check applicable food rules."),
        dict(name="Moisture check before sale", cost_per_kg=1.0, loss_pct=0.0, uplift_pct=3.0,
             why="Documented moisture can help negotiate with buyers; needs a calibrated refractometer."),
        dict(name="Aggregation through producer group", cost_per_kg=2.0, loss_pct=0.0, uplift_pct=5.0,
             why="Combined lots, shared testing and transport."),
    ],
    "Other NTFP": [
        dict(name="Grading and sorting", cost_per_kg=2.0, loss_pct=3.0, uplift_pct=8.0, why="Generic placeholder."),
        dict(name="Aggregation through producer group", cost_per_kg=1.5, loss_pct=0.0, uplift_pct=5.0,
             why="Generic placeholder."),
    ],
}


def evaluate(qty_kg, price_per_kg, cost_per_kg, loss_pct, uplift_pct, fixed_cost=0.0):
    """Compare selling raw vs the option. Option revenue = output kg x price x (1+uplift)."""
    if qty_kg <= 0 or price_per_kg < 0 or not (0 <= loss_pct < 100) or uplift_pct < -100:
        raise ValueError("Invalid inputs for value-addition estimate.")
    base = qty_kg * price_per_kg
    out_kg = qty_kg * (1 - loss_pct / 100)
    revenue = out_kg * price_per_kg * (1 + uplift_pct / 100)
    costs = cost_per_kg * qty_kg + fixed_cost
    opt_net = revenue - costs
    denom = out_kg * price_per_kg
    breakeven = ((base + costs) / denom - 1) * 100 if denom > 0 else None
    return {"baseline_net": base, "output_kg": out_kg, "option_revenue": revenue, "option_costs": costs,
            "option_net": opt_net, "difference": opt_net - base, "breakeven_uplift_pct": breakeven}
