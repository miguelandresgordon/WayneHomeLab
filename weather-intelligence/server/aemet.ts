import { config } from "./config.ts";
import type { AlertSeverity, HourlyPoint, Observation, WeatherAlert } from "./types.ts";

const BASE = "https://opendata.aemet.es/opendata/api";

type AemetEnvelope = {
  estado?: number;
  datos?: string;
  descripcion?: string;
};

function numish(v: unknown): number | null {
  if (v === null || v === undefined || v === "" || v === "Ip") return null;
  if (typeof v === "number" && Number.isFinite(v)) return v;
  const s = String(v).replace(",", ".").trim();
  const n = Number(s);
  return Number.isFinite(n) ? n : null;
}

export async function aemetFetch(path: string): Promise<unknown> {
  if (!config.aemetKey) {
    throw new Error("AEMET_API_KEY missing");
  }
  const url = `${BASE}${path}${path.includes("?") ? "&" : "?"}api_key=${encodeURIComponent(config.aemetKey)}`;
  const res = await fetch(url, {
    headers: { Accept: "application/json", api_key: config.aemetKey },
  });
  if (!res.ok) {
    throw new Error(`AEMET ${res.status} ${path}`);
  }
  const envelope = (await res.json()) as AemetEnvelope;
  if (!envelope.datos) {
    throw new Error(envelope.descripcion || "AEMET without datos URL");
  }
  const dataRes = await fetch(envelope.datos, { headers: { Accept: "application/json" } });
  if (!dataRes.ok) {
    throw new Error(`AEMET datos ${dataRes.status}`);
  }
  return dataRes.json();
}

type PeriodRow = { periodo?: string; value?: unknown; descripcion?: string };

function byPeriod(rows: PeriodRow[] | undefined): Map<string, PeriodRow> {
  const map = new Map<string, PeriodRow>();
  for (const row of rows || []) {
    if (row.periodo) map.set(String(row.periodo).padStart(2, "0").slice(0, 2), row);
  }
  return map;
}

export function parseObservation(payload: unknown): Observation | null {
  const rows = Array.isArray(payload) ? payload : [];
  const last = rows[rows.length - 1] as Record<string, unknown> | undefined;
  if (!last) return null;
  return {
    observedAt: String(last.fint || last.fhor || new Date().toISOString()),
    source: "aemet_station",
    tempC: numish(last.ta),
    humidity: numish(last.hr),
    windMs: numish(last.vv),
    windDir: numish(last.dv),
    precipMm: numish(last.prec),
    pressureHpa: numish(last.pres),
    radiation: numish(last.inso ?? last.global ?? last.rad),
    skyCode: last.vv === undefined ? null : null,
    skyText: typeof last.prec === "number" && last.prec > 0 ? "Precipitación" : null,
  };
}

type VientoRow = {
  periodo?: string;
  direccion?: string[];
  velocidad?: Array<string | number>;
};

export function parseHourly(payload: unknown): HourlyPoint[] {
  const root = Array.isArray(payload) ? payload[0] : payload;
  const dias =
    root && typeof root === "object"
      ? ((root as { prediccion?: { dia?: unknown[] } }).prediccion?.dia ?? [])
      : [];
  const out: HourlyPoint[] = [];

  for (const dia of dias) {
    if (!dia || typeof dia !== "object") continue;
    const d = dia as {
      fecha?: string;
      estadoCielo?: PeriodRow[];
      precipitacion?: PeriodRow[];
      probPrecipitacion?: PeriodRow[];
      temperatura?: PeriodRow[];
      vientoAndRachaMax?: VientoRow[];
    };
    const day = (d.fecha || "").slice(0, 10);
    if (!day) continue;
    const sky = byPeriod(d.estadoCielo);
    const precip = byPeriod(d.precipitacion);
    const temp = byPeriod(d.temperatura);
    const wind = new Map<string, VientoRow>();
    for (const w of d.vientoAndRachaMax || []) {
      if (w.periodo) wind.set(String(w.periodo).padStart(2, "0").slice(0, 2), w);
    }
    const probRows = d.probPrecipitacion || [];

    for (let h = 0; h < 24; h += 1) {
      const key = String(h).padStart(2, "0");
      const skyRow = sky.get(key);
      const tempRow = temp.get(key);
      if (!skyRow && !tempRow) continue;
      const hourAt = `${day}T${key}:00:00`;
      const windKmh = numish(wind.get(key)?.velocidad?.[0]);
      out.push({
        hourAt,
        tempC: numish(tempRow?.value),
        precipProb: precipProbForHour(probRows, h) ?? (numish(precip.get(key)?.value) !== null && (numish(precip.get(key)?.value) || 0) > 0 ? 80 : 0),
        skyCode: skyRow?.value != null ? String(skyRow.value) : null,
        skyText: skyRow?.descripcion || null,
        windMs: windKmh === null ? null : windKmh / 3.6,
      });
    }
  }

  return out.sort((a, b) => a.hourAt.localeCompare(b.hourAt));
}

export function precipProbForHour(rows: PeriodRow[], hour: number): number | null {
  let best: number | null = null;
  let bestSpan = 99;
  for (const row of rows) {
    const p = String(row.periodo || "");
    const m = p.match(/^(\d{2})-(\d{2})$/);
    if (!m) {
      if (p.padStart(2, "0") === String(hour).padStart(2, "0")) {
        return numish(row.value);
      }
      continue;
    }
    const a = Number(m[1]);
    const b = Number(m[2]);
    const inRange = a <= b ? hour >= a && hour < b : hour >= a || hour < b;
    if (!inRange) continue;
    const span = a <= b ? b - a : 24 - a + b;
    if (span < bestSpan) {
      bestSpan = span;
      best = numish(row.value);
    }
  }
  return best;
}

function severityOf(raw: string | undefined): AlertSeverity {
  const s = (raw || "").toLowerCase();
  if (s.includes("extreme") || s.includes("severe") || s === "red" || s.includes("rojo")) return "red";
  if (s.includes("moderate") || s === "orange" || s.includes("naranja")) return "orange";
  if (s.includes("minor") || s === "yellow" || s.includes("amarillo")) return "yellow";
  return "unknown";
}

export function parseAlerts(payload: unknown): WeatherAlert[] {
  const items = Array.isArray(payload) ? payload : payload ? [payload] : [];
  const out: WeatherAlert[] = [];

  for (const item of items) {
    if (!item || typeof item !== "object") continue;
    const rec = item as Record<string, unknown>;
    const infos = Array.isArray(rec.info) ? rec.info : rec.info ? [rec.info] : [rec];
    for (const info of infos) {
      if (!info || typeof info !== "object") continue;
      const inf = info as Record<string, unknown>;
      const areaObj = inf.area as { areaDesc?: string } | undefined;
      const id = String(rec.identifier || rec.id || inf.event || Math.random());
      const phenomenon = String(inf.event || rec.phenomenon || "Aviso AEMET");
      out.push({
        id,
        severity: severityOf(String(inf.severity || rec.severity || "")),
        phenomenon,
        area: String(areaObj?.areaDesc || rec.area || config.locationName),
        onset: inf.onset ? String(inf.onset) : rec.onset ? String(rec.onset) : null,
        expires: inf.expires ? String(inf.expires) : rec.expires ? String(rec.expires) : null,
        summary: String(inf.description || inf.headline || rec.descripcion || phenomenon),
      });
    }
  }
  return out;
}

export async function fetchObservation(): Promise<Observation | null> {
  const payload = await aemetFetch(
    `/observacion/convencional/datos/estacion/${encodeURIComponent(config.idema)}`,
  );
  return parseObservation(payload);
}

export async function fetchHourly(): Promise<HourlyPoint[]> {
  const payload = await aemetFetch(
    `/prediccion/especifica/municipio/horaria/${encodeURIComponent(config.municipioIne)}`,
  );
  return parseHourly(payload);
}

export async function fetchAlerts(): Promise<WeatherAlert[]> {
  const payload = await aemetFetch(
    `/avisos_cap/ultimoelaborado/area/${encodeURIComponent(config.aemetArea)}`,
  );
  return parseAlerts(payload);
}
