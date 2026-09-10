import type { SkyKind } from "./types.ts";

/** AEMET estado del cielo → recinto visual. */
export function skyKindFromCode(code: string | null | undefined, at = new Date()): SkyKind {
  const raw = (code || "").toLowerCase();
  const hour = at.getHours();
  const night = hour >= 21 || hour < 7;

  if (raw.includes("51") || raw.includes("52") || raw.includes("53") || raw.includes("54") || raw.includes("storm") || raw.includes("tormenta")) {
    return "storm";
  }
  if (
    raw.includes("fog") ||
    raw.includes("niebla") ||
    raw.startsWith("81") ||
    raw.startsWith("82")
  ) {
    return "fog";
  }
  if (
    raw.includes("23") ||
    raw.includes("24") ||
    raw.includes("25") ||
    raw.includes("26") ||
    raw.includes("27") ||
    raw.includes("43") ||
    raw.includes("44") ||
    raw.includes("45") ||
    raw.includes("46") ||
    raw.includes("rain") ||
    raw.includes("lluvia") ||
    raw.includes("chubasco")
  ) {
    return "rain";
  }
  if (
    raw.includes("14") ||
    raw.includes("15") ||
    raw.includes("16") ||
    raw.includes("17") ||
    raw.includes("nuboso") ||
    raw.includes("cubierto")
  ) {
    return "overcast";
  }
  if (night) return "night";
  return "clear";
}

export function momentLabel(at = new Date()): string {
  const h = at.getHours();
  if (h < 7) return "de madrugada";
  if (h < 12) return "por la mañana";
  if (h < 15) return "al mediodía";
  if (h < 19) return "por la tarde";
  if (h < 22) return "al anochecer";
  return "por la noche";
}
