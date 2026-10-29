import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { isAllowedAction } from "./ha.ts";

describe("HA allowlist", () => {
  it("allows lamp tv radio only", () => {
    assert.equal(isAllowedAction("light.off"), true);
    assert.equal(isAllowedAction("tv.on"), true);
    assert.equal(isAllowedAction("radio.off"), true);
  });

  it("denies mute and foreign entities", () => {
    assert.equal(isAllowedAction("light.mute"), false);
    assert.equal(isAllowedAction("switch.satellite1_c7ffe4_mute_microphones"), false);
    assert.equal(isAllowedAction("media_player.turn_off"), false);
  });
});
