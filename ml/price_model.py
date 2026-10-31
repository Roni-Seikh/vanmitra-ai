"""Real-data price model: next-month mandi price change, trained on India-wide Agmarknet monthly state prices.

Data   : data/real/agmarknet_state_monthly_all.csv.gz (all commodities, 2019-01..2026-10, ~204k rows; Govt. of India open data).
Task   : y = log(price[t+1]) - log(price[t]) for each (commodity, state) series with >= 48 months of history.
Pooled : trained on ALL commodities (~100k+ labelled rows) because tamarind alone has too few rows; evaluated on tamarind
         (and the forest-produce group) in a held-out future period.
Split  : strictly chronological by TARGET month: train <= 2023-12, validation 2024, test 2025-01..2026-09 (test used once).
Leak-free features at time t: past log changes, deviation from 12-mo mean, volatility, arrivals, calendar month of the target,
         and the series' own past average change for that calendar month (uses only months <= t-12).
Baselines: naive (no change) and seasonal-mean.  Selection on validation only.  Deployment model refit on all labelled rows.
    python -m ml.price_model
"""
import json
from datetime import date
from pathlib import Path
import joblib, numpy as np, pandas as pd, sklearn
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "real" / "agmarknet_state_monthly_all.csv.gz"
OUT = ROOT / "models" / "price"
COMMODITY = "Tamarind Fruit"
MIN_MONTHS = 48
TRAIN_END, VAL_END, TEST_END = "2023-12", "2024-12", "2026-09"
NUM = ["r1", "r2", "r3", "r12", "dev12", "vol6", "arr_chg", "arr_lvl", "seas", "m_sin", "m_cos"]
CAT = ["group"]


def load_all(path=DATA, groups=None):
    d = pd.read_csv(path).dropna(subset=["price_rs_qtl"])
    d = d[d.price_rs_qtl > 0].copy()
    if groups:
        d = d[d.group.isin(groups)]
    d["month"] = pd.PeriodIndex(d["month"], freq="M")
    return d


def series_features(g):
    """Feature frame for ONE (commodity, state) series, indexed by month t. g needs month, price_rs_qtl, arrivals_t."""
    g = g.set_index("month").sort_index()
    idx = pd.period_range(g.index.min(), g.index.max(), freq="M")
    lp = np.log(g["price_rs_qtl"].reindex(idx)).interpolate(limit=2)
    la = np.log1p(g["arrivals_t"].reindex(idx)).interpolate(limit=2)
    f = pd.DataFrame({"lp": lp, "la": la})
    for k in (1, 2, 3, 12):
        f[f"r{k}"] = f.lp - f.lp.shift(k)
    f["dev12"] = f.lp - f.lp.rolling(12).mean()
    f["vol6"] = f.lp.diff().rolling(6).std()
    f["arr_chg"] = f.la.diff(); f["arr_lvl"] = f.la - f.la.rolling(12).mean()
    f["y"] = f.lp.shift(-1) - f.lp
    mo = np.array([p.month for p in f.index])
    # own history of the change into each calendar month, known at t only from y at s<=t-12
    f["seas"] = f.groupby(mo)["y"].transform(lambda x: x.shift(1).expanding().mean())
    f["tm"] = f.index + 1
    tmn = np.array([p.month for p in f["tm"]])
    f["m_sin"], f["m_cos"] = np.sin(2 * np.pi * tmn / 12), np.cos(2 * np.pi * tmn / 12)
    f["price_now"] = np.exp(f.lp); f["month"] = f.index
    return f


def build_panel(d, min_months=MIN_MONTHS):
    parts = []
    for (c, s), g in d.groupby(["commodity", "state"]):
        if len(g) < min_months:
            continue
        f = series_features(g); f["commodity"], f["state"], f["group"] = c, s, g["group"].iloc[0]
        parts.append(f)
    return pd.concat(parts, ignore_index=True)


def _pipe(est):
    return Pipeline([("p", ColumnTransformer([("n", StandardScaler(), NUM), ("c", OneHotEncoder(handle_unknown="ignore"), CAT)])), ("m", est)])


def _candidates(seed=0):
    return {"ridge": _pipe(Ridge(alpha=10.0)),
            "hgb_squared": _pipe(HistGradientBoostingRegressor(max_depth=4, learning_rate=0.05, max_iter=300, l2_regularization=1.0, random_state=seed)),
            "hgb_absolute": _pipe(HistGradientBoostingRegressor(loss="absolute_error", max_depth=4, learning_rate=0.05, max_iter=300, l2_regularization=1.0, random_state=seed))}


def _ev(df, p):
    a = df.price_now * np.exp(df.y); fc = df.price_now * np.exp(p); ae = (a - fc).abs()
    return {"mae_rs_qtl": round(float(ae.mean()), 1), "mape_pct": round(float((ae / a).mean() * 100), 2), "n": int(len(df))}


def _boot_ci(df, p, seed=0, B=2000):
    """Bootstrap 95% CI for (naive MAE - model MAE) in Rs/qtl, resampling rows (rows are correlated: treat as rough)."""
    a = (df.price_now * np.exp(df.y)).values; pn = df.price_now.values; fc = pn * np.exp(p)
    diff = np.abs(a - pn) - np.abs(a - fc)
    rng = np.random.default_rng(seed); bs = [diff[rng.integers(0, len(diff), len(diff))].mean() for _ in range(B)]
    return [round(float(np.percentile(bs, 2.5)), 1), round(float(np.percentile(bs, 97.5)), 1)]


def train_and_evaluate(path=DATA, out_dir=OUT, groups=None, commodity=COMMODITY, seed=0, min_split=30):
    P = build_panel(load_all(path, groups))
    L = P.dropna(subset=NUM + ["y"]); tm = L.tm.astype(str)
    tr, va = L[tm <= TRAIN_END], L[(tm > TRAIN_END) & (tm <= VAL_END)]
    te = L[(tm > VAL_END) & (tm <= TEST_END)]
    focus = lambda x: x[x.commodity == commodity]
    if min(len(tr), len(focus(va)), len(focus(te))) < min_split:
        raise ValueError("Not enough rows per split for a meaningful evaluation.")
    cols = NUM + CAT
    res = {"naive_no_change": {}, "seasonal_mean": {}}
    for nm, sel in (("all_series", lambda x: x), ("forest_group", lambda x: x[x.group == "Forest Products"]), (commodity, focus)):
        for sp, df in (("val", va), ("test", te)):
            x = sel(df)
            if len(x):
                res["naive_no_change"].setdefault(nm, {})[sp] = _ev(x, np.zeros(len(x)))
                res["seasonal_mean"].setdefault(nm, {})[sp] = _ev(x, x.seas.fillna(0).values)
    fit = {n: m.fit(tr[cols], tr.y) for n, m in _candidates(seed).items()}
    for n, m in fit.items():
        res[n] = {nm: {"val": _ev(sel(va), m.predict(sel(va)[cols]))} for nm, sel in
                  (("all_series", lambda x: x), ("forest_group", lambda x: x[x.group == "Forest Products"]), (commodity, focus)) if len(sel(va))}
    best = min(fit, key=lambda n: res[n]["all_series"]["val"]["mae_rs_qtl"])          # VALIDATION only
    resid_val = focus(va).y.values - fit[best].predict(focus(va)[cols])
    q10, q90 = (float(v) for v in np.quantile(resid_val, [.10, .90]))                  # interval calibrated on validation
    chosen = _candidates(seed)[best].fit(pd.concat([tr, va])[cols], pd.concat([tr, va]).y)
    for nm, sel in (("all_series", lambda x: x), ("forest_group", lambda x: x[x.group == "Forest Products"]), (commodity, focus)):
        x = sel(te)
        if len(x):
            res[best].setdefault(nm, {})["test"] = _ev(x, chosen.predict(x[cols]))
    tt = focus(te); pt = chosen.predict(tt[cols])
    cover = float(((tt.y.values >= pt + q10) & (tt.y.values <= pt + q90)).mean() * 100)
    mae_n, mae_m = res["naive_no_change"][commodity]["test"]["mae_rs_qtl"], res[best][commodity]["test"]["mae_rs_qtl"]
    allskill = 1 - res[best]["all_series"]["test"]["mae_rs_qtl"] / res["naive_no_change"]["all_series"]["test"]["mae_rs_qtl"]
    final = _candidates(seed)[best].fit(L[cols], L.y)
    metrics = {"data_source": "Agmarknet monthly state prices (Govt. of India open data, GODL-India) via github.com/herrrickshaw/india-mandi-arrivals",
               "target": "next-month log price change per (commodity, state) series", "focus_commodity": commodity,
               "n_series": int(P.groupby(["commodity", "state"]).ngroups), "n_labelled_rows": int(len(L)),
               "splits": {"train_targets_to": TRAIN_END, "validation_targets_to": VAL_END, "test_targets": f"2025-01..{TEST_END}",
                          "n_train": int(len(tr)), "n_val": int(len(va)), "n_test": int(len(te))},
               "selected_model": best, "results": res,
               "test_skill_vs_naive_mae_pct": {"all_series": round(allskill * 100, 2), commodity: round((1 - mae_m / mae_n) * 100, 2)},
               "tamarind_test_bootstrap95_naive_minus_model_mae_rs_qtl": _boot_ci(tt, pt),
               "interval_logchange_q10_q90": [q10, q90], "interval_coverage_on_tamarind_test_pct": round(cover, 1),
               "deployment": "refit on all labelled rows; reported metrics come from the pre-test model (train+validation only)",
               "caveats": ["Skill over the naive baseline is modest; one-month-ahead prices are noisy.",
                           "Agmarknet prices mix grades/varieties at regulated mandis, not forest-gate prices.",
                           "Coverage of the Nov 2025+ period widened in Agmarknet; arrivals may not be comparable over time.",
                           "Decision support, not a price guarantee."],
               "sklearn_version": sklearn.__version__, "trained_on": date.today().isoformat()}
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": final, "q10": q10, "q90": q90, "features": cols}, out / "model.joblib")
    (out / "metrics.json").write_text(json.dumps(metrics, indent=2))
    return metrics


# ------------------------------------------------------------------ inference + insights
def load_model(out_dir=OUT):
    f = Path(out_dir) / "model.joblib"
    return joblib.load(f) if f.exists() else None


def modelled_states(commodity=COMMODITY, path=DATA, min_months=MIN_MONTHS):
    d = load_all(path); d = d[d.commodity == commodity]
    return sorted(s for s, g in d.groupby("state") if len(g) >= min_months)


def forecast(state, commodity=COMMODITY, path=DATA, out_dir=OUT):
    """Next-month forecast for one state from the latest observed month. Returns dict or raises ValueError."""
    art = load_model(out_dir)
    if art is None:
        raise ValueError("Price model not trained. Run: python -m ml.price_model")
    d = load_all(path); g = d[(d.commodity == commodity) & (d.state == state)]
    if len(g) < MIN_MONTHS:
        raise ValueError(f"{state}: fewer than {MIN_MONTHS} months of {commodity} data; no forecast.")
    f = series_features(g).dropna(subset=NUM)
    last = f.iloc[[-1]].copy(); last["group"] = g["group"].iloc[0]
    pred = float(art["model"].predict(last[art["features"]])[0])
    now = float(last.price_now.iloc[0])
    return {"state": state, "last_month": str(last.month.iloc[0]), "price_now_rs_qtl": now,
            "forecast_month": str(last.month.iloc[0] + 1), "forecast_rs_qtl": now * np.exp(pred),
            "low_rs_qtl": now * np.exp(pred + art["q10"]), "high_rs_qtl": now * np.exp(pred + art["q90"]),
            "expected_change_pct": (np.exp(pred) - 1) * 100,
            "interval_change_pct": [(np.exp(pred + art["q10"]) - 1) * 100, (np.exp(pred + art["q90"]) - 1) * 100]}


def seasonal_profile(commodity=COMMODITY, path=DATA, min_months=MIN_MONTHS):
    """Real seasonality: avg % deviation of price from its own 12-month mean, and arrivals share, by calendar month (modelled states)."""
    d = load_all(path); d = d[d.commodity == commodity]; out = []
    for s, g in d.groupby("state"):
        if len(g) < min_months:
            continue
        f = series_features(g)
        dev = (f.lp - f.lp.rolling(12, center=True, min_periods=9).mean()).dropna()
        arr = np.expm1(f.la); share = (arr / arr.rolling(12, center=True, min_periods=9).mean()).dropna()
        out.append(pd.DataFrame({"state": s, "month_no": [p.month for p in dev.index], "price_dev_pct": (np.exp(dev.values) - 1) * 100}).assign(
            arrivals_idx=share.reindex(dev.index).values))
    z = pd.concat(out)
    prof = z.groupby("month_no").agg(price_dev_pct=("price_dev_pct", "median"), arrivals_idx=("arrivals_idx", "median")).reset_index()
    prof["month"] = prof.month_no.map(lambda m: ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][m - 1])
    return prof


def price_history(commodity=COMMODITY, path=DATA):
    d = load_all(path); d = d[d.commodity == commodity].copy(); d["month"] = d["month"].astype(str)
    return d[["month", "state", "price_rs_qtl", "arrivals_t"]]


if __name__ == "__main__":
    m = train_and_evaluate()
    print(json.dumps({k: m[k] for k in ("selected_model", "n_series", "n_labelled_rows", "splits", "test_skill_vs_naive_mae_pct",
                                        "tamarind_test_bootstrap95_naive_minus_model_mae_rs_qtl", "interval_coverage_on_tamarind_test_pct")}, indent=1))
    for k in ("naive_no_change", "seasonal_mean", m["selected_model"]):
        print(k, json.dumps(m["results"][k]))
