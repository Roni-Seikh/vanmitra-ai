# Likely questions — honest answers
- **Is this real AI?** Screening is a transparent rule-based expert system. We searched for datasets and found none linking NTFP storage conditions to outcomes; training on invented labels would give fake accuracy. The ML pipeline (baseline, held-out test, saved model) is built and tested and trains when pilot data arrives. Our pilot doubles as data collection.
- **Why not use the Kaggle honey dataset?** It predicts purity from composition, looks synthetic, and has no storage features.
- **How accurate is it?** Unknown — unvalidated. We report no accuracy figure.
- **Where do thresholds come from?** Team-set heuristics (honey 20% moisture follows a commonly cited limit); need expert/FSSAI review.
- **Are the prices real?** No; SAMPLE offers are illustrative. Users enter real offers.
- **Does QR prove authenticity/sustainability?** No; it is a lookup link to user-reported data with status labels.
- **Who pays?** Hypothesis: cooperatives, NGOs, buyers needing traceability — untested.
- **Competitors?** Not researched in depth; do not claim uniqueness.
- **Will users with low literacy cope?** Not tested; Bengali is partial; voice/icons are future work.
- **Data privacy?** Local SQLite, no cloud; no auth yet.
- **What did you not do?** ML, real datasets, MSP data, field trial, browser/phone visual QA, full Bengali, deployment.

## Added for the real-data model
- **What data trained the model?** 203,798 real Agmarknet monthly records (Govt. of India open data, GODL-India), 1,588 commodity-state series; tamarind is the focus.
- **Why pool all commodities?** Tamarind alone has ~743 rows; pooling gave ~100k labelled rows. Evaluated on tamarind in a held-out future period.
- **Is it accurate?** Beats 'no change' by 8.2% MAE overall; tamarind +10.1% but CI includes zero. We say so on the model card page.
- **How do you prevent leakage?** Chronological split by target month, model chosen on validation, test used once, and an automated test that altering future prices does not change earlier features.
- **Why is the risk module not ML?** No labelled storage-outcome data exists publicly; faking labels would be dishonest. Pilot data collection (template provided) fixes this.
- **Do collectors get mandi prices?** No: mandi prices are wholesale context; we apply only relative seasonal change to the user's own price.
- **Why no honey forecast?** The source has one honey record.
