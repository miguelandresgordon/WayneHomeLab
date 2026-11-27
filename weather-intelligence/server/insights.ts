import { momentLabel } from "./sky.ts";
import type { HomeAction, HourlyPoint, Observation, WeatherAlert } from "./types.ts";

export type Insight = { text: string; action: HomeAction | null };

export function nextRain(hours: HourlyPoint[], from = new Date()): HourlyPoint | null {
  const fromMs = from.getTime();
  const until = fromMs + 12 * 3600 * 1000;
  for (const h of hours) {
    const t = Date.parse(h.hourAt);
    if (Number.isNaN(t) || t < fromMs || t > until) continue;
    const wet =
      (h.precipProb !== null && h.precipProb >= 40) ||
      (h.skyText || "").toLowerCase().includes("lluvia") ||
      (h.skyText || "").toLowerCase().includes("chubasco");
    if (wet) return h;
  }
  return null;
}

export function buildPhrase(
  observation: Observation | null,
  hours: HourlyPoint[],
  alert: WeatherAlert | null,
  at = new Date(),
): { lead: string; follow: string } {
  if (alert && (alert.severity === "red" || alert.severity === "orange")) {
    return { lead: alert.phenomenon, follow: "aviso AEMET" };
  }
  const rain = nextRain(hours, at);
  if (rain) {
    const hh = new Date(rain.hourAt).getHours();
    return { lead: rain.skyText || "Lluvia", follow: `a las ${hh} h` };
  }
  const sky = observation?.skyText || hours[0]?.skyText || "Cielo en calma";
  const lead = sky.charAt(0).toUpperCase() + sky.slice(1);
  return { lead, follow: momentLabel(at) };
}

export function buildInsight(
  hours: HourlyPoint[],
  alert: WeatherAlert | null,
  observation: Observation | null,
  at = new Date(),
): Insight {
  if (alert && (alert.severity === "red" || alert.severity === "orange")) {
    return { text: `${alert.phenomenon}. Revisa el aviso antes de salir.`, action: null };
  }
  const rain = nextRain(hours, at);
  if (rain) {
    const hh = new Date(rain.hourAt).getHours();
    const inTwoHours = Date.parse(rain.hourAt) - at.getTime() <= 2 * 3600 * 1000;
    return {
      text: inTwoHours
        ? `A las ${hh} h se moja el salón si dejas la ventana.`
        : `Lluvia prevista a las ${hh} h.`,
      action: null,
    };
  }
  if ((observation?.windMs || 0) >= 12) {
    return { text: "Viento fuerte. Cierra bien ventanas.", action: null };
  }
  const hour = at.getHours();
  if (hour >= 21 && (observation?.skyText || "").toLowerCase().includes("despejado")) {
    return { text: "Noche despejada. Puedes apagar la lámpara del salón.", action: "light.off" };
  }
  return { text: "Sin avisos. La casa está en calma.", action: null };
}
