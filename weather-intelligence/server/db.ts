import Database from "better-sqlite3";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { config, ensureDataDir } from "./config.ts";
import type { HourlyPoint, Observation, WeatherAlert } from "./types.ts";

const schemaPath = path.join(path.dirname(fileURLToPath(import.meta.url)), "schema.sql");

let db: Database.Database | null = null;

export function getDb(): Database.Database {
  if (db) return db;
  ensureDataDir();
  db = new Database(config.dbPath);
  db.pragma("journal_mode = WAL");
  db.pragma("synchronous = NORMAL");
  db.exec(fs.readFileSync(schemaPath, "utf8"));
  return db;
}

export function logIngest(kind: string, ok: boolean, detail: string): void {
  getDb()
    .prepare(
      `INSERT INTO ingest_runs (kind, started_at, finished_at, ok, detail)
       VALUES (@kind, @at, @at, @ok, @detail)`,
    )
    .run({
      kind,
      at: new Date().toISOString(),
      ok: ok ? 1 : 0,
      detail: detail.slice(0, 2000),
    });
}

export function upsertObservation(row: Observation): void {
  getDb()
    .prepare(
      `INSERT INTO observations (
         observed_at, source, temp_c, humidity, wind_ms, wind_dir,
         precip_mm, pressure_hpa, radiation, sky_code, sky_text
       ) VALUES (
         @observedAt, @source, @tempC, @humidity, @windMs, @windDir,
         @precipMm, @pressureHpa, @radiation, @skyCode, @skyText
       )
       ON CONFLICT(observed_at) DO UPDATE SET
         source=excluded.source, temp_c=excluded.temp_c, humidity=excluded.humidity,
         wind_ms=excluded.wind_ms, wind_dir=excluded.wind_dir, precip_mm=excluded.precip_mm,
         pressure_hpa=excluded.pressure_hpa, radiation=excluded.radiation,
         sky_code=excluded.sky_code, sky_text=excluded.sky_text`,
    )
    .run(row);
}

export function replaceHourly(points: HourlyPoint[]): void {
  const conn = getDb();
  const tx = conn.transaction(() => {
    conn.exec("DELETE FROM hourly_forecast");
    const ins = conn.prepare(
      `INSERT INTO hourly_forecast (hour_at, temp_c, precip_prob, sky_code, sky_text, wind_ms)
       VALUES (@hourAt, @tempC, @precipProb, @skyCode, @skyText, @windMs)`,
    );
    for (const p of points) ins.run(p);
  });
  tx();
}

export function replaceAlerts(alerts: WeatherAlert[]): void {
  const conn = getDb();
  const tx = conn.transaction(() => {
    conn.exec("DELETE FROM alerts");
    const ins = conn.prepare(
      `INSERT INTO alerts (id, severity, phenomenon, area, onset, expires, summary, active)
       VALUES (@id, @severity, @phenomenon, @area, @onset, @expires, @summary, 1)`,
    );
    for (const a of alerts) ins.run(a);
  });
  tx();
}

export function latestObservation(): Observation | null {
  const row = getDb()
    .prepare(
      `SELECT observed_at AS observedAt, source, temp_c AS tempC, humidity,
              wind_ms AS windMs, wind_dir AS windDir, precip_mm AS precipMm,
              pressure_hpa AS pressureHpa, radiation, sky_code AS skyCode, sky_text AS skyText
       FROM observations ORDER BY observed_at DESC LIMIT 1`,
    )
    .get() as Observation | undefined;
  return row ?? null;
}

export function listHourly(): HourlyPoint[] {
  return getDb()
    .prepare(
      `SELECT hour_at AS hourAt, temp_c AS tempC, precip_prob AS precipProb,
              sky_code AS skyCode, sky_text AS skyText, wind_ms AS windMs
       FROM hourly_forecast ORDER BY hour_at ASC`,
    )
    .all() as HourlyPoint[];
}

export function activeAlert(): WeatherAlert | null {
  const now = new Date().toISOString();
  const row = getDb()
    .prepare(
      `SELECT id, severity, phenomenon, area, onset, expires, summary
       FROM alerts
       WHERE active = 1
         AND (expires IS NULL OR expires > @now)
       ORDER BY CASE severity WHEN 'red' THEN 0 WHEN 'orange' THEN 1 WHEN 'yellow' THEN 2 ELSE 3 END
       LIMIT 1`,
    )
    .get({ now }) as WeatherAlert | undefined;
  return row ?? null;
}

export function upsertArchive(sample: {
  sampledAt: string;
  tempC: number | null;
  humidity: number | null;
  windMs: number | null;
  precipMm: number | null;
  skyText: string | null;
}): void {
  getDb()
    .prepare(
      `INSERT INTO archive_samples (sampled_at, temp_c, humidity, wind_ms, precip_mm, sky_text)
       VALUES (@sampledAt, @tempC, @humidity, @windMs, @precipMm, @skyText)
       ON CONFLICT(sampled_at) DO UPDATE SET
         temp_c=excluded.temp_c, humidity=excluded.humidity, wind_ms=excluded.wind_ms,
         precip_mm=excluded.precip_mm, sky_text=excluded.sky_text`,
    )
    .run(sample);
}

export function logAction(action: string, ok: boolean, detail: string): void {
  getDb()
    .prepare(
      `INSERT INTO action_log (action, ok, at, detail) VALUES (@action, @ok, @at, @detail)`,
    )
    .run({
      action,
      ok: ok ? 1 : 0,
      at: new Date().toISOString(),
      detail: detail.slice(0, 1000),
    });
}
