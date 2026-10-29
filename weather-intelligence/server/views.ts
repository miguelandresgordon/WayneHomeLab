import { config } from "./config.ts";
import { activeAlert, latestObservation, listHourly } from "./db.ts";
import { demoHours, demoObservation } from "./fixtures.ts";
import { readDevices, readHaWeatherTemp } from "./ha.ts";
import { buildInsight, buildPhrase } from "./insights.ts";
import { skyKindFromCode } from "./sky.ts";
import type { CasaView, ContextPack, HomeView, HourlyPoint } from "./types.ts";

const STALE_MS = 90 * 60 * 1000;

function upcomingHours(hours: HourlyPoint[], n = 12): HourlyPoint[] {
  const now = Date.now() - 30 * 60 * 1000;
  return hours.filter((h) => Date.parse(h.hourAt) >= now).slice(0, n);
}

export async function buildHomeView(): Promise<HomeView> {
  let observation = latestObservation();
  let hours = listHourly();
  const alert = activeAlert();
  const demo = config.demo || (!config.aemetKey && !observation);
  if (demo && !observation) {
    observation = demoObservation();
    hours = demoHours();
  }

  const nextHours = upcomingHours(hours.length ? hours : demoHours());
  const age = observation ? Date.now() - Date.parse(observation.observedAt) : STALE_MS + 1;
  const weatherStale = !observation || Number.isNaN(age) || age > STALE_MS;

  const { reachable, devices } = await readDevices();
  const haTempC = await readHaWeatherTemp();
  const skyCode = observation?.skyCode || nextHours[0]?.skyCode;
  const skyText = observation?.skyText || nextHours[0]?.skyText;

  return {
    generatedAt: new Date().toISOString(),
    stale: weatherStale && !demo,
    staleReason: weatherStale && !demo ? "AEMET_STALE" : reachable ? null : "HA_UNREACHABLE",
    locationName: config.locationName,
    observation,
    haTempC,
    phrase: buildPhrase(observation, nextHours, alert),
    tempC: observation?.tempC ?? nextHours[0]?.tempC ?? null,
    sky: skyKindFromCode(`${skyCode ?? ""} ${skyText ?? ""}`),
    hours: nextHours,
    alert,
    insight: buildInsight(nextHours, alert, observation),
    haReachable: reachable,
    devices,
  };
}

export async function buildCasaView(): Promise<CasaView> {
  const { reachable, devices } = await readDevices();
  return {
    generatedAt: new Date().toISOString(),
    haReachable: reachable,
    staleReason: reachable ? null : "HA_UNREACHABLE",
    devices,
  };
}

export async function buildContextPack(): Promise<ContextPack> {
  const home = await buildHomeView();
  return {
    generatedAt: home.generatedAt,
    locationName: home.locationName,
    observation: home.observation,
    hours: home.hours,
    alert: home.alert,
    devices: home.devices,
    insight: home.insight,
  };
}
