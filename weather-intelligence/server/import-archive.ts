import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { getDb, logIngest, upsertArchive } from "./db.ts";

function numComma(v: string | undefined): number | null {
  if (v === undefined || v === "" || v === "Ip" || v === "null") return null;
  const n = Number(String(v).replace(",", ".").trim());
  return Number.isFinite(n) ? n : null;
}

function splitCsvLine(line: string): string[] {
  const out: string[] = [];
  let cur = "";
  let q = false;
  for (const ch of line) {
    if (ch === '"') {
      q = !q;
      continue;
    }
    if (ch === "," && !q) {
      out.push(cur.trim());
      cur = "";
      continue;
    }
    cur += ch;
  }
  out.push(cur.trim());
  return out;
}

export type ArchiveRow = {
  sampledAt: string;
  tempC: number | null;
  humidity: number | null;
  windMs: number | null;
  precipMm: number | null;
  skyText: string | null;
};

export function parseArchiveCsv(text: string): ArchiveRow[] {
  const lines = text.split(/\r?\n/).filter((l) => l.trim() && !l.startsWith("#"));
  if (lines.length < 2) return [];
  const header = splitCsvLine(lines[0]).map((h) => h.toLowerCase());
  const idx = (names: string[]) => names.map((n) => header.indexOf(n)).find((i) => i >= 0) ?? -1;

  const iFecha = idx(["timestamp", "sampled_at", "fecha", "date"]);
  const iTemp = idx(["temp_c", "tmed", "ta", "temp"]);
  const iHum = idx(["humidity", "hr", "humedad"]);
  const iWind = idx(["wind_ms", "velmedia", "vv", "viento"]);
  const iPrec = idx(["precip_mm", "prec", "precipitacion"]);
  const iSky = idx(["sky_text", "cielo", "sky"]);

  if (iFecha < 0) {
    throw new Error("CSV needs timestamp/fecha column");
  }

  const aemetDaily = header.includes("tmed") || header.includes("indicativo");
  const rows: ArchiveRow[] = [];
  for (const line of lines.slice(1)) {
    const cols = splitCsvLine(line);
    const rawDate = cols[iFecha];
    if (!rawDate) continue;
    const sampledAt = rawDate.includes("T")
      ? new Date(rawDate).toISOString()
      : `${rawDate}T12:00:00.000Z`;
    let windMs = numComma(iWind >= 0 ? cols[iWind] : undefined);
    if (aemetDaily && windMs !== null) {
      windMs = windMs / 3.6;
    }
    rows.push({
      sampledAt,
      tempC: numComma(iTemp >= 0 ? cols[iTemp] : undefined),
      humidity: numComma(iHum >= 0 ? cols[iHum] : undefined),
      windMs,
      precipMm: numComma(iPrec >= 0 ? cols[iPrec] : undefined),
      skyText: iSky >= 0 ? cols[iSky] || null : null,
    });
  }
  return rows;
}

export function parseArchiveJson(text: string): ArchiveRow[] {
  const data = JSON.parse(text) as unknown;
  const arr = Array.isArray(data) ? data : [];
  return arr.map((item) => {
    const r = item as Record<string, unknown>;
    const ts = String(r.timestamp || r.sampledAt || r.fecha || "");
    return {
      sampledAt: ts.includes("T") ? new Date(ts).toISOString() : `${ts}T12:00:00.000Z`,
      tempC: typeof r.tempC === "number" ? r.tempC : numComma(String(r.temp_c ?? r.tmed ?? "")),
      humidity: typeof r.humidity === "number" ? r.humidity : numComma(String(r.hr ?? "")),
      windMs: typeof r.windMs === "number" ? r.windMs : numComma(String(r.wind_ms ?? r.velmedia ?? "")),
      precipMm: typeof r.precipMm === "number" ? r.precipMm : numComma(String(r.precip_mm ?? r.prec ?? "")),
      skyText: r.skyText ? String(r.skyText) : r.sky_text ? String(r.sky_text) : null,
    };
  });
}

export function importArchiveFile(filePath: string): number {
  const abs = path.resolve(filePath);
  const text = fs.readFileSync(abs, "utf8");
  const rows = abs.toLowerCase().endsWith(".json") ? parseArchiveJson(text) : parseArchiveCsv(text);
  getDb();
  for (const row of rows) {
    if (!row.sampledAt || Number.isNaN(Date.parse(row.sampledAt))) continue;
    upsertArchive(row);
  }
  logIngest("archive-import", true, `${rows.length} rows from ${path.basename(abs)}`);
  return rows.length;
}

function isCli(): boolean {
  const self = fileURLToPath(import.meta.url);
  const invoked = process.argv[1] ? path.resolve(process.argv[1]) : "";
  return path.resolve(self) === invoked;
}

if (isCli()) {
  const target = process.argv[2];
  if (!target) {
    console.error("Usage: npm run import -- /path/to/aemet.csv");
    process.exit(1);
  }
  const n = importArchiveFile(target);
  console.log(`imported ${n} rows`);
}
