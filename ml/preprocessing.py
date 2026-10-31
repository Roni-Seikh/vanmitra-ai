"""Feature definitions + sklearn pipeline for a FUTURE validated model trained on real labelled pilot data."""
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

NUM = ["age_days", "storage_humidity_pct", "storage_temp_c", "moisture_pct"]
CAT = ["product", "storage_type", "packaging_type"]
FLAG = ["visible_mold", "pest_signs"]
TARGET = "outcome"                 # 1 = downgraded/rejected/lost at sale or inspection, 0 = acceptable
FEATURES = NUM + CAT + FLAG
# LEAKAGE WARNING: if the outcome label IS mould/pest rejection, exclude FLAG columns (train_model --exclude).


def build_pipeline(estimator, exclude=()):
    num = [c for c in NUM if c not in exclude]; cat = [c for c in CAT if c not in exclude]
    flag = [c for c in FLAG if c not in exclude]
    ct = ColumnTransformer([
        ("num", Pipeline([("imp", SimpleImputer(strategy="median", keep_empty_features=True)),
                          ("sc", StandardScaler())]), num),
        ("cat", OneHotEncoder(handle_unknown="ignore"), cat),
        ("flag", "passthrough", flag)])
    return Pipeline([("prep", ct), ("model", estimator)]), num + cat + flag


def batch_to_row(batch, today=None):
    """Convert an app batch dict to a one-row DataFrame with the training feature names."""
    from datetime import date, datetime
    today = today or date.today()
    cd = batch["collection_date"]
    cd = datetime.strptime(cd, "%Y-%m-%d").date() if isinstance(cd, str) else cd
    row = {k: batch.get(k) for k in FEATURES if k != "age_days"}
    row["age_days"] = max((today - cd).days, 0)
    return pd.DataFrame([row], columns=FEATURES)
