"""VanMitra AI — BioNexis | Bio-Economy Hackathon 2026. Run: streamlit run app.py"""
import json
from datetime import date, datetime
import pandas as pd
import plotly.express as px
import streamlit as st
import config
from database import db
from modules import market_comparison as mc, value_addition as va, impact_analytics as ia
from modules.risk_assessment import assess
from utils import exports, qr_generator
from utils.i18n import BN
from ml import predict as mlp, price_model as pm
from modules import market_intel as mi
from utils.calculations import to_kg
from utils.validation import validate_batch, validate_offer

st.set_page_config(page_title="VanMitra AI · BioNexis", page_icon="🌿", layout="wide")
db.init_db()

NAV = {"dash": ("Dashboard", "ড্যাশবোর্ড"), "batch": ("Batches", "ব্যাচ"),
       "risk": ("Risk Screening", "ঝুঁকি যাচাই"), "market": ("Buyer Offers", "ক্রেতার দর তুলনা"), "intel": ("Market Intelligence", "বাজার বিশ্লেষণ"),
       "value": ("Value Addition", "মূল্য সংযোজন"), "trace": ("Traceability", "ট্রেসেবিলিটি"),
       "impact": ("Impact", "প্রভাব"), "data": ("Data & Settings", "ডেটা ও সেটিংস")}

st.markdown("""<style>
:root{--g:#2f5d3a;--gd:#1c3d26;--l:#eaf2e6;--gold:#b8860b;--ink:#1f2a22}
html,body,[class*="css"]{font-family:"Segoe UI",Inter,system-ui,sans-serif}
.block-container{padding-top:1.2rem;max-width:1220px}
h1,h2,h3{color:var(--gd);letter-spacing:-.01em}
.vm-hero{background:linear-gradient(120deg,#1c3d26 0%,#2f6b44 70%,#3f8156 100%);color:#fff;padding:1.3rem 1.6rem;border-radius:14px;margin-bottom:1.1rem;box-shadow:0 6px 18px rgba(28,61,38,.18)}
.vm-hero h2{color:#fff!important;margin:0 0 .25rem 0;font-size:1.65rem}
.vm-hero span{color:#dcebd9;font-size:1rem}
.chip{display:inline-block;padding:.14rem .6rem;border-radius:999px;font-size:.74rem;font-weight:700;margin:0 .35rem .35rem 0;border:1px solid}
.chip.real{background:#e4f3e7;color:#1d6b35;border-color:#9ccfa8}.chip.sample{background:#fff4d6;color:#8a6200;border-color:#e6c668}
.chip.est{background:#e7eefb;color:#2a4d8f;border-color:#a9bde6}.chip.rule{background:#f1e9f7;color:#5b3a7a;border-color:#cdb6e2}
.vm-card{background:#fff;border:1px solid #dfe8da;border-radius:12px;padding:1rem 1.1rem;height:100%;box-shadow:0 2px 8px rgba(0,0,0,.04)}
.vm-card h4{margin:.1rem 0 .4rem 0;color:var(--g)} .vm-card p{margin:0;color:#44514a;font-size:.93rem}
[data-testid=stMetric]{background:#f7f9f5;border:1px solid #dfe8da;padding:.7rem .9rem;border-radius:12px}
[data-testid=stSidebar]{background:#f3f7f0}
.stButton>button[kind=primary],.stFormSubmitButton>button{background:var(--g);border:0;border-radius:8px}
.vm-note{font-size:.85rem;color:#555}
</style>""", unsafe_allow_html=True)

import plotly.graph_objects as go
COLORS = ["#2f5d3a", "#b8860b", "#6fa37d", "#c0562b", "#4a7ba7", "#8e6c8a"]


def style(fig, h=340):
    fig.update_layout(height=h, margin=dict(t=40, b=10, l=10, r=10), colorway=COLORS, font=dict(family="Segoe UI, sans-serif"),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", legend=dict(orientation="h", y=-0.2))
    fig.update_xaxes(showgrid=False); fig.update_yaxes(gridcolor="#e6ece3")
    return fig


def chips(*items):
    cls = {"REAL DATA": "real", "SAMPLE": "sample", "ESTIMATE": "est", "RULE-BASED": "rule"}
    st.markdown("".join(f'<span class="chip {cls.get(i, "est")}">{i}</span>' for i in items), unsafe_allow_html=True)

lang = st.sidebar.radio("Language / ভাষা", ["English", "বাংলা"], horizontal=True)
L = 0 if lang == "English" else 1


def T(x):
    return BN.get(x, x) if L else x

qp = st.query_params.get("batch")
if qp and "page" not in st.session_state:
    st.session_state["page"], st.session_state["trace_pick"] = "trace", qp
st.sidebar.markdown(f"### 🌿 {config.APP_NAME}\n**Team {config.TEAM}** · Brainware University")
page = st.sidebar.radio("Menu", list(NAV), format_func=lambda k: NAV[k][L], key="page")
st.sidebar.caption("Bio-Economy Hackathon 2026 · Forest-Based Bio-Economy track")
st.sidebar.warning(BN["disclaimer"] if L else "Estimates & SAMPLE data are illustrative. Not lab tests, certification or market quotes.")


def hero(title, sub):
    st.markdown(f'<div class="vm-hero"><h2>{title}</h2><span>{sub}</span></div>', unsafe_allow_html=True)


def inr(x):
    return f"₹{x:,.0f}"


def pick_batch(key, label=T("Select batch")):
    df = db.list_batches()
    if df.empty:
        st.info("No batches yet. Register one in **Batches**, or load the SAMPLE demo data in **Data & Settings**.")
        return None
    lab = {r.batch_id: f"{r.batch_id} · {r.product} · {r.quantity:g} {r.unit}" + (" · SAMPLE" if r.is_sample else "")
           for r in df.itertuples()}
    return st.selectbox(label, list(lab), format_func=lab.get, key=key)


def errors_box(errs):
    for e in errs:
        st.error(e)


# ---------------------------------------------------------------- Dashboard
if page == "dash":
    hero(f"{config.APP_NAME}: forest-produce loss prevention & fair-market assistant",
         T("Helps collectors, producer groups and small forest-product businesses record batches, screen handling risks, compare buyer offers on net return, and share a traceable batch record."))
    chips("REAL DATA", "RULE-BASED", "ESTIMATE", "SAMPLE")
    k = st.columns(4)
    for col, (ico, h, t) in zip(k, [("🧪", "Screen the risk", "Product-specific, explainable storage checks"), ("📈", "Read the market", "Real government price history and a tested forecast"),
                                    ("⚖️", "Compare net return", "Every cost and deduction, per kg"), ("🔗", "Prove the record", "QR batch page with honest status labels")]):
        col.markdown(f'<div class="vm-card"><h4>{ico} {h}</h4><p>{t}</p></div>', unsafe_allow_html=True)
    st.write("")
    m = ia.measured()
    c = st.columns(5)
    c[0].metric(T("Batches"), m["batches"]); c[1].metric(T("Recorded quantity"), f"{m['total_kg']:,.0f} kg")
    c[2].metric(T("Batches screened"), m["assessed"]); c[3].metric(T("Elevated screening"), m["elevated"])
    c[4].metric(T("Offers recorded"), m["offers"])
    if m["batches"] == 0:
        st.info("Empty database. Go to **Data & Settings → Load SAMPLE data** to start the demo.")
    else:
        a, b = st.columns(2)
        with a:
            st.subheader(T("Screening-level overview"))
            if m["latest_levels"]:
                fig = px.bar(x=list(m["latest_levels"]), y=list(m["latest_levels"].values()),
                             labels={"x": "Latest screening level", "y": T("Batches")},
                             color=list(m["latest_levels"]), color_discrete_map={
                                 "Low": "#4c9a5b", "Moderate": "#e0a030", "Elevated": "#c0392b", "Insufficient data": "#999"})
                fig.update_layout(showlegend=False)
                st.plotly_chart(style(fig, 300), width="stretch")
            else:
                st.caption("No batch screened yet — open **Risk Screening**.")
        with b:
            st.subheader(T("Recorded offers (measured from entered data)"))
            st.write(f"Gross: **{inr(m['gross_recorded'])}** · Net: **{inr(m['net_recorded'])}** across {m['offers']} offers")
            st.write(f"Like-for-like net-return spread between best and worst offers (same batch & grade): "
                     f"**{inr(m['recorded_spread'])}** over {m['spread_groups']} comparison group(s). "
                     "This is a recorded difference, not realised savings.")
            st.subheader(T("Traceability"))
            bd = db.list_batches()
            st.write(f"{(bd.provenance_status != 'unavailable').sum()} of {len(bd)} batches have provenance info "
                     f"(**{(bd.provenance_status == 'verified').sum()} verified**, "
                     f"{(bd.provenance_status == 'documented').sum()} documented, "
                     f"{(bd.provenance_status == 'user-reported').sum()} user-reported).")
        st.subheader(T("Batches"))
        st.dataframe(bd[["batch_id", "product", "collection_date", "quantity", "unit", "region", "is_sample"]],
                     width="stretch", hide_index=True)
    ph = pm.price_history(); lastm = ph.month.max()
    snap = ph[ph.month == ph[ph.state.isin(pm.modelled_states())].month.max()].copy()
    snap = snap[snap.state.isin(pm.modelled_states())].assign(kg=lambda x: x.price_rs_qtl / 100).sort_values("kg")
    fig = px.bar(snap, x="kg", y="state", orientation="h", title=f"Real market snapshot: tamarind fruit mandi price by state, {snap.month.iloc[0]} (₹/kg)",
                 labels={"kg": "₹/kg", "state": ""})
    fig.update_traces(marker_color="#2f5d3a")
    st.plotly_chart(style(fig, 300), width="stretch"); chips("REAL DATA")
    st.caption("Agmarknet wholesale mandi prices (mixed grades); not what a collector necessarily receives. " + config.DISCLAIMER)

# ---------------------------------------------------------------- Batches
elif page == "batch":
    hero(T("Forest-product batches"), T("Register, edit and review the history of each batch. All entries are user-reported."))

    def batch_form(key, d=None):
        d = d or {}
        with st.form(key):
            a, b, c = st.columns(3)
            prods = list(config.PRODUCTS)
            product = a.selectbox(T("Product"), prods, index=prods.index(d["product"]) if d.get("product") in prods else 0)
            cdate = b.date_input(T("Collection date"), value=datetime.strptime(d["collection_date"], "%Y-%m-%d").date()
                                 if d.get("collection_date") else date.today(), max_value=date.today())
            region = c.text_input(T("Collection region (district/state level)"), d.get("region", ""),
                                  help="Do not enter exact locations of threatened or protected resources.")
            a, b, c = st.columns(3)
            qty = a.number_input(T("Quantity"), min_value=0.0, value=float(d.get("quantity", 0) or 0), step=1.0)
            units = list(config.UNIT_TO_KG)
            unit = b.selectbox(T("Unit"), units, index=units.index(d.get("unit", "kg")))
            group = c.text_input(T("Producer group ID (optional)"), d.get("producer_group", ""))
            a, b = st.columns(2)
            st_ = config.STORAGE_TYPES; pk = config.PACKAGING_TYPES
            storage = a.selectbox(T("Storage type"), st_, index=st_.index(d["storage_type"]) if d.get("storage_type") in st_ else 0)
            pack = b.selectbox(T("Packaging"), pk, index=pk.index(d["packaging_type"]) if d.get("packaging_type") in pk else 0)
            a, b, c = st.columns(3)
            temp = a.number_input(T("Storage temperature °C (optional)"), value=d.get("storage_temp_c"), step=0.5)
            hum = b.number_input(T("Storage humidity % (optional)"), value=d.get("storage_humidity_pct"), step=1.0)
            moist = c.number_input(T("Product moisture % (optional, measured)"), value=d.get("moisture_pct"), step=0.1)
            a, b = st.columns(2)
            mold = a.checkbox(T("Visible mould observed"), bool(d.get("visible_mold")))
            pest = b.checkbox(T("Pest signs observed"), bool(d.get("pest_signs")))
            notes = st.text_area(T("Handling notes"), d.get("handling_notes", ""))
            ps = config.PROVENANCE_STATUSES
            a, b, c = st.columns(3)
            pstat = a.selectbox(T("Provenance status"), ps, index=ps.index(d.get("provenance_status", "user-reported")),
                                help="'verified' needs a named verifier. This app does not verify anything itself.")
            pref = b.text_input(T("Provenance reference (permit/receipt no.)"), d.get("provenance_ref", ""))
            ver = c.text_input(T("Verified by (if verified)"), d.get("verifier", ""))
            a, b = st.columns(2)
            sstat = a.selectbox(T("Sustainability documentation"), ps, index=ps.index(d.get("sustainability_doc_status", "unavailable")))
            sref = b.text_input(T("Sustainability document reference"), d.get("sustainability_doc_ref", ""))
            ok = st.form_submit_button(T("Save batch"), type="primary")
        if ok:
            raw = dict(product=product, collection_date=cdate, region=region, quantity=qty or None, unit=unit,
                       storage_type=storage, packaging_type=pack, storage_temp_c=temp, storage_humidity_pct=hum,
                       moisture_pct=moist, visible_mold=mold, pest_signs=pest, handling_notes=notes,
                       producer_group=group, provenance_status=pstat, provenance_ref=pref, verifier=ver,
                       sustainability_doc_status=sstat, sustainability_doc_ref=sref, is_sample=d.get("is_sample", 0))
            return validate_batch(raw)
        return None

    t1, t2 = st.tabs([T("➕ Register batch"), T("📋 Browse / edit / history")])
    with t1:
        r = batch_form("new_batch")
        if r:
            clean, errs = r
            if errs:
                errors_box(errs)
            else:
                bid = db.create_batch(clean)
                st.success(f"Batch registered: **{bid}**. Next: Risk Screening, Buyer Offers, Traceability.")
    with t2:
        bid = pick_batch("browse_pick")
        if bid:
            batch = db.get_batch(bid)
            if batch["is_sample"]:
                st.caption("SAMPLE record — illustrative demonstration data.")
            r = batch_form(f"edit_{bid}", batch)
            if r:
                clean, errs = r
                if errs:
                    errors_box(errs)
                else:
                    ch = db.update_batch(bid, clean)
                    st.success(f"Updated: {', '.join(ch)}" if ch else "No changes to save.")
            st.subheader(T("History"))
            st.dataframe(db.list_events(bid), width="stretch", hide_index=True)

# ---------------------------------------------------------------- Risk
elif page == "risk":
    hero(T("Post-harvest risk screening"), T("A transparent, product-specific checklist — not a spoilage prediction."))
    st.info("Method: rule-based screening (not machine learning). Thresholds are team-set heuristics, not validated "
            "cut-offs. No labelled public dataset was verified for training a model — see docs/limitations.md.")
    bid = pick_batch("risk_pick")
    if bid:
        batch = db.get_batch(bid)
        run = st.button(T("Run screening"), type="primary")
        if run or st.session_state.get("risk_last") == bid:
            res = assess(batch)
            if run:  # every explicit run is saved to the batch's screening history
                db.save_assessment(bid, res)
                st.session_state["risk_last"] = bid
            color = {"Low": "🟢", "Moderate": "🟠", "Elevated": "🔴", "Insufficient data": "⚪"}[res["level"]]
            st.subheader(f"{color} Screening level: {res['level']}  (score {res['score']})")
            st.markdown(T("**Factors that influenced this result**"))
            st.dataframe(pd.DataFrame(res["factors"]).rename(columns={"factor": "Factor", "value": "Recorded",
                         "points": "Points", "why": "Reason"}), width="stretch", hide_index=True)
            a, b = st.columns(2)
            with a:
                st.markdown(T("**Recommended next steps**"))
                for s in res["next_steps"]:
                    st.write("• " + s)
            with b:
                st.markdown(T("**Missing information that could change the result**"))
                for s in (res["missing"] or ["None of the key inputs are missing."]):
                    st.write("• " + s)
            st.caption(res["rule_note"]); st.warning(res["limitations"])
        with st.expander("ML readiness (honest status)"):
            ms = mlp.status()
            (st.success if ms["real_model"] else st.info)(ms["message"])
            if ms["real_model"]:
                st.json(ms["real_metrics"])
            elif ms["demo_metrics"]:
                st.warning("SYNTHETIC pipeline check only (labels came from our own rules): " + ms["demo_metrics"]["warning"])
                st.caption(f"Rows {ms['demo_metrics']['n_rows']}, selected {ms['demo_metrics']['selected_model']}. "
                           "These numbers are NOT evidence of real-world accuracy and are not used for screening.")
        hist = db.list_assessments(bid)
        if len(hist):
            st.markdown(T("**Screening history for this batch**"))
            st.dataframe(hist[["created_at", "level", "score"]], width="stretch", hide_index=True)
        if st.button(T("Reset screening view")):
            st.session_state.pop("risk_last", None); st.rerun()

# ---------------------------------------------------------------- Market
elif page == "market":
    hero(T("Buyer-offer comparison"), T("Net return = sale revenue − deductions − selling costs. Everything is shown."))
    bid = pick_batch("mkt_pick")
    if bid:
        batch = db.get_batch(bid)
        kg = to_kg(batch["quantity"], batch["unit"])
        with st.expander(T("➕ Add a buyer offer"), expanded=db.list_offers(bid).empty):
            with st.form(f"offer_{bid}"):
                a, b, c, d_ = st.columns(4)
                buyer = a.text_input(T("Buyer name / ID")); price = b.number_input(T("Price per unit (₹)"), min_value=0.0, step=1.0)
                q = c.number_input(T("Quantity offered"), min_value=0.0, value=float(batch["quantity"]))
                units = list(config.UNIT_TO_KG)
                u = d_.selectbox(T("Unit"), units, index=units.index(batch["unit"]))
                a, b, c, d_ = st.columns(4)
                grade = a.selectbox(T("Grade / spec"), config.GRADES)
                tr = b.number_input(T("Transport (₹ total)"), min_value=0.0); pk = c.number_input(T("Packaging (₹)"), min_value=0.0)
                pr = d_.number_input(T("Processing (₹)"), min_value=0.0)
                a, b, c = st.columns(3)
                oth = a.number_input(T("Other costs (₹)"), min_value=0.0)
                dp = b.number_input(T("Quality deduction (%)"), min_value=0.0, max_value=100.0)
                df_ = c.number_input(T("Flat deduction (₹)"), min_value=0.0)
                ok = st.form_submit_button(T("Save offer"), type="primary")
            if ok:
                clean, errs = validate_offer(dict(buyer=buyer, price_per_unit=price or None, quantity=q or None, unit=u,
                    grade=grade, transport=tr, packaging=pk, processing=pr, other=oth, deduction_pct=dp, deduction_flat=df_))
                if errs:
                    errors_box(errs)
                else:
                    db.add_offer(bid, clean); st.success("Offer saved."); st.rerun()
        offers = db.list_offers(bid)
        if offers.empty:
            st.info("No offers for this batch yet. Add at least two to compare.")
        else:
            crit = st.radio(T("Rank by"), ["net_per_kg", "net"], horizontal=True,
                            format_func=lambda x: "Net return per kg (fair for different quantities)" if x == "net_per_kg" else "Total net return")
            res = mc.compare_offers(offers.to_dict("records"), crit, kg)
            best = res["best"]
            st.success(f"Best recorded option under your criterion: **{best['buyer']}** — net {inr(best['net'])} "
                       f"(₹{best['net_per_kg']:.2f}/kg)")
            for r in res["reasons"]:
                st.write("• " + r)
            for w in res["warnings"]:
                st.warning(w)
            tbl = pd.DataFrame(res["rows"]).drop(columns=["is_sample"]).rename(columns={
                "buyer": "Buyer", "grade": "Grade", "qty_kg": "Qty (kg)", "gross": "Gross ₹", "deductions": "Deductions ₹",
                "cost_transport": "Transport ₹", "cost_packaging": "Packaging ₹", "cost_processing": "Processing ₹",
                "cost_other": "Other ₹", "total_costs": "Total costs ₹", "net": "NET ₹", "net_per_kg": "Net ₹/kg"})
            st.dataframe(tbl.round(2), width="stretch", hide_index=True)
            fig = px.bar(tbl, x="Buyer", y="Net ₹/kg", color="Grade", height=300)
            st.plotly_chart(fig, width="stretch")
            st.markdown(T("**Assumptions**")); [st.write("• " + a) for a in res["assumptions"]]
            refs = pd.read_csv(config.ROOT / "data" / "reference_prices.csv")
            refs = refs[refs["product"] == batch["product"]]
            if len(refs):
                with st.expander("Reference price (UNVERIFIED — not used in ranking)"):
                    for r_ in refs.itertuples():
                        st.write(f"**{r_.item}: ₹{r_.reference_inr_per_kg}/kg** · {r_.source_name}")
                        st.caption(f"Applicability: {r_.applicability}. Status: {r_.verification_status}. {r_.notes}")
                        st.caption(r_.source_url)
            st.caption("Reference prices (e.g. MSP) are intentionally not shown: no verified source for this product/"
                       "region/date was integrated. Sample prices are not market quotations.")
            st.download_button(T("Download comparison CSV"), exports.df_to_csv(tbl), f"offers_{bid}.csv", "text/csv")
            with st.expander("Remove an offer"):
                oid = st.selectbox("Offer", offers.id, format_func=lambda i: offers.set_index("id").loc[i, "buyer"])
                if st.button("Delete offer"):
                    db.delete_offer(int(oid)); st.rerun()

# ---------------------------------------------------------------- Value addition
elif page == "intel":
    hero(T("Market intelligence from real government data"),
         T("Real Agmarknet mandi prices and arrivals (2019-2026), a trained forecasting model with published test results, and a hold-or-sell advisor tied to your batch."))
    chips("REAL DATA", "ESTIMATE")
    hist = pm.price_history()
    mstates = pm.modelled_states()
    t1, t2, t3, t4 = st.tabs(["📈 Price history", "🗓 Seasonality", "🔮 Next-month forecast", "⚖️ Hold or sell?"])
    with t1:
        pick = st.multiselect("States", sorted(hist.state.unique()), default=mstates)
        h = hist[hist.state.isin(pick)].assign(date=lambda x: pd.to_datetime(x.month), price_kg=lambda x: x.price_rs_qtl / 100)
        fig = px.line(h, x="date", y="price_kg", color="state", labels={"price_kg": "Mandi price (₹/kg)", "date": ""},
                      title="Tamarind fruit: monthly weighted-average mandi price (Agmarknet)")
        st.plotly_chart(style(fig, 380), width="stretch")
        st.caption("Source: Government of India Agmarknet via an open GODL-India re-publication. Wholesale mandi prices (mixed grades), "
                   "not forest-gate prices; the latest month is in progress.")
    with t2:
        prof = pm.seasonal_profile()
        fig = go.Figure()
        fig.add_bar(x=prof.month, y=prof.price_dev_pct, name="Price vs yearly average (%)", marker_color="#2f5d3a")
        fig.add_scatter(x=prof.month, y=prof.arrivals_idx, name="Arrivals index (1 = average)", yaxis="y2", mode="lines+markers", line=dict(color="#b8860b", width=3))
        fig.update_layout(title="Tamarind seasonality (median across modelled states)", yaxis=dict(title="% vs 12-month mean"),
                          yaxis2=dict(title="Arrivals index", overlaying="y", side="right", showgrid=False))
        st.plotly_chart(style(fig, 380), width="stretch")
        pk, lo, hi = prof.loc[prof.arrivals_idx.idxmax(), "month"], prof.loc[prof.price_dev_pct.idxmin(), "month"], prof.loc[prof.price_dev_pct.idxmax(), "month"]
        st.info(f"In this data, tamarind arrivals peak in **{pk}**; prices tend to be lowest in **{lo}** "
                f"({prof.price_dev_pct.min():+.1f}%) and highest in **{hi}** ({prof.price_dev_pct.max():+.1f}%). "
                "A pattern in past years, not a promise.")
    with t3:
        stt = st.selectbox("State (with enough history)", mstates, index=mstates.index("Karnataka") if "Karnataka" in mstates else 0)
        try:
            fc = pm.forecast(stt)
            a, b, c = st.columns(3)
            a.metric(f"Latest ({fc['last_month']})", f"₹{fc['price_now_rs_qtl'] / 100:,.0f}/kg")
            b.metric(f"Forecast ({fc['forecast_month']})", f"₹{fc['forecast_rs_qtl'] / 100:,.0f}/kg", f"{fc['expected_change_pct']:+.1f}%", delta_color="off")
            c.metric("Likely range (about 80%)", f"₹{fc['low_rs_qtl'] / 100:,.0f}–{fc['high_rs_qtl'] / 100:,.0f}")
            hh = hist[hist.state == stt].tail(24).assign(date=lambda x: pd.to_datetime(x.month), kg=lambda x: x.price_rs_qtl / 100)
            fig = go.Figure()
            fig.add_scatter(x=hh.date, y=hh.kg, mode="lines+markers", name="Observed", line=dict(color="#2f5d3a"))
            fd = pd.to_datetime(fc["forecast_month"])
            fig.add_scatter(x=[fd], y=[fc["forecast_rs_qtl"] / 100], mode="markers", name="Forecast", marker=dict(size=12, color="#b8860b"),
                            error_y=dict(type="data", symmetric=False, array=[(fc["high_rs_qtl"] - fc["forecast_rs_qtl"]) / 100],
                                         arrayminus=[(fc["forecast_rs_qtl"] - fc["low_rs_qtl"]) / 100]))
            fig.update_layout(title=f"{stt}: last 24 months and next-month forecast (₹/kg)")
            st.plotly_chart(style(fig, 360), width="stretch")
        except ValueError as e:
            st.error(str(e))
        met = json.loads((pm.OUT / "metrics.json").read_text()) if (pm.OUT / "metrics.json").exists() else None
        if met:
            with st.expander("Model card: how good is this forecast? (real evaluation)", expanded=True):
                R, sel = met["results"], met["selected_model"]
                rows = []
                for nm, lab in (("all_series", f"All {met['n_series']:,} series"), (met["focus_commodity"], "Tamarind fruit")):
                    rows.append({"Test set (2025-01 to 2026-09)": lab, "Rows": R[sel][nm]["test"]["n"],
                                 "Naive 'no change' MAE ₹/qtl": R["naive_no_change"][nm]["test"]["mae_rs_qtl"],
                                 "Our model MAE ₹/qtl": R[sel][nm]["test"]["mae_rs_qtl"],
                                 "Improvement": f"{met['test_skill_vs_naive_mae_pct'][nm]:+.1f}%"})
                st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
                lo_, hi_ = met["tamarind_test_bootstrap95_naive_minus_model_mae_rs_qtl"]
                st.write(f"Trained on {met['n_labelled_rows']:,} real monthly records ({met['n_series']:,} commodity-state series), chronological split: "
                         f"train to {met['splits']['train_targets_to']}, validate 2024, test once on 2025-01..2026-09. Selected model: **{sel}**.")
                st.warning(f"Honest reading: across all series the gain over the baseline is clear (large test set). For tamarind alone it is {met['test_skill_vs_naive_mae_pct'][met['focus_commodity']]:+.1f}% "
                           f"but the 95% bootstrap interval of the gain is ₹{lo_:.0f} to ₹{hi_:.0f}/qtl, which includes zero, so it is promising rather than proven. "
                           f"Forecast ranges covered {met['interval_coverage_on_tamarind_test_pct']:.0f}% of tamarind test outcomes. " + " ".join(met["caveats"][:2]))
    with t4:
        bd = db.list_batches(); tb = bd[bd["product"] == "Tamarind"] if len(bd) else bd
        if tb.empty:
            st.info("Register or load a tamarind batch first (Batches, or Data & Settings → Load SAMPLE data).")
        else:
            lab = {r.batch_id: f"{r.batch_id} · {r.quantity:g} {r.unit}" + (" · SAMPLE" if r.is_sample else "") for r in tb.itertuples()}
            bid = st.selectbox("Tamarind batch", list(lab), format_func=lab.get, key="hs_pick")
            batch = db.get_batch(bid); la = db.list_assessments(bid)
            level = la.level.iloc[0] if len(la) else assess(batch)["level"]
            st.write(f"Screening level used: **{level}**" + ("" if len(la) else " (computed now; run Risk Screening to save it)"))
            offs = db.list_offers(bid)
            default_price = float((offs.price_per_unit / offs.unit.map(config.UNIT_TO_KG)).max()) if len(offs) else 0.0
            a, b, c, d_ = st.columns(4)
            p0 = a.number_input("Selling price today (₹/kg)", min_value=0.0, value=round(default_price, 2), key=f"hp{bid}")
            mo = b.slider("Hold for (months)", 1, 12, 3, key=f"hm{bid}")
            cost = c.number_input("Storage cost (₹/kg/month)", min_value=0.0, value=0.5, key=f"hc{bid}", help="Your own estimate.")
            loss = d_.number_input("Assumed loss (%/month)", 0.0, 99.0, mi.DEFAULT_MONTHLY_LOSS_PCT[level], key=f"hl{bid}{level}",
                                   help="A placeholder assumption linked to the screening level, not measured data. Replace with your own records.")
            if p0 <= 0:
                st.info("Enter today's selling price (or record a buyer offer for this batch).")
            else:
                try:
                    r = mi.hold_or_sell(p0, mo, date.today().month, pm.seasonal_profile(), cost, loss, level)
                    (st.error if r["recommendation"] == "Sell or inspect now" else st.success if r["recommendation"] == "Holding may pay" else st.warning)(
                        f"**{r['recommendation']}** (hold to {r['to_month']})")
                    m = st.columns(3)
                    m[0].metric("Sell now", f"₹{r['sell_value']:.2f}/kg"); m[1].metric(f"Hold → {r['to_month']}", f"₹{r['hold_value']:.2f}/kg", f"{r['diff_pct']:+.1f}%", delta_color="off")
                    m[2].metric("Break-even price", f"₹{r['breakeven_price']:.2f}/kg")
                    for x in r["reasons"]:
                        st.write("• " + x)
                    chips("ESTIMATE", "REAL DATA", "RULE-BASED"); st.caption(r["note"])
                except ValueError as e:
                    st.error(str(e))

elif page == "value":
    hero(T("Value-addition decision support"), T("Compare selling raw vs. a possible improvement. All defaults are editable placeholders."))
    bid = pick_batch("va_pick")
    if bid:
        batch = db.get_batch(bid)
        opts = va.PATHWAYS[batch["product"]]
        pw = st.selectbox(T("Pathway"), opts, format_func=lambda p: p["name"])
        st.caption(pw["why"])
        kg = to_kg(batch["quantity"], batch["unit"])
        offers = db.list_offers(bid)
        default_price = float(offers.price_per_unit.iloc[0] / config.UNIT_TO_KG[offers.unit.iloc[0]]) if len(offers) else 0.0
        a, b, c = st.columns(3)
        price = a.number_input(T("Raw selling price (₹/kg)"), min_value=0.0, value=default_price, key=f"p{bid}")
        cost = b.number_input(T("Added cost (₹/kg)"), min_value=0.0, value=pw["cost_per_kg"], key=f"c{pw['name']}")
        fixed = c.number_input(T("Fixed cost (₹)"), min_value=0.0, value=0.0, key=f"f{pw['name']}")
        a, b = st.columns(2)
        loss = a.number_input(T("Weight loss in processing (%)"), 0.0, 99.0, pw["loss_pct"], key=f"l{pw['name']}")
        up = b.number_input(T("Price uplift expected (%)"), -100.0, 500.0, pw["uplift_pct"], key=f"u{pw['name']}")
        if price <= 0:
            st.info("Enter a raw selling price (or record an offer first).")
        else:
            r = va.evaluate(kg, price, cost, loss, up, fixed)
            m = st.columns(4)
            m[0].metric(T("Sell raw"), inr(r["baseline_net"])); m[1].metric(T("Option net"), inr(r["option_net"]))
            m[2].metric(T("Difference"), inr(r["difference"])); m[3].metric(T("Break-even uplift"), f"{r['breakeven_uplift_pct']:.1f}%")
            st.write(f"Output after loss: {r['output_kg']:.1f} kg · option revenue {inr(r['option_revenue'])} · "
                     f"option costs {inr(r['option_costs'])}")
            (st.success if r["difference"] > 0 else st.warning)(
                "Under these assumptions the option " + ("beats" if r["difference"] > 0 else "does not beat") + " selling raw.")
        st.warning("ILLUSTRATIVE: " + va.CAUTION)

# ---------------------------------------------------------------- Traceability
elif page == "trace":
    hero(T("QR batch traceability"), T("Each QR links to a batch record. It does not prove authenticity, safety or sustainability."))
    df = db.list_batches()
    if df.empty:
        st.info("No batches yet.")
    else:
        ids = list(df.batch_id)
        if st.session_state.get("trace_pick") not in ids:
            st.session_state.pop("trace_pick", None)
            if qp:
                st.error(f"Batch '{qp}' was not found in this database.")
        bid = st.selectbox(T("Batch"), ids, key="trace_pick")
        base = st.text_input("App address encoded in QR", config.DEFAULT_QR_BASE_URL,
                             help="For phone scanning use your laptop's LAN address, e.g. http://192.168.1.5:8501")
        batch = db.get_batch(bid)
        a, b = st.columns([1, 2])
        png = qr_generator.make_qr_png(base, bid)
        with a:
            st.image(png, caption=qr_generator.batch_url(base, bid))
            st.download_button(T("Download QR (PNG)"), png, f"{bid}_qr.png", "image/png")
        with b:
            rows = pd.DataFrame(exports.info_status(batch), columns=["Field", "Value", "Information status"])
            rows["Value"] = rows["Value"].astype(str)
            st.dataframe(rows, width="stretch", hide_index=True)
            st.caption("Status key: verified (named verifier) · documented (reference supplied) · user-reported · unavailable")
        la = db.list_assessments(bid)
        latest = json.loads(la.result_json.iloc[0]) if len(la) else None
        st.markdown(T("**Handling & processing records**"))
        st.dataframe(db.list_events(bid), width="stretch", hide_index=True)
        st.download_button(T("Download batch summary (.txt)"), exports.batch_summary_text(batch, latest), f"{bid}_summary.txt")
        if batch["is_sample"]:
            st.warning("SAMPLE record — illustrative demonstration data.")

# ---------------------------------------------------------------- Impact
elif page == "impact":
    hero(T("Impact analytics"), "Measured numbers come from stored records. Scenarios are hypothetical and clearly separate.")
    m = ia.measured()
    st.subheader(T("A. Measured from recorded data"))
    c = st.columns(4)
    c[0].metric(T("Batches"), m["batches"]); c[1].metric(T("Quantity"), f"{m['total_kg']:,.0f} kg")
    c[2].metric("Screened / elevated", f"{m['assessed']} / {m['elevated']}"); c[3].metric("Offers", m["offers"])
    st.write(f"Recorded gross {inr(m['gross_recorded'])}, net {inr(m['net_recorded'])} (sum of all entered offers — "
             "alternatives, not sales). Like-for-like offer spread: "
             f"{inr(m['recorded_spread'])}. A risk alert is not a prevented loss; no savings are claimed here.")
    st.subheader(T("B. Illustrative loss-reduction scenario (hypothetical)"))
    a, b, c, d = st.columns(4)
    kg = a.number_input(T("Quantity (kg)"), min_value=0.0, value=float(round(m["total_kg"], 1)))
    pr = b.number_input(T("Price (₹/kg)"), min_value=0.0, value=60.0)
    bl = c.number_input(T("Assumed baseline loss (%)"), 0.0, 100.0, 10.0, help="Your assumption — not a measured value.")
    rd = d.number_input(T("Assumed loss reduction (%)"), 0.0, 100.0, 30.0)
    s = ia.loss_scenario(kg, pr, bl, rd)
    st.metric(T("Hypothetical value of avoided loss"), inr(s["hypothetical_value"]),
              f"{s['hypothetical_avoided_kg']:.1f} kg of {s['baseline_lost_kg']:.1f} kg assumed lost", delta_color="off")
    st.warning("HYPOTHETICAL: depends entirely on the assumptions above. A pilot with before/after loss records is "
               "needed before any savings can be claimed.")
    rep = pd.DataFrame([{"type": "measured", "indicator": "batches", "value": m["batches"]},
                        {"type": "measured", "indicator": "total_kg", "value": m["total_kg"]},
                        {"type": "measured", "indicator": "batches_screened", "value": m["assessed"]},
                        {"type": "measured", "indicator": "batches_elevated", "value": m["elevated"]},
                        {"type": "measured", "indicator": "offers", "value": m["offers"]},
                        {"type": "measured", "indicator": "like_for_like_offer_spread_inr", "value": m["recorded_spread"]},
                        {"type": "HYPOTHETICAL", "indicator": "avoided_loss_value_inr", "value": s["hypothetical_value"]}])
    st.download_button(T("Download impact report (CSV)"), exports.df_to_csv(rep), "impact_report.csv", "text/csv")

# ---------------------------------------------------------------- Data
else:
    hero(T("Data & settings"), T("Sample loading is additive; deleting is always explicit."))
    st.subheader(T("Demo data"))
    st.write("Adds SAMPLE tamarind and honey batches with SAMPLE offers. Existing records are not touched; "
             "re-loading does not duplicate.")
    if st.button(T("Load SAMPLE data")):
        n = db.load_sample_data(); st.success(f"{n} sample batch(es) added." if n else "Sample data already present.")
    st.subheader(T("Export"))
    for name, df in [("batches", db.list_batches()), ("offers", db.list_offers())]:
        st.download_button(f"Download {name}.csv", exports.df_to_csv(df), f"{name}.csv", "text/csv", disabled=df.empty)
    st.subheader(T("Delete"))
    if st.checkbox("I understand: remove only SAMPLE records (my own batches are kept)"):
        if st.button(T("Remove SAMPLE records")):
            st.success(f"Removed {db.remove_sample_data()} sample batch(es).")
    txt = st.text_input(T("Type DELETE to erase ALL data (export CSVs first)"))
    if st.button(T("Erase everything")):
        try:
            db.wipe_all(txt); st.success("All data erased.")
        except PermissionError as e:
            st.error(str(e))
