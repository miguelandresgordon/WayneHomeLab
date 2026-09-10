import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import dotenv from "dotenv";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
dotenv.config({ path: path.join(root, ".env") });

function num(name: string, fallback: number): number {
  const raw = process.env[name];
  if (!raw) return fallback;
  const n = Number(raw);
  return Number.isFinite(n) ? n : fallback;
}

export const config = {
  root,
  port: num("WIC_PORT", 3000),
  dbPath: process.env.WIC_DB_PATH || path.join(root, "data", "wic.db"),
  demo: process.env.WIC_DEMO === "1",
  lat: num("WIC_LAT", 40.4168),
  lon: num("WIC_LON", -3.7038),
  elevation: num("WIC_ELEVATION", 667),
  locationName: process.env.WIC_LOCATION_NAME || "Casa",
  municipioIne: process.env.WIC_MUNICIPIO_INE || "28079",
  idema: process.env.WIC_IDEMA || "3195",
  aemetArea: process.env.WIC_AEMET_AREA || "68",
  aemetKey: process.env.AEMET_API_KEY || "",
  haBaseUrl: (process.env.HA_BASE_URL || "http://192.168.1.110:8123").replace(/\/$/, ""),
  haToken: process.env.HA_TOKEN || "",
  haWeatherEntity: process.env.HA_WEATHER_ENTITY || "",
  ingestToken: process.env.WIC_INGEST_TOKEN || "",
  isProd: process.env.NODE_ENV === "production",
};

export function ensureDataDir(): void {
  fs.mkdirSync(path.dirname(path.resolve(config.dbPath)), { recursive: true });
}
