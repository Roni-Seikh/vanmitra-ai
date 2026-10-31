"""SQLite persistence. Every function accepts an optional db_path (used by tests)."""
import json, secrets, sqlite3
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from pathlib import Path
import pandas as pd
import config

SCHEMA = Path(__file__).with_name("schema.sql")
BATCH_FIELDS = ["product", "collection_date", "quantity", "unit", "region", "storage_type", "packaging_type",
                "storage_temp_c", "storage_humidity_pct", "moisture_pct", "visible_mold", "pest_signs",
                "handling_notes", "producer_group", "provenance_status", "provenance_ref", "verifier",
                "sustainability_doc_status", "sustainability_doc_ref", "is_sample"]
OFFER_FIELDS = ["buyer", "price_per_unit", "quantity", "unit", "grade", "transport", "packaging", "processing",
                "other", "deduction_pct", "deduction_flat", "is_sample"]


def _now():
    return datetime.now().isoformat(timespec="seconds")


@contextmanager
def connect(db_path=None):
    path = db_path or config.DB_PATH
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(db_path=None):
    with connect(db_path) as c:
        c.executescript(SCHEMA.read_text(encoding="utf-8"))


def _event(c, batch_id, kind, detail):
    c.execute("INSERT INTO events(batch_id,ts,event_type,detail) VALUES(?,?,?,?)", (batch_id, _now(), kind, detail))


def create_batch(data, batch_id=None, db_path=None):
    """Insert a validated batch. Random IDs retry on collision; an explicit ID that exists raises ValueError."""
    init_db(db_path)
    day = data["collection_date"].replace("-", "")
    for _ in range(10):
        bid = batch_id or f"VM-{day}-{secrets.token_hex(2).upper()}"
        try:
            with connect(db_path) as c:
                c.execute(f"INSERT INTO batches(batch_id,{','.join(BATCH_FIELDS)},created_at,updated_at) "
                          f"VALUES(?,{','.join('?' * len(BATCH_FIELDS))},?,?)",
                          [bid, *[data.get(k) for k in BATCH_FIELDS], _now(), _now()])
                _event(c, bid, "registered", "Batch registered (user-reported details).")
            return bid
        except sqlite3.IntegrityError:
            if batch_id:
                raise ValueError(f"Batch ID {batch_id} already exists.")
    raise RuntimeError("Could not generate a unique batch ID.")


def get_batch(batch_id, db_path=None):
    init_db(db_path)
    with connect(db_path) as c:
        r = c.execute("SELECT * FROM batches WHERE batch_id=?", (batch_id,)).fetchone()
    return dict(r) if r else None


def update_batch(batch_id, data, db_path=None):
    old = get_batch(batch_id, db_path)
    if not old:
        raise KeyError(batch_id)
    changed = {k: (old[k], data.get(k)) for k in BATCH_FIELDS if k != "is_sample" and old[k] != data.get(k)}
    if not changed:
        return []
    with connect(db_path) as c:
        c.execute(f"UPDATE batches SET {','.join(f'{k}=?' for k in changed)}, updated_at=? WHERE batch_id=?",
                  [*[v[1] for v in changed.values()], _now(), batch_id])
        _event(c, batch_id, "edited", "; ".join(f"{k}: {a!r} -> {b!r}" for k, (a, b) in changed.items()))
    return list(changed)


def list_batches(db_path=None):
    init_db(db_path)
    with connect(db_path) as c:
        return pd.read_sql_query("SELECT * FROM batches ORDER BY created_at DESC, batch_id", c)


def add_offer(batch_id, offer, db_path=None):
    if not get_batch(batch_id, db_path):
        raise KeyError(batch_id)
    with connect(db_path) as c:
        cur = c.execute(f"INSERT INTO offers(batch_id,{','.join(OFFER_FIELDS)},created_at) "
                        f"VALUES(?,{','.join('?' * len(OFFER_FIELDS))},?)",
                        [batch_id, *[offer.get(k) for k in OFFER_FIELDS], _now()])
        _event(c, batch_id, "offer_recorded", f"Offer from {offer['buyer']} recorded.")
        return cur.lastrowid


def list_offers(batch_id=None, db_path=None):
    init_db(db_path)
    q, p = "SELECT * FROM offers", ()
    if batch_id:
        q, p = q + " WHERE batch_id=?", (batch_id,)
    with connect(db_path) as c:
        return pd.read_sql_query(q + " ORDER BY id", c, params=p)


def delete_offer(offer_id, db_path=None):
    with connect(db_path) as c:
        c.execute("DELETE FROM offers WHERE id=?", (offer_id,))


def save_assessment(batch_id, result, db_path=None):
    with connect(db_path) as c:
        c.execute("INSERT INTO assessments(batch_id,created_at,level,score,result_json) VALUES(?,?,?,?,?)",
                  (batch_id, _now(), result["level"], result["score"], json.dumps(result)))
        _event(c, batch_id, "risk_screened", f"Screening level: {result['level']} (score {result['score']}).")


def list_assessments(batch_id=None, db_path=None):
    init_db(db_path)
    q, p = "SELECT id,batch_id,created_at,level,score,result_json FROM assessments", ()
    if batch_id:
        q, p = q + " WHERE batch_id=?", (batch_id,)
    with connect(db_path) as c:
        return pd.read_sql_query(q + " ORDER BY id DESC", c, params=p)


def list_events(batch_id, db_path=None):
    init_db(db_path)
    with connect(db_path) as c:
        return pd.read_sql_query("SELECT ts,event_type,detail FROM events WHERE batch_id=? ORDER BY id", c,
                                 params=(batch_id,))


# ---- sample data & reset: always explicit ----
def _sample_batches():
    t = date.today()
    base = dict(storage_temp_c=None, moisture_pct=None, visible_mold=0, pest_signs=0, handling_notes="",
                producer_group="", provenance_status="user-reported", provenance_ref="", verifier="",
                sustainability_doc_status="unavailable", sustainability_doc_ref="", is_sample=1, unit="kg")
    return [
        ("VM-SAMPLE-TAM-001", {**base, "product": "Tamarind", "collection_date": (t - timedelta(days=42)).isoformat(),
         "quantity": 250, "region": "SAMPLE district, West Bengal", "storage_type": "Ground-level room",
         "packaging_type": "Jute sack", "storage_humidity_pct": 78, "storage_temp_c": 31,
         "handling_notes": "SAMPLE: sun-dried 3 days, stored in jute sacks.", "producer_group": "SAMPLE-SHG-01",
         "sustainability_doc_status": "documented", "sustainability_doc_ref": "SAMPLE permit ref (illustrative)"}),
        ("VM-SAMPLE-HON-001", {**base, "product": "Honey", "collection_date": (t - timedelta(days=20)).isoformat(),
         "quantity": 40, "region": "SAMPLE region, West Bengal", "storage_type": "Raised platform, ventilated room",
         "packaging_type": "Airtight food-grade container", "storage_humidity_pct": 66, "storage_temp_c": 29,
         "moisture_pct": 21.5, "handling_notes": "SAMPLE: moisture reading entered by user (not lab-verified)."}),
    ]


# (buyer, price/unit INR, qty, unit, grade, transport, packaging, processing, other, deduction %) - all illustrative
_SAMPLE_OFFERS = [
    ("VM-SAMPLE-TAM-001", "SAMPLE Buyer A (local trader)", 62, 250, "kg", "Ungraded", 400, 0, 0, 0, 5),
    ("VM-SAMPLE-TAM-001", "SAMPLE Buyer B (distant aggregator)", 70, 250, "kg", "Ungraded", 1800, 250, 0, 150, 2),
    ("VM-SAMPLE-TAM-001", "SAMPLE Buyer C (needs sorting)", 78, 220, "kg", "Grade A", 900, 300, 500, 0, 0),
]


def load_sample_data(db_path=None):
    """Additive only: inserts missing sample rows, never overwrites or deletes. Returns batches added."""
    init_db(db_path)
    added = 0
    for bid, data in _sample_batches():
        if get_batch(bid, db_path):
            continue
        create_batch(data, batch_id=bid, db_path=db_path)
        added += 1
        for o in (x for x in _SAMPLE_OFFERS if x[0] == bid):
            add_offer(bid, {"buyer": o[1], "price_per_unit": o[2], "quantity": o[3], "unit": o[4], "grade": o[5],
                            "transport": o[6], "packaging": o[7], "processing": o[8], "other": o[9],
                            "deduction_pct": o[10], "deduction_flat": 0, "is_sample": 1}, db_path)
    return added


def remove_sample_data(db_path=None):
    with connect(db_path) as c:
        n = c.execute("SELECT COUNT(*) FROM batches WHERE is_sample=1").fetchone()[0]
        c.execute("DELETE FROM batches WHERE is_sample=1")  # cascades to offers/assessments/events
    return n


def wipe_all(confirm_text, db_path=None):
    """Destroys everything. Requires the exact confirmation string 'DELETE'."""
    if confirm_text != "DELETE":
        raise PermissionError("Type DELETE to confirm.")
    with connect(db_path) as c:
        for t in ("events", "assessments", "offers", "batches"):
            c.execute(f"DELETE FROM {t}")
