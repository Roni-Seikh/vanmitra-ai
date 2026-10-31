CREATE TABLE IF NOT EXISTS batches (
  batch_id TEXT PRIMARY KEY, product TEXT NOT NULL, collection_date TEXT NOT NULL,
  quantity REAL NOT NULL, unit TEXT NOT NULL, region TEXT NOT NULL,
  storage_type TEXT NOT NULL, packaging_type TEXT NOT NULL,
  storage_temp_c REAL, storage_humidity_pct REAL, moisture_pct REAL,
  visible_mold INTEGER NOT NULL DEFAULT 0, pest_signs INTEGER NOT NULL DEFAULT 0,
  handling_notes TEXT DEFAULT '', producer_group TEXT DEFAULT '',
  provenance_status TEXT NOT NULL DEFAULT 'unavailable', provenance_ref TEXT DEFAULT '', verifier TEXT DEFAULT '',
  sustainability_doc_status TEXT NOT NULL DEFAULT 'unavailable', sustainability_doc_ref TEXT DEFAULT '',
  is_sample INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS offers (
  id INTEGER PRIMARY KEY AUTOINCREMENT, batch_id TEXT NOT NULL REFERENCES batches(batch_id) ON DELETE CASCADE,
  buyer TEXT NOT NULL, price_per_unit REAL NOT NULL, quantity REAL NOT NULL, unit TEXT NOT NULL,
  grade TEXT NOT NULL, transport REAL NOT NULL DEFAULT 0, packaging REAL NOT NULL DEFAULT 0,
  processing REAL NOT NULL DEFAULT 0, other REAL NOT NULL DEFAULT 0,
  deduction_pct REAL NOT NULL DEFAULT 0, deduction_flat REAL NOT NULL DEFAULT 0,
  is_sample INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS assessments (
  id INTEGER PRIMARY KEY AUTOINCREMENT, batch_id TEXT NOT NULL REFERENCES batches(batch_id) ON DELETE CASCADE,
  created_at TEXT NOT NULL, level TEXT NOT NULL, score INTEGER NOT NULL, result_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY AUTOINCREMENT, batch_id TEXT NOT NULL REFERENCES batches(batch_id) ON DELETE CASCADE,
  ts TEXT NOT NULL, event_type TEXT NOT NULL, detail TEXT NOT NULL);
