import type { HourlyPoint, Observation, WeatherAlert } from "./types.ts";

function isoHour(offset: number): string {
  const d = new Date();
  d.setMinutes(0, 0, 0);
  d.setHours(d.getHours() + offset);
  return d.toISOString();
}

export function demoObservation(): Observation {
  return {
    observedAt: new Date().toISOString(),
    source: "demo",
    tempC: 14.2,
    humidity: 78,
    windMs: 3.1,
    windDir: 240,
    precipMm: 0,
    pressureHpa: 1014,
    radiation: null,
    skyCode: "25",
    skyText: "Lluvia débil",
  };
}

export function demoHours(): HourlyPoint[] {
  const skies = [
    "Lluvia débil",
    "Lluvia débil",
    "Intervalos nubosos",
    "Intervalos nubosos",
    "Nuboso",
    "Nuboso",
    "Poco nuboso",
    "Poco nuboso",
    "Despejado",
    "Despejado",
    "Despejado",
    "Poco nuboso",
  ];
  return skies.map((skyText, i) => ({
    hourAt: isoHour(i),
    tempC: 14 - Math.round(i / 4),
    precipProb: i < 2 ? 70 : i < 5 ? 30 : 5,
    skyCode: i < 2 ? "25" : "12",
    skyText,
    windMs: 3 + i * 0.1,
  }));
}

export function demoAlert(): WeatherAlert | null {
  return null;
}
