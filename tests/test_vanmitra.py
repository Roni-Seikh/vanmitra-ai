import os, sys, json
from datetime import date, timedelta
import pytest
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from database import db
from modules.risk_assessment import assess
from modules.market_comparison import compare_offers
from modules import impact_analytics as ia, value_addition as va
from utils import exports, qr_generator
from utils.calculations import to_kg, offer_net
from utils.validation import validate_batch, validate_offer


@pytest.fixture
def p(tmp_path):
    path = str(tmp_path / "t.db"); db.init_db(path); return path


def good(**kw):
    d = dict(product="Tamarind", collection_date=date.today() - timedelta(days=5), region="Test district",
             quantity=100, unit="kg", storage_type="Sealed dry container", packaging_type="Lined HDPE bag")
    d.update(kw); return d


def test_db_init_persist_empty(p):
    assert db.list_batches(p).empty and db.list_offers(db_path=p).empty and ia.measured(p)["batches"] == 0
    c, e = validate_batch(good()); assert not e
    bid = db.create_batch(c, db_path=p)
    assert db.get_batch(bid, p)["quantity"] == 100        # re-read via a fresh connection = persisted
    assert db.get_batch("nope", p) is None


def test_duplicate_id_and_edit_history(p):
    c, _ = validate_batch(good())
    db.create_batch(c, batch_id="X1", db_path=p)
    with pytest.raises(ValueError): db.create_batch(c, batch_id="X1", db_path=p)
    c2, _ = validate_batch(good(quantity=150))
    assert db.update_batch("X1", c2, p) == ["quantity"]
    assert db.update_batch("X1", c2, p) == []
    ev = db.list_events("X1", p); assert list(ev.event_type) == ["registered", "edited"]


@pytest.mark.parametrize("bad", [dict(quantity=0), dict(quantity=None), dict(quantity="abc"), dict(region=" "),
    dict(collection_date=date.today() + timedelta(days=1)), dict(storage_humidity_pct=120), dict(storage_temp_c=99),
    dict(moisture_pct=-1), dict(unit="bucket"), dict(product="Gold"), dict(quantity=float("nan")),
    dict(provenance_status="verified", verifier="")])
def test_invalid_batches_rejected(bad):
    assert validate_batch(good(**bad))[1]


def test_offer_validation():
    assert validate_offer(dict(buyer="", price_per_unit=5, quantity=1, unit="kg"))[1]
    assert validate_offer(dict(buyer="A", price_per_unit=-5, quantity=1, unit="kg"))[1]
    assert not validate_offer(dict(buyer="A", price_per_unit=5, quantity=1, unit="kg"))[1]


def test_net_return_math_and_units():
    o = dict(price_per_unit=60, quantity=2, unit="quintal", transport=500, packaging=100, processing=50,
             other=50, deduction_pct=10, deduction_flat=100)
    r = offer_net(o)
    assert r["gross"] == 120 and r["kg"] == 200   # price is per quintal here
    assert r["net"] == pytest.approx(120 - (12 + 100) - 700)
    assert to_kg(500, "g") == 0.5 and to_kg(1, "tonne") == 1000
    with pytest.raises(ValueError): to_kg(1, "bucket")


def test_comparison_headline_price_vs_net():
    A = dict(buyer="A", grade="Ungraded", price_per_unit=70, quantity=100, unit="kg", transport=2000, packaging=0,
             processing=0, other=0, deduction_pct=0, deduction_flat=0)
    B = dict(A, buyer="B", price_per_unit=60, transport=100)
    r = compare_offers([A, B])
    assert r["best"]["buyer"] == "B" and any("headline price" in x for x in r["reasons"])
    assert compare_offers([])["best"] is None


def test_mixed_grade_unit_warnings():
    A = dict(buyer="A", grade="Grade A", price_per_unit=7000, quantity=1, unit="quintal")
    B = dict(buyer="B", grade="Grade B", price_per_unit=60, quantity=50, unit="kg")
    r = compare_offers([A, B], batch_kg=100)
    assert any("different grades" in w for w in r["warnings"])
    assert {round(x["qty_kg"]) for x in r["rows"]} == {100, 50}
    assert any("covers only" in w for w in r["warnings"])


def test_risk_edge_cases():
    base = good(storage_humidity_pct=50, storage_temp_c=25)
    low = assess(validate_batch(base)[0]); assert low["level"] == "Low"
    mold = assess(validate_batch({**base, "visible_mold": True})[0]); assert mold["level"] == "Elevated"
    nodata = assess(validate_batch(good())[0]); assert nodata["level"] == "Insufficient data" and nodata["missing"]
    bad = assess(validate_batch(good(storage_humidity_pct=90, storage_temp_c=40, storage_type="Open air / uncovered",
                                     packaging_type="Open / loose"))[0]); assert bad["level"] == "Elevated"
    old = assess(validate_batch(good(collection_date=date.today() - timedelta(days=100),
                                     storage_humidity_pct=50, storage_temp_c=25))[0]); assert old["score"] == 2


def test_product_specific_logic():
    mk = lambda prod, m: validate_batch(good(product=prod, moisture_pct=m, storage_humidity_pct=50, storage_temp_c=25))[0]
    assert assess(mk("Honey", 22))["score"] == 3 and assess(mk("Tamarind", 22))["score"] == 3
    assert assess(mk("Honey", 19))["score"] == 1 and assess(mk("Tamarind", 19))["score"] == 3   # different lines per product
    assert assess(mk("Honey", 13))["score"] == 0 and assess(mk("Tamarind", 13))["score"] == 1
    assert assess(mk("Other NTFP", 22))["score"] == 0      # no honey/tamarind moisture rule leaks into other products
    assert "not machine learning" in assess(mk("Tamarind", 10))["method"]


def test_qr_roundtrip_and_lookup(p):
    c, _ = validate_batch(good()); bid = db.create_batch(c, db_path=p)
    url = qr_generator.batch_url("http://x:8501/", bid)
    assert qr_generator.batch_id_from_url(url) == bid
    png = qr_generator.make_qr_png("http://x:8501", bid); assert png[:8] == b"\x89PNG\r\n\x1a\n"
    assert db.get_batch(qr_generator.batch_id_from_url(url), p)["batch_id"] == bid


def test_csv_export_and_summary(p):
    db.load_sample_data(p)
    csv = exports.df_to_csv(db.list_batches(p)).decode()
    assert csv.startswith("batch_id") and "VM-SAMPLE-TAM-001" in csv
    txt = exports.batch_summary_text(db.get_batch("VM-SAMPLE-TAM-001", p))
    assert "SAMPLE" in txt and "verified" in txt and "[user-reported]" in txt
    assert "[verified]" not in txt


def test_sample_loading_and_reset_safeguards(p):
    c, _ = validate_batch(good()); mine = db.create_batch(c, db_path=p)
    assert db.load_sample_data(p) == 2 and db.load_sample_data(p) == 0   # idempotent
    assert len(db.list_offers(db_path=p)) == 3
    assert db.remove_sample_data(p) == 2
    assert [b for b in db.list_batches(p).batch_id] == [mine]            # user data kept
    assert db.list_offers(db_path=p).empty                                # cascade
    with pytest.raises(PermissionError): db.wipe_all("delete", p)
    assert len(db.list_batches(p)) == 1
    db.wipe_all("DELETE", p); assert db.list_batches(p).empty


def test_impact_measured_vs_scenario(p):
    db.load_sample_data(p)
    m = ia.measured(p); assert m["batches"] == 2 and m["total_kg"] == 290 and m["assessed"] == 0
    for b in db.list_batches(p).to_dict("records"): db.save_assessment(b["batch_id"], assess(b), p)
    assert ia.measured(p)["assessed"] == 2
    assert m["spread_groups"] == 1 and m["recorded_spread"] == pytest.approx((57.3 - 59.8) * 0 + (59.8 - 57.3) * 250)
    s = ia.loss_scenario(1000, 50, 10, 30); assert s["hypothetical_value"] == pytest.approx(1500)
    with pytest.raises(ValueError): ia.loss_scenario(1000, 50, 120, 30)


def test_value_addition():
    r = va.evaluate(100, 60, 2, 3, 8)
    assert r["option_net"] == pytest.approx(97 * 60 * 1.08 - 200) and r["difference"] == pytest.approx(r["option_net"] - 6000)
    assert va.evaluate(100, 60, 2, 3, r["breakeven_uplift_pct"])["difference"] == pytest.approx(0, abs=1e-6)
    with pytest.raises(ValueError): va.evaluate(0, 60, 1, 0, 0)


def test_app_end_to_end(tmp_path, monkeypatch):
    """Drives the real Streamlit pages headlessly (streamlit.testing)."""
    from streamlit.testing.v1 import AppTest
    import config
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "e2e.db"))
    app = os.path.join(os.path.dirname(os.path.dirname(__file__)), "app.py")
    at = AppTest.from_file(app, default_timeout=60).run(); assert not at.exception
    at.sidebar.radio(key="page").set_value("data").run()
    [b for b in at.button if b.label == "Load SAMPLE data"][0].click().run(); assert not at.exception
    for pg in ["dash", "batch", "risk", "market", "value", "trace", "impact", "data"]:
        at.sidebar.radio(key="page").set_value(pg).run()
        assert not at.exception, (pg, at.exception)
    at.sidebar.radio(key="page").set_value("risk").run()
    [b for b in at.button if b.label == "Run screening"][0].click().run(); assert not at.exception
    assert any("Screening level" in s.value for s in at.subheader)
    at.sidebar.radio(key="page").set_value("market").run()
    at.selectbox(key="mkt_pick").set_value("VM-SAMPLE-TAM-001").run()
    assert any("Best recorded option" in s.value for s in at.success)


# ---------------- added in build round 2 ----------------
def test_qr_image_actually_decodes():
    """Decode the generated PNG with OpenCV: proves the QR image is scannable and holds the right URL."""
    cv2 = pytest.importorskip("cv2")
    import numpy as np
    png = qr_generator.make_qr_png("http://192.168.1.5:8501", "VM-SAMPLE-TAM-001")
    img = cv2.imdecode(np.frombuffer(png, np.uint8), cv2.IMREAD_GRAYSCALE)
    text, _, _ = cv2.QRCodeDetector().detectAndDecode(img)
    assert text == "http://192.168.1.5:8501/?batch=VM-SAMPLE-TAM-001"
    assert qr_generator.batch_id_from_url(text) == "VM-SAMPLE-TAM-001"


def test_tamarind_moisture_rule_sourced():
    b = lambda m: validate_batch(good(moisture_pct=m, storage_humidity_pct=50, storage_temp_c=25))[0]
    assert assess(b(10))["score"] == 0 and assess(b(13))["score"] == 1 and assess(b(16))["score"] == 3
    assert "botanikabharat" in assess(b(10))["rule_note"]


def test_ml_pipeline_synthetic_and_refusals(tmp_path):
    from ml import train_model as tm, predict as mp
    df = tm.make_synthetic_demo(tmp_path / "s.csv", n=400)
    m = tm.train(df, tmp_path / "demo", synthetic=True)
    assert m["SYNTHETIC_DEMO"] and m["n_train"] + m["n_test"] == 400
    assert m["model_test"]["f1"] >= m["baseline_most_frequent"]["f1"]
    assert (tmp_path / "demo" / "model.joblib").exists()
    with pytest.raises(ValueError, match="Refusing to train"):    # same data is NOT accepted as real
        tm.train(df.head(50), tmp_path / "real")
    with pytest.raises(ValueError): tm.train(df.assign(outcome=2), tmp_path / "x", synthetic=True)
    with pytest.raises(ValueError, match="Missing columns"): tm.train(df.drop(columns=["age_days"]), tmp_path / "x", synthetic=True)
    st_ = mp.status(real_dir=tmp_path / "none", demo_dir=tmp_path / "demo")
    assert st_["real_model"] is False and st_["demo_metrics"]["SYNTHETIC_DEMO"]
    assert mp.predict_risk(good(), real_dir=tmp_path / "demo") is None   # synthetic model must never score batches


def test_ml_real_path_loads_and_predicts(tmp_path):
    """Mechanics only: uses synthetic rows PRETENDING to be real, in a temp dir, to prove load+predict work."""
    from ml import train_model as tm, predict as mp
    import json
    df = tm.make_synthetic_demo(tmp_path / "s.csv", n=600)
    tm.train(df, tmp_path / "real", synthetic=False)               # passes size gate (>=200 rows, >=30/class)
    p = mp.predict_risk(validate_batch(good(storage_humidity_pct=80, storage_temp_c=33))[0], real_dir=tmp_path / "real")
    assert 0 <= p["probability_downgraded_or_lost"] <= 1


def test_reference_price_file_flagged():
    import pandas as pd, config
    r = pd.read_csv(config.ROOT / "data" / "reference_prices.csv")
    assert r.verification_status.str.contains("NEEDS VERIFICATION").all()


def test_bengali_ui_all_pages(tmp_path, monkeypatch):
    from streamlit.testing.v1 import AppTest
    import config
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "bn.db"))
    db.load_sample_data()
    at = AppTest.from_file(os.path.join(os.path.dirname(os.path.dirname(__file__)), "app.py"), default_timeout=60).run()
    at.sidebar.radio[0].set_value("বাংলা").run()
    for pg in ["dash", "batch", "risk", "market", "value", "trace", "impact", "data"]:
        at.sidebar.radio(key="page").set_value(pg).run()
        assert not at.exception, (pg, at.exception)
    at.sidebar.radio(key="page").set_value("batch").run()
    assert any("বনজ পণ্যের ব্যাচ" in m.value for m in at.markdown)   # translated page header really renders


def test_nan_from_pandas_counts_as_missing(p):
    db.load_sample_data(p)
    b = db.list_batches(p).set_index("batch_id").loc["VM-SAMPLE-TAM-001"].to_dict()
    b["batch_id"] = "VM-SAMPLE-TAM-001"
    r = assess(b)
    assert "product moisture reading" in r["missing"] and r["level"] == "Moderate"


# ---------------- round 3: real-data price model + market intelligence ----------------
import json as _json


def test_real_dataset_present_and_sane():
    from ml import price_model as pm
    d = pm.load_all()
    assert len(d) > 100_000 and (d.price_rs_qtl > 0).all()
    t = d[d.commodity == "Tamarind Fruit"]
    assert t.state.nunique() >= 6 and t.month.astype(str).min() == "2019-01"
    assert {"Karnataka", "Maharashtra"} <= set(pm.modelled_states())


def test_features_use_only_past_information():
    """Changing FUTURE prices must not change features of earlier months (no leakage)."""
    from ml import price_model as pm
    d = pm.load_all(); g = d[(d.commodity == "Tamarind Fruit") & (d.state == "Karnataka")].copy()
    base = pm.series_features(g)
    g2 = g.copy(); g2.loc[g2.index[-1], "price_rs_qtl"] *= 5; g2.loc[g2.index[-1], "arrivals_t"] *= 5
    alt = pm.series_features(g2)
    cols = pm.NUM
    assert base[cols].iloc[:-1].equals(alt[cols].iloc[:-1])          # rows before the changed month are identical


def test_price_model_pipeline_on_forest_subset(tmp_path):
    from ml import price_model as pm
    m = pm.train_and_evaluate(out_dir=tmp_path / "m", groups=["Forest Products"], min_split=30)
    assert (tmp_path / "m" / "model.joblib").exists() and m["splits"]["n_train"] > 100
    assert m["selected_model"] in m["results"] and "Tamarind Fruit" in m["results"]["naive_no_change"]
    assert set(m["test_skill_vs_naive_mae_pct"]) == {"all_series", "Tamarind Fruit"}
    with pytest.raises(ValueError): pm.train_and_evaluate(out_dir=tmp_path / "x", groups=["Forest Products"], commodity="Nonexistent")


def test_shipped_model_and_metrics_are_real_and_consistent():
    from ml import price_model as pm
    met = _json.loads((pm.OUT / "metrics.json").read_text())
    assert met["n_labelled_rows"] > 90_000 and met["splits"]["test_targets"].startswith("2025-01")
    assert met["test_skill_vs_naive_mae_pct"]["all_series"] > 0              # beats baseline on the big held-out set
    sel = met["selected_model"]; R = met["results"]
    gain = 1 - R[sel]["Tamarind Fruit"]["test"]["mae_rs_qtl"] / R["naive_no_change"]["Tamarind Fruit"]["test"]["mae_rs_qtl"]
    assert gain * 100 == pytest.approx(met["test_skill_vs_naive_mae_pct"]["Tamarind Fruit"], abs=0.02)   # reported skill matches raw metrics
    f = pm.forecast("Karnataka")
    assert f["low_rs_qtl"] < f["forecast_rs_qtl"] < f["high_rs_qtl"] and f["price_now_rs_qtl"] > 0
    with pytest.raises(ValueError): pm.forecast("Atlantis")


def test_seasonal_profile_shape():
    from ml import price_model as pm
    p = pm.seasonal_profile()
    assert list(p.month_no) == list(range(1, 13)) and p.arrivals_idx.max() > 1.5


def test_hold_or_sell_logic():
    from ml import price_model as pm
    from modules import market_intel as mi
    prof = pm.seasonal_profile()
    r = mi.hold_or_sell(100, 6, 4, prof, 0.5, 1.0, "Low")             # April -> October: real data says prices rise
    assert r["to_month"] == "Oct" and r["seasonal_change_pct"] > 5
    assert r["breakeven_price"] > 100
    assert mi.hold_or_sell(100, 6, 4, prof, 0.5, 1.0, "Elevated")["recommendation"] == "Sell or inspect now"
    assert mi.hold_or_sell(100, 6, 4, prof, 30, 1.0, "Low")["recommendation"] == "Sell now"     # heavy storage cost kills the gain
    for bad in [dict(price_now=0), dict(months=0), dict(months=13), dict(monthly_cost=-1), dict(monthly_loss_pct=100)]:
        kw = dict(price_now=100, months=3, from_month_no=4, profile=prof, monthly_cost=0.5, monthly_loss_pct=1, risk_level="Low"); kw.update(bad)
        with pytest.raises(ValueError): mi.hold_or_sell(**kw)


def test_market_intelligence_page_runs(tmp_path, monkeypatch):
    from streamlit.testing.v1 import AppTest
    import config
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "mi.db")); db.load_sample_data()
    at = AppTest.from_file(os.path.join(os.path.dirname(os.path.dirname(__file__)), "app.py"), default_timeout=90).run()
    at.sidebar.radio(key="page").set_value("intel").run()
    assert not at.exception, at.exception
    assert len(at.tabs) == 4 and any("Model card" in e.label for e in at.expander)
    at.sidebar.radio(key="page").set_value("dash").run(); assert not at.exception
