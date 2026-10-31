# Data sources and documentation
## 1. REAL dataset used for the ML model: Agmarknet monthly state prices & arrivals
| Field | Detail |
|---|---|
| Original publisher | Government of India: Directorate of Marketing & Inspection / Dept. of Agriculture & Farmers Welfare, portal **Agmarknet** (agmarknet.gov.in), report `statewise_price_arrival_sp` |
| Copy we used (secondary) | `https://github.com/herrrickshaw/india-mandi-arrivals` -> `data/agmarknet/state_monthly.csv.gz` (downloaded 31 Oct 2026). We did not re-collect from Agmarknet ourselves, so we rely on that repo's accuracy; fetching the original portal is the next verification step. |
| Licence | Data: Government of India open data, re-published under **GODL-India with attribution** (repo `DATA_LICENSE.md`); code MIT. Attribution: "Source: Agmarknet, Govt. of India, via herrrickshaw/india-mandi-arrivals". |
| What a row is | one commodity x state x month: weighted-average price (₹/quintal) and arrivals (tonnes) |
| Fields | month, commodity_id, commodity, group, state, arrivals_t, price_rs_qtl |
| Size / span | 203,798 rows, 2019-01 to 2026-10 (46,886 rows have no price/arrivals and are dropped) |
| Real or synthetic | **Real** (official market reports) |
| Tamarind coverage | "Tamarind Fruit": 743 rows, 11-12 states; 6 states with >= 48 months (Chhattisgarh, Karnataka, Madhya Pradesh, Maharashtra, Tamil Nadu, Telangana). **No West Bengal series.** |
| Honey coverage | 1 row in total: **no honey price model is built** |
| Missing data | months without reports are NaN; gaps <= 2 months are interpolated; longer gaps leave the row unused |
| Known issues | prices mix grades/varieties; markets report irregularly; Agmarknet widened market coverage from Nov 2025 (arrivals not comparable across that change); latest month is in progress; some series have spikes (e.g. Madhya Pradesh tamarind) |
| Bias risks | wholesale regulated-mandi prices, not forest-gate or SHG prices; collectors may receive far less; states with more mandis dominate |
| Intended use | timing decision support (seasonality, next-month change, hold-or-sell) |
| Not suitable for | predicting what a particular collector will be paid; storage spoilage; honey pricing |
Also shipped: `data/real/agmarknet_state_monthly_all.csv.gz` (the file above, unmodified). Rebuild with `python -m ml.prepare_data`.

## 2. Datasets investigated and NOT used (searched 28-31 Oct 2026)
| Source | Why not used |
|---|---|
| Kaggle "Predict Purity and Price of Honey" | looks synthetic; target is purity; no storage features |
| Zenodo 20072146, Mendeley 6kxjzpkdvd (honey physicochemical, real) | composition only; no storage conditions or outcomes |
| Tamarind storage experiments (journal papers) | no downloadable row-level data |
| Grain/aflatoxin storage literature | different commodities; qualitative support for the ~65% RH mould-risk line only |
| Kaggle Agmarknet mirrors (2023-25) | duplicate the same source; GitHub copy has longer span |
**Consequence:** no public labelled dataset links forest-produce storage conditions to spoilage outcomes, so the **storage-risk screening stays rule-based**. The pilot-data template and `ml/train_model.py` train a real model once such labels are collected.

## 3. Facts behind the screening rules (secondary sources - verify)
Honey <= 20% moisture general limit: Foods 2026, doi:10.3390/foods15132311. Tamarind moisture/storage guidance: botanikabharat.com/tamarind.php (commercial exporter, accessed 28 Oct 2026). ~65% RH mould threshold: PMC3989759 (grain review).
## 4. Reference price (UNVERIFIED, never used in calculations)
Tamarind (with seeds) ₹36/kg, Ministry of Tribal Affairs MSP-for-MFP list (tribal.nic.in PDF); the site blocks automated access so date/currency could not be confirmed; honey omitted because sources conflict (₹195 vs ₹225).
