# Limitations & data sources (read before pitching)
- **The storage-risk screening is not ML, because no suitable real labelled dataset exists publicly** (see data_sources.md for what was checked). A synthetic-labelled demo model exists only to prove the pipeline runs; it is never used to score batches. The architecture keeps `assess(batch)`
  as a single function that a validated model could replace. A future model needs real, labelled pilot records, a held-out test set,
  a baseline, precision/recall/F1 and a confusion matrix.
- Screening thresholds are heuristics (honey 20% moisture is the commonly cited general limit — **verify with FSSAI / buyer spec**).
  Not a spoilage predictor, lab test, certification or food-safety check.
- Tamarind moisture/humidity lines come from a commercial exporter page and a grain-storage review; treat as provisional.
- All SAMPLE batches and offers are invented for demonstration; they are not market quotes. One MSP reference (tamarind with seeds) is shown only as UNVERIFIED context and never enters calculations.
- Provenance is user-entered. *verified* appears only when the user names a verifier; the app verifies nothing. A QR code is only a lookup link.
- Regions are free text at district/state level; do not enter locations of threatened/protected resources.
- Single-user local SQLite; no login, no multi-device sync, no offline-first mobile app. Bengali covers main screens but is machine-drafted and unreviewed.
- Automated UI test uses Streamlit's headless test harness; visual layout of the app was **not** checked in a real browser or phone (no browser available in the build sandbox); the slide deck was rendered and inspected.
## To verify with organisers
Exact submission format, whether a live internet/projector connection is available, whether slides are mandatory, and any rules on pre-built code.

## Price model limitations (real-data model)
- Gain over the naive baseline is modest; one-month-ahead mandi prices are noisy and forecast ranges are wide (about -20% to +40%).
- For tamarind alone the improvement (+10.1% MAE) is not statistically distinguishable from zero on 114 test rows; the all-series improvement (+8.2%, 26,966 rows) is.
- Wholesale mixed-grade mandi prices, not forest-gate prices; no West Bengal tamarind series; no honey series.
- We used a GitHub re-publication of Agmarknet, not the original portal; verify before formal claims.
- Hold-or-Sell uses historical seasonality plus the user's own cost and loss assumptions; the default loss-by-risk-level values are placeholders, not measurements.
