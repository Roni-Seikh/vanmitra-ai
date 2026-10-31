"""Hold-or-sell logic combining REAL seasonal price behaviour (Agmarknet) with the batch's screening level and user costs."""
MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
# Placeholder monthly-loss ASSUMPTIONS by screening level (not measured data) - user can override in the UI.
DEFAULT_MONTHLY_LOSS_PCT = {"Low": 0.5, "Moderate": 1.5, "Elevated": 4.0, "Insufficient data": 1.0}


def seasonal_change_pct(profile, from_m, to_m):
    """Typical % change in price between two calendar months, from the real seasonal profile (median over states)."""
    dev = dict(zip(profile.month_no, profile.price_dev_pct))
    return ((1 + dev[to_m] / 100) / (1 + dev[from_m] / 100) - 1) * 100


def hold_or_sell(price_now, months, from_month_no, profile, monthly_cost, monthly_loss_pct, risk_level, margin_pct=3.0):
    if not price_now or price_now <= 0:
        raise ValueError("Enter a current selling price above zero.")
    if not (1 <= months <= 12):
        raise ValueError("Holding period must be 1-12 months.")
    if monthly_cost < 0 or not (0 <= monthly_loss_pct < 100):
        raise ValueError("Storage cost must be >= 0 and monthly loss between 0 and 100%.")
    to_m = (from_month_no - 1 + months) % 12 + 1
    sc = seasonal_change_pct(profile, from_month_no, to_m)
    exp_price = price_now * (1 + sc / 100)
    kept = (1 - monthly_loss_pct / 100) ** months
    hold_value = exp_price * kept - monthly_cost * months          # per kg of today's stock
    diff = hold_value - price_now; diff_pct = diff / price_now * 100
    breakeven = (price_now + monthly_cost * months) / kept
    why = [f"Typical seasonal price move {MON[from_month_no - 1]} to {MON[to_m - 1]}: {sc:+.1f}% (real Agmarknet history; the pattern is not guaranteed).",
           f"After {months} month(s) you keep about {kept * 100:.1f}% of the stock (assumed {monthly_loss_pct:g}%/month loss) and pay Rs{monthly_cost * months:.2f}/kg storage.",
           f"Holding is worth about Rs{hold_value:.2f} per kg of today's stock vs Rs{price_now:.2f} selling now ({diff_pct:+.1f}%).",
           f"Break-even: the price must reach about Rs{breakeven:.2f}/kg for holding to match selling now."]
    if risk_level == "Elevated":
        rec = "Sell or inspect now"
        why.insert(0, "Screening level is Elevated (e.g. mould/pest/damp signs): handling risk outweighs any seasonal upside until the stock is inspected.")
    elif diff_pct > margin_pct:
        rec = "Holding may pay"
    elif diff_pct < -margin_pct:
        rec = "Sell now"
    else:
        rec = "Too close to call"
    return {"recommendation": rec, "to_month": MON[to_m - 1], "seasonal_change_pct": sc, "expected_price": exp_price,
            "hold_value": hold_value, "sell_value": price_now, "diff_pct": diff_pct, "breakeven_price": breakeven,
            "reasons": why, "note": "Estimate from historical seasonality and your assumptions; not a price forecast or guarantee."}
