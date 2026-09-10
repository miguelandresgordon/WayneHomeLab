export type SkyKind = "clear" | "overcast" | "rain" | "storm" | "night" | "fog";

export type AlertSeverity = "yellow" | "orange" | "red" | "unknown";

export type HomeAction =
  | "light.on"
  | "light.off"
  | "tv.on"
  | "tv.off"
  | "radio.on"
  | "radio.off";

export type Observation = {
  observedAt: string;
  source: "aemet_station" | "ha_weather" | "demo";
  tempC: number | null;
  humidity: number | null;
  windMs: number | null;
  windDir: number | null;
  precipMm: number | null;
  pressureHpa: number | null;
  radiation: number | null;
  skyCode: string | null;
  skyText: string | null;
};

export type HourlyPoint = {
  hourAt: string;
  tempC: number | null;
  precipProb: number | null;
  skyCode: string | null;
  skyText: string | null;
  windMs: number | null;
};

export type WeatherAlert = {
  id: string;
  severity: AlertSeverity;
  phenomenon: string;
  area: string;
  onset: string | null;
  expires: string | null;
  summary: string;
};

export type DeviceState = {
  id: "lamp" | "tv" | "radio";
  label: string;
  on: boolean;
  available: boolean;
  brightness?: number | null;
};

export type HomeView = {
  generatedAt: string;
  stale: boolean;
  staleReason: "AEMET_STALE" | "HA_UNREACHABLE" | null;
  locationName: string;
  observation: Observation | null;
  haTempC: number | null;
  phrase: { lead: string; follow: string };
  tempC: number | null;
  sky: SkyKind;
  hours: HourlyPoint[];
  alert: WeatherAlert | null;
  insight: { text: string; action: HomeAction | null };
  haReachable: boolean;
  devices: DeviceState[];
};

export type CasaView = {
  generatedAt: string;
  haReachable: boolean;
  staleReason: "HA_UNREACHABLE" | null;
  devices: DeviceState[];
};

export type ContextPack = {
  generatedAt: string;
  locationName: string;
  observation: Observation | null;
  hours: HourlyPoint[];
  alert: WeatherAlert | null;
  devices: DeviceState[];
  insight: { text: string; action: HomeAction | null };
};
