# 🌿 VanMitra AI — by Team BioNexis
**Forest-produce loss prevention & fair-market assistant** (Forest-Based Bio-Economy track, Bio-Economy Hackathon 2026, Eastern Region).
Roni Seikh (Leader), Rahul Pal · Brainware University.

## What is real and what is not
| Component | Status |
|---|---|
| **Price intelligence & forecast** | **Real data** (203,798 official Agmarknet records, 2019-2026) + **real trained model** (HistGradientBoosting, chronological split, baselines, published metrics in `docs/model_card.md`) |
| **Hold-or-Sell advisor** | Uses the real seasonality; costs/loss are user assumptions (labelled) |
| **Storage-risk screening** | **Rule-based** (transparent). No public labelled storage-outcome dataset exists, so we do not fake an ML model; `ml/train_model.py` trains one on real pilot labels |
| Net-return comparison, QR traceability, impact | Real calculations on user-entered data |
| Sample batches/offers | SAMPLE (illustrative), always labelled |
**Model result in one line:** on 26,966 held-out months (2025-26) it cuts error 8.2% vs the "no change" baseline; for tamarind alone +10.1% but not statistically proven (n=114). Details and caveats: `docs/model_card.md`.

## Setup (Windows 11, PowerShell, working directory = the `vanmitra-ai` folder)
```powershell
python --version                      # 3.10 – 3.13 recommended
python -m venv .venv
.\.venv\Scripts\Activate.ps1          # if blocked: Set-ExecutionPolicy -Scope Process Bypass
pip install -r requirements.txt
python -m pytest -q                   # expect: 40 passed
streamlit run app.py                  # opens http://localhost:8501
```
First use: sidebar → **Data & Settings → Load SAMPLE data**. Data persists in `data/vanmitra.db`.

**Phone QR scan:** laptop and phone on the same Wi-Fi → run `ipconfig`, copy the IPv4 address, run
`streamlit run app.py --server.address 0.0.0.0`, then on the **Traceability** page set the address to
`http://<IPv4>:8501` (allow Python through Windows Firewall if asked). Scanning opens that batch's record.

**Common fixes:** if you see a scikit-learn *version mismatch* warning about the saved model, run `python -m ml.price_model` (about 1 minute) to retrain it locally;  `streamlit not recognized` → activate the venv; `Port in use` → `--server.port 8502`;
old Streamlit warnings about `width` → `pip install -U streamlit`.

## Modules (all functional)
Dashboard · Batches (register/edit/history) · Risk Screening · Buyer Offers (net-return) · Value Addition ·
Traceability (QR, status labels, downloads) · Impact (measured vs hypothetical, CSV) · Data & Settings
(additive sample load, explicit deletion). Bengali: navigation + disclaimer only (partial).

## Net-return formula
`gross = price/unit × quantity`; `deductions = gross × deduction% + flat`; `costs = transport + packaging + processing + other`;
`net = gross − deductions − costs`; `net/kg = net ÷ quantity in kg` (units normalised: g, kg, quintal=100 kg, tonne=1000 kg).
Ranking default is net/kg (fair when offered quantities differ). Different grades trigger a warning.

## Risk-screening logic
Points from: days since collection, storage humidity, temperature, storage type, packaging, reported pests (+3), reported mould
(+4, forces *Elevated*), and for honey only a moisture reading (>20% +3, >18% +1). Score ≥6 Elevated, 3–5 Moderate, 0–2 Low;
if all key measurements are missing → *Insufficient data*. Thresholds are **team-set heuristics, not validated**; edit `RULES` in
`modules/risk_assessment.py` with a domain expert. Every result lists factors, missing inputs, next steps and limitations.

## Layout
`app.py` UI · `modules/` logic · `database/` SQLite · `utils/` validation, maths, QR, exports · `tests/` · `docs/`
Data flow: form → `validate_*` → SQLite → `assess` / `compare_offers` / `evaluate` → UI, QR, CSV/TXT exports. No network needed.

## Machine learning
```powershell
python -m ml.price_model          # retrains the REAL price model (~1 min) and rewrites models/price/metrics.json
python -m ml.prepare_data         # re-downloads the real dataset (internet needed once)
python -m ml.train_model --csv data\pilot\labelled_batches.csv   # storage-risk model: REAL pilot labels only (refuses < 200 rows)
```
Price model: pooled across 1,588 commodity-state series, chronological split (train to 2023, validate 2024, test 2025-01..2026-09 once), naive and seasonal baselines, model chosen on validation, bootstrap CI, leakage test. Risk model template: `data/pilot/labelled_batches_TEMPLATE.csv`.

## Pages
Dashboard (real market snapshot) · Batches · Risk Screening · Buyer Offers · **Market Intelligence** (history, seasonality, forecast + model card, hold-or-sell) · Value Addition · Traceability · Impact · Data & Settings. Bengali covers main screens (machine-drafted; needs native review).

## Files
`docs/VanMitra_AI_BioNexis_Pitch.pptx` · `docs/model_card.md` · `docs/data_sources.md` · `docs/limitations.md` · `docs/demo_script.md` · `docs/qa_prep.md` · `docs/judging_matrix.md` · `docs/test_report.md`
