import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { parseHourly, precipProbForHour, parseObservation, parseAlerts } from "./aemet.ts";

describe("precipProbForHour", () => {
  it("picks the tightest matching period", () => {
    const rows = [
      { periodo: "00-24", value: 10 },
      { periodo: "12-18", value: 40 },
      { periodo: "15-16", value: 80 },
    ];
    assert.equal(precipProbForHour(rows, 15), 80);
    assert.equal(precipProbForHour(rows, 10), 10);
  });
});

describe("parseHourly", () => {
  it("flattens AEMET municipal hours", () => {
    const payload = [
      {
        prediccion: {
          dia: [
            {
              fecha: "2026-09-10T00:00:00",
              estadoCielo: [{ periodo: "15", value: "25", descripcion: "Muy nuboso con lluvia" }],
              temperatura: [{ periodo: "15", value: "14" }],
              precipitacion: [{ periodo: "15", value: "1" }],
              probPrecipitacion: [{ periodo: "12-18", value: "70" }],
              vientoAndRachaMax: [{ periodo: "15", velocidad: ["18"] }],
            },
          ],
        },
      },
    ];
    const hours = parseHourly(payload);
    assert.equal(hours.length, 1);
    assert.equal(hours[0]?.tempC, 14);
    assert.equal(hours[0]?.precipProb, 70);
    assert.ok((hours[0]?.windMs || 0) > 4);
  });
});

describe("parseObservation", () => {
  it("reads last station sample", () => {
    const obs = parseObservation([
      { fint: "2026-09-10T10:00:00", ta: 12, hr: 80, vv: 2.5, dv: 180, prec: 0, pres: 1012 },
      { fint: "2026-09-10T11:00:00", ta: 13.4, hr: 77, vv: 3, dv: 200, prec: 0.2, pres: 1011 },
    ]);
    assert.equal(obs?.tempC, 13.4);
    assert.equal(obs?.precipMm, 0.2);
    assert.equal(obs?.source, "aemet_station");
  });
});

describe("parseAlerts", () => {
  it("flattens CAP info", () => {
    const alerts = parseAlerts({
      identifier: "es.aemet.1",
      info: {
        event: "Lluvias",
        severity: "Moderate",
        onset: "2026-09-10T12:00:00Z",
        expires: "2026-09-10T20:00:00Z",
        headline: "Aviso naranja por lluvias",
        area: { areaDesc: "Madrid" },
      },
    });
    assert.equal(alerts[0]?.severity, "orange");
    assert.equal(alerts[0]?.phenomenon, "Lluvias");
  });
});
