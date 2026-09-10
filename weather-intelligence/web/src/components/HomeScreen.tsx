import { useCallback, useEffect, useState } from "react";
import type { DeviceState, HomeAction, HomeView } from "../../../server/types.ts";
import { fetchHome, postAction } from "../lib/api.ts";
import { SkyField } from "./SkyField.tsx";

function hourLabel(iso: string): string {
  return String(new Date(iso).getHours());
}

function actionForDevice(device: DeviceState): HomeAction {
  if (device.id === "lamp") return device.on ? "light.off" : "light.on";
  if (device.id === "tv") return device.on ? "tv.off" : "tv.on";
  return device.on ? "radio.off" : "radio.on";
}

function verb(device: DeviceState): string {
  if (device.id === "lamp") return device.on ? "Apagar lámpara" : "Encender lámpara";
  if (device.id === "tv") return device.on ? "Apagar tele" : "Encender tele";
  return device.on ? "Parar radio" : "Poner radio";
}

export function HomeScreen({
  onCasa,
  onNotice,
}: {
  onCasa: () => void;
  onNotice: (text: string) => void;
}) {
  const [data, setData] = useState<HomeView | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    fetchHome()
      .then((view) => {
        setData(view);
        setError(null);
      })
      .catch(() => setError("No se pudo leer el cielo. Reintenta."));
  }, []);

  useEffect(() => {
    load();
    const id = window.setInterval(load, 60_000);
    const onVis = () => {
      if (document.visibilityState === "visible") load();
    };
    document.addEventListener("visibilitychange", onVis);
    return () => {
      window.clearInterval(id);
      document.removeEventListener("visibilitychange", onVis);
    };
  }, [load]);

  async function toggle(device: DeviceState) {
    if (!device.available) {
      onNotice("Home Assistant no responde.");
      return;
    }
    const action = actionForDevice(device);
    try {
      await postAction(action);
      onNotice(verb(device));
      load();
    } catch {
      onNotice("Home Assistant no responde.");
    }
  }

  if (error && !data) {
    return (
      <SkyField sky="overcast">
        <p className="font-ui text-[17px] text-mist">{error}</p>
        <button className="mt-6 font-ui text-gulf" type="button" onClick={load}>
          Reintenta
        </button>
      </SkyField>
    );
  }

  if (!data) {
    return (
      <SkyField sky="night">
        <p className="font-ui text-haze">Leyendo AEMET…</p>
      </SkyField>
    );
  }

  const lamp = data.devices.find((d) => d.id === "lamp");
  const tv = data.devices.find((d) => d.id === "tv");

  return (
    <SkyField sky={data.sky}>
      <p className="font-ui text-[15px] text-haze">{data.locationName}</p>

      <h1 className="settle mt-8 font-phrase text-phrase font-normal text-mist">
        {data.phrase.lead}
        <span className="mt-2 block text-[1.65rem] text-mist/80">{data.phrase.follow}</span>
      </h1>

      <p className="mt-10 font-ui text-temp font-medium tracking-tight text-mist">
        {data.tempC !== null ? `${Math.round(data.tempC)}°` : "—"}
      </p>
      {data.haTempC !== null ? (
        <p className="mt-2 font-ui text-[15px] text-haze">HA {Math.round(data.haTempC)}°</p>
      ) : null}

      {data.stale && data.staleReason === "AEMET_STALE" ? (
        <p className="mt-4 font-ui text-[15px] text-gale">
          AEMET no responde. Último dato a las{" "}
          {data.observation
            ? `${new Date(data.observation.observedAt).getHours()}:${String(
                new Date(data.observation.observedAt).getMinutes(),
              ).padStart(2, "0")}`
            : "—"}
          .
        </p>
      ) : null}

      <div className="hours mt-12 flex gap-6 overflow-x-auto pb-2">
        {data.hours.map((h) => (
          <div key={h.hourAt} className="w-10 shrink-0">
            <p className="font-ui text-[13px] text-haze">{hourLabel(h.hourAt)}</p>
            <p className="mt-2 font-ui text-[17px] text-mist">
              {h.tempC !== null ? Math.round(h.tempC) : "—"}
            </p>
            <span
              className="mt-3 block h-10 w-[3px] rounded-full bg-gulf/80"
              style={{ height: `${8 + (h.precipProb || 0) * 0.28}px` }}
              title={h.skyText || ""}
            />
          </div>
        ))}
      </div>

      {data.alert ? (
        <button
          type="button"
          className="mt-10 max-w-[34ch] text-left font-ui text-[17px]"
          style={{ color: data.alert.severity === "red" ? "#B54A3C" : "#C4A35A" }}
        >
          {data.alert.summary}
        </button>
      ) : (
        <p className="mt-10 max-w-[34ch] font-ui text-[17px] leading-snug text-mist/90">
          {data.insight.text}
        </p>
      )}

      <div className="fixed inset-x-0 bottom-0 bg-ink/70 px-6 pb-[max(1.25rem,env(safe-area-inset-bottom))] pt-4 backdrop-blur-md lg:left-[12vw] lg:right-auto lg:w-[420px]">
        <div className="flex items-end justify-between gap-4">
          <button
            type="button"
            className="text-left font-ui text-[16px] text-mist"
            onClick={() => lamp && toggle(lamp)}
          >
            Lámpara
            <span className="mt-1 block text-[13px] text-haze">
              {lamp?.available ? (lamp.on ? "encendida" : "apagada") : "sin enlace"}
            </span>
          </button>
          <button
            type="button"
            className="text-left font-ui text-[16px] text-mist"
            onClick={() => tv && toggle(tv)}
          >
            Tele
            <span className="mt-1 block text-[13px] text-haze">
              {tv?.available ? (tv.on ? "encendida" : "apagada") : "sin enlace"}
            </span>
          </button>
          <button type="button" className="text-left font-ui text-[16px] text-mist" onClick={onCasa}>
            Casa
            <span className="mt-1 block text-[13px] text-haze">salón</span>
          </button>
        </div>
      </div>
    </SkyField>
  );
}
