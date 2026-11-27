import { useCallback, useEffect, useState } from "react";
import type { CasaView, DeviceState, HomeAction } from "../../../server/types.ts";
import { fetchCasa, postAction, postBrightness } from "../lib/api.ts";
import { SkyField } from "./SkyField.tsx";

function actionFor(device: DeviceState): HomeAction {
  if (device.id === "lamp") return device.on ? "light.off" : "light.on";
  if (device.id === "tv") return device.on ? "tv.off" : "tv.on";
  return device.on ? "radio.off" : "radio.on";
}

function doneLabel(device: DeviceState): string {
  if (device.id === "lamp") return device.on ? "Lámpara apagada" : "Lámpara encendida";
  if (device.id === "tv") return device.on ? "Tele apagada" : "Tele encendida";
  return device.on ? "Radio parada" : "Radio puesta";
}

function cta(device: DeviceState): string {
  if (device.id === "lamp") return device.on ? "Apagar lámpara" : "Encender lámpara";
  if (device.id === "tv") return device.on ? "Apagar tele" : "Encender tele";
  return device.on ? "Parar radio" : "Poner radio";
}

export function CasaScreen({
  onBack,
  onNotice,
}: {
  onBack: () => void;
  onNotice: (text: string) => void;
}) {
  const [data, setData] = useState<CasaView | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const load = useCallback(() => {
    fetchCasa()
      .then((view) => {
        setData(view);
        setError(null);
      })
      .catch(() => setError("Home Assistant no responde."));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function run(device: DeviceState) {
    setBusy(device.id);
    try {
      await postAction(actionFor(device));
      onNotice(doneLabel(device));
      load();
    } catch {
      onNotice("Home Assistant no responde.");
    } finally {
      setBusy(null);
    }
  }

  async function dim(value: number) {
    try {
      await postBrightness(value);
      onNotice("Lámpara encendida");
      load();
    } catch {
      onNotice("Home Assistant no responde.");
    }
  }

  const lamp = data?.devices.find((d) => d.id === "lamp");

  return (
    <SkyField sky="night">
      <button type="button" className="font-ui text-[15px] text-haze" onClick={onBack}>
        Cielo
      </button>
      <h1 className="mt-8 font-phrase text-phrase font-normal text-mist">Salón</h1>
      <p className="mt-3 max-w-[34ch] font-ui text-[17px] text-haze">
        Tres cosas. La bombilla del dormitorio no está aquí.
      </p>

      {error || data?.staleReason === "HA_UNREACHABLE" ? (
        <p className="mt-8 font-ui text-[15px] text-gale">
          {error || "Home Assistant no responde. El cielo sigue en la pantalla anterior."}
        </p>
      ) : null}

      {!data && !error ? (
        <p className="mt-14 font-ui text-[15px] text-haze">Leyendo la casa…</p>
      ) : null}

      <ul className="mt-14 space-y-12">
        {(data?.devices || []).map((device) => (
          <li key={device.id}>
            <p className="font-phrase text-[2rem] leading-none text-mist">{device.label}</p>
            <p className="mt-2 font-ui text-[15px] text-haze">
              {device.available ? (device.on ? "encendida" : "apagada") : "sin enlace"}
            </p>
            <button
              type="button"
              disabled={!device.available || busy === device.id}
              className="mt-5 font-ui text-[17px] text-gulf disabled:text-haze"
              onClick={() => run(device)}
            >
              {cta(device)}
            </button>
            {device.id === "lamp" && lamp?.available ? (
              <label className="mt-6 block max-w-[220px] font-ui text-[13px] text-haze">
                Brillo
                <input
                  className="mt-2 w-full accent-gulf"
                  type="range"
                  min={8}
                  max={255}
                  defaultValue={lamp.brightness ?? 180}
                  onPointerUp={(ev) => dim(Number((ev.target as HTMLInputElement).value))}
                />
              </label>
            ) : null}
          </li>
        ))}
      </ul>
    </SkyField>
  );
}
