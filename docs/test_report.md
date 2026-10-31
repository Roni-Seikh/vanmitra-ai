# Test report (executed 31 Oct 2026, Python 3.12.3, Linux sandbox)
`python -m pytest -q` -> **40 passed** (tests/test_vanmitra.py, ~45 s).
Covers: DB init/persistence/empty DB; batch CRUD/history/duplicates; 12 invalid-batch cases; offer validation; net-return and unit maths; mixed-grade/unit warnings;
risk rules incl. product-specific lines and NaN-as-missing; QR round-trip and OpenCV decode of the PNG; CSV/summary export; sample-load idempotency and reset safeguards;
impact measured vs scenario; value-addition break-even; **real dataset sanity (rows, span, states); feature no-leakage test; price-model pipeline on a forest subset;
shipped metrics.json consistency (reported skill equals raw MAE ratio; beats baseline on 26,966 held-out rows); forecast ordering and invalid-state error; seasonal profile; hold-or-sell logic and input validation**;
headless Streamlit runs of all pages in English and Bengali and of the Market Intelligence page.
Model training executed: `python -m ml.price_model` (results in docs/model_card.md).
## NOT done (not possible here)
Visual check in a real browser/phone (no browser in sandbox); phone QR scan (QR PNG decodes in OpenCV); Windows 11 run; 5-minute rehearsal; native Bengali review;
verification of the MSP reference; downloading the original Agmarknet portal data (we used a GODL-India GitHub copy); real storage-outcome model (no data exists).
