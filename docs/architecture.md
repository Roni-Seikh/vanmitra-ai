# Architecture
```
 User (browser) ─▶ app.py (Streamlit UI)
                    ├─ utils/validation.py ─▶ database/db.py ─▶ SQLite (batches, offers, assessments, events)
                    ├─ modules/risk_assessment.py   (rules → level, factors, missing, next steps)
                    ├─ modules/market_comparison.py ◀─ utils/calculations.py (unit + net maths)
                    ├─ modules/value_addition.py    (raw vs option, break-even)
                    ├─ modules/impact_analytics.py  (measured vs hypothetical)
                    └─ utils/qr_generator.py, utils/exports.py (QR PNG, CSV, TXT)
```
Business logic is pure Python (unit-tested); the UI only calls it. Runs fully offline.
