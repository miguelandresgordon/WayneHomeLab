import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { buildInsight, buildPhrase, nextRain } from "./insights.ts";
import type { HourlyPoint } from "./types.ts";

const hours = (iso: string, precipProb: number, skyText: string): HourlyPoint => ({
  hourAt: iso,
  tempC: 14,
  precipProb,
  skyCode: "25",
  skyText,
  windMs: 2,
});

describe("nextRain", () => {
  it("returns first wet hour in the next 12h", () => {
    const from = new Date("2026-09-10T15:00:00Z");
    const found = nextRain(
      [
        hours("2026-09-10T14:00:00Z", 80, "Lluvia"),
        hours("2026-09-10T17:00:00Z", 70, "Lluvia débil"),
      ],
      from,
    );
    assert.equal(found?.hourAt, "2026-09-10T17:00:00Z");
  });
});

describe("buildPhrase", () => {
  it("leads with orange alert", () => {
    const phrase = buildPhrase(null, [], {
      id: "1",
      severity: "orange",
      phenomenon: "Viento",
      area: "Madrid",
      onset: null,
      expires: null,
      summary: "Viento",
    });
    assert.equal(phrase.lead, "Viento");
    assert.equal(phrase.follow, "aviso AEMET");
  });
});

describe("buildInsight", () => {
  it("points at rain this evening without inventing HA automations", () => {
    const from = new Date("2026-09-10T16:00:00Z");
    const insight = buildInsight(
      [hours("2026-09-10T17:30:00Z", 80, "Lluvia débil")],
      null,
      null,
      from,
    );
    assert.match(insight.text, /17 h/);
    assert.equal(insight.action, null);
  });
});
