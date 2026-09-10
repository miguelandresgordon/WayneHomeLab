CREATE TABLE IF NOT EXISTS observations (
  observed_at TEXT PRIMARY KEY,
  source TEXT NOT NULL,
  temp_c REAL,
  humidity REAL,
  wind_ms REAL,
  wind_dir INTEGER,
  precip_mm REAL,
  pressure_hpa REAL,
  radiation REAL,
  sky_code TEXT,
  sky_text TEXT
);

CREATE TABLE IF NOT EXISTS hourly_forecast (
  hour_at TEXT PRIMARY KEY,
  temp_c REAL,
  precip_prob INTEGER,
  sky_code TEXT,
  sky_text TEXT,
  wind_ms REAL
);

CREATE TABLE IF NOT EXISTS alerts (
  id TEXT PRIMARY KEY,
  severity TEXT NOT NULL,
  phenomenon TEXT,
  area TEXT,
  onset TEXT,
  expires TEXT,
  summary TEXT,
  active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS archive_samples (
  sampled_at TEXT PRIMARY KEY,
  temp_c REAL,
  humidity REAL,
  wind_ms REAL,
  precip_mm REAL,
  sky_text TEXT
);

CREATE TABLE IF NOT EXISTS ingest_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  kind TEXT NOT NULL,
  started_at TEXT NOT NULL,
  finished_at TEXT,
  ok INTEGER NOT NULL,
  detail TEXT
);

CREATE TABLE IF NOT EXISTS action_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  action TEXT NOT NULL,
  ok INTEGER NOT NULL,
  at TEXT NOT NULL,
  detail TEXT
);
