# Model card — VanMitra AI tamarind price-change model (real data)
**Task:** predict next-month change in the mandi price (log change) of a commodity in a state, from past prices/arrivals. Applied to Tamarind Fruit for the Hold-or-Sell advisor.
**Data:** Agmarknet monthly state prices & arrivals, 203,798 rows, 2019-01..2026-10 (real). See data_sources.md for licence and caveats.
**Training:** pooled across 1,588 commodity-state series (99,861 labelled rows) because tamarind alone has only ~743 rows.
**Chronological split by target month:** train to 2023-12 (n=55,786), validation 2024 (n=15,814), test 2025-01..2026-09 (n=26,966), test used once. Model selected on validation: **hgb_absolute** (HistGradientBoosting, absolute-error loss, depth 4). Deployed model refit on all rows.
**Features (all known at time t):** 1/2/3/12-month log changes, deviation from 12-month mean, 6-month volatility, arrivals change/level, series' own past average change for the target calendar month, calendar month, commodity group. A test verifies no future leakage.
## Held-out test results (₹ per quintal; lower is better)
| Test set | Rows | Naive 'no change' MAE | Seasonal-mean MAE | Our model MAE | MAPE naive / model |
|---|---|---|---|---|---|
| All series | 26966 | 791.2 | 880.2 | 726.5 | 18.25% / 16.51% |
| Forest-produce group | 287 | 821.2 | 1107.2 | 747.3 | 23.64% / 31.07% |
| Tamarind fruit | 114 | 1146.5 | 1650.0 | 1030.3 | 13.09% / 11.13% |
**Improvement over naive (MAE):** all series +8.2%; tamarind +10.1%.
**Honest reading:** the all-series gain is clear (n=26,966). For tamarind alone the 95% bootstrap interval of the MAE gain is ₹-45.8 to ₹319.3/qtl and includes zero (n=114), so the tamarind advantage is promising, not proven. In the forest-produce group the model has lower MAE but a higher MAPE than naive (a few large misses), so there it is mixed.
**Forecast range:** 10th–90th percentile of validation residuals (log change -0.22 to +0.34); covered 89.5% of tamarind test outcomes. Ranges are wide because monthly mandi prices are noisy.
**Intended use:** decision support on timing (sell now vs hold) alongside the batch's storage screening. **Not** a price guarantee, not forest-gate price, not financial advice.
**Limitations:** wholesale mandi prices of mixed grades/varieties; six states with enough tamarind history (none in West Bengal); Agmarknet widened market coverage from Nov 2025; one-step-ahead only; small tamarind test set.
**Reproduce:** `python -m ml.price_model` (about 1 minute). Metrics: `models/price/metrics.json`.
