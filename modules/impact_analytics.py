"""Impact indicators. 'Measured' = computed from stored records; 'scenario' = hypothetical, user-adjustable."""
import pandas as pd
from database import db
from utils.calculations import to_kg, offer_net
from modules.risk_assessment import assess  # noqa: F401  (kept for callers)


def measured(db_path=None):
    b, o, a = db.list_batches(db_path), db.list_offers(db_path=db_path), db.list_assessments(db_path=db_path)
    out = {"batches": len(b), "total_kg": 0.0, "assessed": 0, "elevated": 0, "offers": len(o),
           "sample_batches": int(b["is_sample"].sum()) if len(b) else 0, "gross_recorded": 0.0,
           "net_recorded": 0.0, "recorded_spread": 0.0, "spread_groups": 0, "handling_events_kg": 0.0}
    if len(b):
        out["total_kg"] = float(sum(to_kg(r.quantity, r.unit) for r in b.itertuples()))
    if len(a):
        latest = a.drop_duplicates("batch_id")  # list is newest-first
        out["assessed"] = len(latest)
        out["elevated"] = int((latest.level == "Elevated").sum())
        out["latest_levels"] = latest.level.value_counts().to_dict()
    else:
        out["latest_levels"] = {}
    if len(o):
        calc = [offer_net(r) for r in o.to_dict("records")]
        o = o.assign(net=[c["net"] for c in calc], npk=[c["net_per_kg"] for c in calc])
        out["gross_recorded"] = float(sum(c["gross"] for c in calc))
        out["net_recorded"] = float(sum(c["net"] for c in calc))
        # spread between best and worst net/kg for same batch AND same grade (like-for-like only)
        bkg = {r.batch_id: to_kg(r.quantity, r.unit) for r in b.itertuples()}
        for (bid, _g), grp in o.groupby(["batch_id", "grade"]):
            if len(grp) >= 2:
                out["recorded_spread"] += float((grp.npk.max() - grp.npk.min()) * bkg.get(bid, 0))
                out["spread_groups"] += 1
    return out


def loss_scenario(total_kg, price_per_kg, baseline_loss_pct, reduction_pct):
    """Hypothetical: if baseline losses were reduced by reduction_pct (relative). NOT actual savings."""
    if min(total_kg, price_per_kg) < 0 or not (0 <= baseline_loss_pct <= 100) or not (0 <= reduction_pct <= 100):
        raise ValueError("Invalid scenario inputs.")
    lost = total_kg * baseline_loss_pct / 100
    avoided = lost * reduction_pct / 100
    return {"baseline_lost_kg": lost, "hypothetical_avoided_kg": avoided,
            "hypothetical_value": avoided * price_per_kg}
