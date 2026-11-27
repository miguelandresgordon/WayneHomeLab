import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { parseArchiveCsv } from "./import-archive.ts";

describe("parseArchiveCsv", () => {
  it("reads generic WIC csv", () => {
    const rows = parseArchiveCsv(`timestamp,temp_c,humidity,wind_ms,precip_mm,sky_text
2026-09-01T12:00:00Z,21.5,40,2.1,0,Despejado
`);
    assert.equal(rows.length, 1);
    assert.equal(rows[0]?.tempC, 21.5);
  });

  it("reads AEMET climatologia diaria and converts wind km/h", () => {
    const rows = parseArchiveCsv(`fecha,indicativo,tmed,prec,velmedia
2026-09-01,3195,"21,5","0,0","18,0"
`);
    assert.equal(rows[0]?.tempC, 21.5);
    assert.ok(Math.abs((rows[0]?.windMs || 0) - 5) < 0.1);
  });
});
