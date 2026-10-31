"""Loads a model ONLY if it was trained on real data. The synthetic demo model is never used for screening."""
import json
from pathlib import Path
import joblib
import config
from ml.preprocessing import batch_to_row

REAL = Path(config.ROOT) / "models" / "real"
DEMO = Path(config.ROOT) / "models" / "demo"


def _metrics(d):
    f = Path(d) / "metrics.json"
    return json.loads(f.read_text()) if f.exists() else None


def status(real_dir=REAL, demo_dir=DEMO):
    rm, dm = _metrics(real_dir), _metrics(demo_dir)
    real_ok = bool(rm) and not rm.get("SYNTHETIC_DEMO", True) and (Path(real_dir) / "model.joblib").exists()
    return {"real_model": real_ok, "real_metrics": rm if real_ok else None, "demo_metrics": dm,
            "message": ("A model trained on supplied pilot data is loaded; see its held-out metrics." if real_ok else
                        "No model trained on REAL data exists. Screening stays rule-based. The ML pipeline is built and "
                        "tested; it needs real labelled pilot batches (>=200 rows).")}


def predict_risk(batch, real_dir=REAL):
    """Probability that a batch is downgraded/lost, or None if no real-data model exists."""
    if not status(real_dir)["real_model"]:
        return None
    pipe = joblib.load(Path(real_dir) / "model.joblib")
    return {"probability_downgraded_or_lost": float(pipe.predict_proba(batch_to_row(batch))[0][1]),
            "note": "Model estimate from pilot data; not a guarantee."}
