#!/usr/bin/env python3
"""spotify_probe.py — Measure Spotify track-change latency on the Satellite1
(Music Assistant player) and count MA retry lines during the run.

Starts a playlist/URI on media_player.satellite1 at a low temporary volume,
then presses «next» N times. For each press it records the time until the new
title is `playing` (and, with --use-position, until the reported position
moves). Exit 1 when the median exceeds --threshold (default 2 s).

  ./spotify_probe.py --uri "spotify--XXXX://playlist/..." --presses 8 --out run.json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import statistics
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

HA_URL = os.environ.get("HA_URL", "http://192.168.1.110:8123")
HAOS_SSH = os.environ.get("HAOS_SSH", "root@192.168.1.110")
MA_PLAYER = "media_player.satellite1"
DEVICE_PLAYER = "media_player.satellite1_c7ffe4_media_player"
RETRY_RE = re.compile(r"\[music_assistant[^\]]*\] (Attempt \d)/5 failed")


@dataclass(frozen=True)
class Sample:
    t: float
    title: str | None
    state: str
    position: float | None = None


def switch_latency(timeline: list[Sample], t_cmd: float, old_title: str | None, use_position: bool = False) -> float | None:
    """Seconds from t_cmd until a different title is playing (and, optionally,
    its position has started moving)."""
    first_pos: float | None = None
    for s in sorted(timeline, key=lambda x: x.t):
        if s.t < t_cmd or s.title in (None, old_title) or s.state != "playing":
            continue
        if not use_position:
            return s.t - t_cmd
        if first_pos is None:
            first_pos = s.position or 0.0
            if (s.position or 0) > 0:
                return s.t - t_cmd
            continue
        if (s.position or 0) > first_pos:
            return s.t - t_cmd
    return None


def summarize(latencies: list[float | None], threshold_s: float) -> dict:
    ok = [x for x in latencies if x is not None]
    med = statistics.median(ok) if ok else None
    return {
        "n": len(latencies),
        "failed": len(latencies) - len(ok),
        "median_s": med,
        "max_s": max(ok) if ok else None,
        "all_s": [round(x, 2) if x is not None else None for x in latencies],
        "threshold_s": threshold_s,
        "pass": bool(ok) and len(ok) == len(latencies) and med is not None and med <= threshold_s,
    }


def count_retries(log_text: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for m in RETRY_RE.finditer(log_text):
        out[m.group(1)] = out.get(m.group(1), 0) + 1
    return out


# --------------------------------------------------------------------------- #
def _token() -> str:
    tok = os.environ.get("HA_TOKEN", "").strip()
    p = Path.home() / ".config" / "wayne" / "ha_token"
    if not tok and p.is_file():
        tok = p.read_text().strip()
    if not tok:
        sys.exit("HA token missing")
    return tok


def run(args: argparse.Namespace) -> int:
    import requests

    s = requests.Session()
    s.headers["Authorization"] = f"Bearer {_token()}"

    def st() -> dict:
        return s.get(f"{HA_URL}/api/states/{MA_PLAYER}", timeout=5).json()

    def call(domain: str, svc: str, data: dict) -> None:
        s.post(f"{HA_URL}/api/services/{domain}/{svc}", json=data, timeout=30).raise_for_status()

    vol0 = s.get(f"{HA_URL}/api/states/{DEVICE_PLAYER}", timeout=5).json()["attributes"].get("volume_level")
    t_start = time.strftime("%Y-%m-%d %H:%M:%S")
    latencies: list[float | None] = []
    try:
        call("media_player", "volume_set", {"entity_id": DEVICE_PLAYER, "volume_level": args.volume})
        call("music_assistant", "play_media", {"entity_id": MA_PLAYER, "media_id": args.uri, "media_type": args.media_type, "enqueue": "replace"})
        deadline = time.time() + 30
        while time.time() < deadline and st()["state"] != "playing":
            time.sleep(0.3)
        time.sleep(args.settle)
        for i in range(args.presses):
            cur = st()
            old = cur["attributes"].get("media_title")
            timeline: list[Sample] = []
            t_cmd = time.time()
            call("media_player", "media_next_track", {"entity_id": MA_PLAYER})
            while time.time() - t_cmd < args.timeout:
                x = st()
                a = x["attributes"]
                timeline.append(Sample(time.time(), a.get("media_title"), x["state"], a.get("media_position")))
                time.sleep(0.2)
                if switch_latency(timeline, t_cmd, old, args.use_position) is not None:
                    break
            lat = switch_latency(timeline, t_cmd, old, args.use_position)
            latencies.append(lat)
            print(f"[{i + 1}/{args.presses}] {old!r} -> {timeline[-1].title!r}: {lat if lat is None else round(lat, 2)} s", flush=True)
            time.sleep(args.settle)
    finally:
        try:
            call("media_player", "media_pause", {"entity_id": MA_PLAYER})
        finally:
            if vol0 is not None:
                call("media_player", "volume_set", {"entity_id": DEVICE_PLAYER, "volume_level": vol0})

    logs = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", HAOS_SSH, "ha apps logs d5369777_music_assistant -n 2000"],
        capture_output=True, text=True, check=False,
    ).stdout
    recent = "\n".join(line for line in logs.splitlines() if line[5:24] >= t_start or line[:19] >= t_start)
    summary = summarize(latencies, args.threshold) | {"retries_during_run": count_retries(recent), "started": t_start}
    print(json.dumps(summary, indent=2))
    if args.out:
        Path(args.out).write_text(json.dumps(summary, indent=2))
    return 0 if summary["pass"] else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--uri", required=True)
    ap.add_argument("--media-type", default="playlist")
    ap.add_argument("--presses", type=int, default=8)
    ap.add_argument("--volume", type=float, default=0.15)
    ap.add_argument("--settle", type=float, default=6.0, help="seconds to listen between presses")
    ap.add_argument("--timeout", type=float, default=20.0)
    ap.add_argument("--threshold", type=float, default=2.0)
    ap.add_argument("--use-position", action="store_true")
    ap.add_argument("--out", default="")
    return run(ap.parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
