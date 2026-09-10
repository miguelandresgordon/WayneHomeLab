import { config } from "./config.ts";
import type { DeviceState, HomeAction } from "./types.ts";

export const HA_ENTITIES = {
  lamp: "light.yeelink_mono6_6409_light",
  tv: "media_player.tv_ga_2",
} as const;

export const HA_SCRIPTS = {
  radioOn: "poner_radio",
  radioOff: "parar_radio",
  tvOn: "encender_tele",
  tvOff: "apagar_tele",
} as const;

const ALLOWED_ACTIONS = new Set<HomeAction>([
  "light.on",
  "light.off",
  "tv.on",
  "tv.off",
  "radio.on",
  "radio.off",
]);

export function isAllowedAction(action: string): action is HomeAction {
  return ALLOWED_ACTIONS.has(action as HomeAction);
}

type HaState = {
  entity_id: string;
  state: string;
  attributes?: Record<string, unknown>;
};

async function haFetch(path: string, init?: RequestInit): Promise<Response> {
  if (!config.haToken) {
    throw new Error("HA_TOKEN missing");
  }
  return fetch(`${config.haBaseUrl}${path}`, {
    ...init,
    headers: {
      Authorization: `Bearer ${config.haToken}`,
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
    signal: AbortSignal.timeout(8000),
  });
}

export async function getState(entityId: string): Promise<HaState | null> {
  const res = await haFetch(`/api/states/${entityId}`);
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`HA ${res.status} ${entityId}`);
  return (await res.json()) as HaState;
}

export async function callService(
  domain: string,
  service: string,
  data: Record<string, unknown>,
): Promise<void> {
  const res = await haFetch(`/api/services/${domain}/${service}`, {
    method: "POST",
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`HA ${domain}.${service} ${res.status} ${text.slice(0, 200)}`);
  }
}

function isOn(state: string | undefined): boolean {
  if (!state) return false;
  return !["off", "unavailable", "unknown", "idle", "standby"].includes(state);
}

export async function readDevices(): Promise<{ reachable: boolean; devices: DeviceState[] }> {
  if (!config.haToken) {
    return { reachable: false, devices: emptyDevices() };
  }
  try {
    const [lamp, tv] = await Promise.all([
      getState(HA_ENTITIES.lamp),
      getState(HA_ENTITIES.tv),
    ]);
    const radio = await getState("media_player.satellite1_c7ffe4_media_player").catch(() => null);
    return {
      reachable: true,
      devices: [
        {
          id: "lamp",
          label: "Lámpara",
          on: isOn(lamp?.state),
          available: Boolean(lamp && lamp.state !== "unavailable"),
          brightness:
            typeof lamp?.attributes?.brightness === "number" ? lamp.attributes.brightness : null,
        },
        {
          id: "tv",
          label: "Tele",
          on: isOn(tv?.state),
          available: Boolean(tv && tv.state !== "unavailable"),
        },
        {
          id: "radio",
          label: "Radio",
          on: isOn(radio?.state),
          available: Boolean(radio),
        },
      ],
    };
  } catch {
    return { reachable: false, devices: emptyDevices() };
  }
}

export async function readHaWeatherTemp(): Promise<number | null> {
  if (!config.haToken || !config.haWeatherEntity) return null;
  try {
    const st = await getState(config.haWeatherEntity);
    const t = st?.attributes?.temperature;
    return typeof t === "number" ? t : null;
  } catch {
    return null;
  }
}

function emptyDevices(): DeviceState[] {
  return [
    { id: "lamp", label: "Lámpara", on: false, available: false },
    { id: "tv", label: "Tele", on: false, available: false },
    { id: "radio", label: "Radio", on: false, available: false },
  ];
}

export async function runAction(action: HomeAction): Promise<void> {
  switch (action) {
    case "light.on":
      await callService("light", "turn_on", { entity_id: HA_ENTITIES.lamp });
      return;
    case "light.off":
      await callService("light", "turn_off", { entity_id: HA_ENTITIES.lamp });
      return;
    case "tv.on":
      await callService("script", HA_SCRIPTS.tvOn, {});
      return;
    case "tv.off":
      await callService("script", HA_SCRIPTS.tvOff, {});
      return;
    case "radio.on":
      await callService("script", HA_SCRIPTS.radioOn, { emisora: "ser" });
      return;
    case "radio.off":
      await callService("script", HA_SCRIPTS.radioOff, {});
      return;
    default:
      throw new Error("ACTION_DENIED");
  }
}

export async function setLampBrightness(brightness: number): Promise<void> {
  const b = Math.max(1, Math.min(255, Math.round(brightness)));
  await callService("light", "turn_on", { entity_id: HA_ENTITIES.lamp, brightness: b });
}
