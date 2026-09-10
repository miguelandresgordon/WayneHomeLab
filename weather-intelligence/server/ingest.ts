import { fetchAlerts, fetchHourly, fetchObservation } from "./aemet.ts";
import { config } from "./config.ts";
import {
  getDb,
  logIngest,
  latestObservation,
  replaceAlerts,
  replaceHourly,
  upsertArchive,
  upsertObservation,
} from "./db.ts";
import { demoAlert, demoHours, demoObservation } from "./fixtures.ts";

let ingesting = false;

async function runKind(kind: string, fn: () => Promise<void>): Promise<void> {
  try {
    await fn();
    logIngest(kind, true, "ok");
  } catch (err) {
    const detail = err instanceof Error ? err.message : String(err);
    logIngest(kind, false, detail);
    throw err;
  }
}

export async function ingestAll(): Promise<{ ok: boolean; detail: string }> {
  if (ingesting) return { ok: true, detail: "already running" };
  ingesting = true;
  getDb();
  try {
    if (config.demo || !config.aemetKey) {
      const obs = demoObservation();
      upsertObservation(obs);
      replaceHourly(demoHours());
      replaceAlerts(demoAlert() ? [demoAlert()!] : []);
      upsertArchive({
        sampledAt: obs.observedAt,
        tempC: obs.tempC,
        humidity: obs.humidity,
        windMs: obs.windMs,
        precipMm: obs.precipMm,
        skyText: obs.skyText,
      });
      logIngest("demo", true, config.demo ? "WIC_DEMO=1" : "no AEMET_API_KEY");
      return { ok: true, detail: "demo" };
    }

    const errors: string[] = [];
    await runKind("observation", async () => {
      const obs = await fetchObservation();
      if (obs) {
        upsertObservation(obs);
        upsertArchive({
          sampledAt: obs.observedAt,
          tempC: obs.tempC,
          humidity: obs.humidity,
          windMs: obs.windMs,
          precipMm: obs.precipMm,
          skyText: obs.skyText,
        });
      }
    }).catch((e) => errors.push(String(e)));

    await runKind("hourly", async () => {
      replaceHourly(await fetchHourly());
    }).catch((e) => errors.push(String(e)));

    await runKind("alerts", async () => {
      replaceAlerts(await fetchAlerts());
    }).catch((e) => errors.push(String(e)));

    const stale = !latestObservation();
    return {
      ok: errors.length === 0 && !stale,
      detail: errors.join("; ") || "ok",
    };
  } finally {
    ingesting = false;
  }
}

export function startScheduler(): void {
  const boot = () => {
    ingestAll().catch(() => undefined);
  };
  setTimeout(boot, 1500);
  setInterval(() => {
    ingestAll().catch(() => undefined);
  }, 10 * 60 * 1000);
}

const once = process.argv.includes("--once");
if (once) {
  ingestAll()
    .then((r) => {
      console.log(r.detail);
      process.exit(r.ok ? 0 : 1);
    })
    .catch((err) => {
      console.error(err);
      process.exit(1);
    });
}
