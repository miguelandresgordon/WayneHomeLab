#!/usr/bin/env python3
"""radio_probe.py — Measure radio start latency and cuts on the Satellite1.

Starts a station through one *route*, samples the player state every second
for --duration seconds and fails (exit 1) when explicit thresholds are not met.

Routes:
  esphome  media_player.play_media on the ESPHome player with the raw stream URL
           (HA wraps it in its ffmpeg proxy -> FLAC to the Satellite1).
  ma       media_player.play_media on the Music Assistant player (Sendspin).
  script   script.poner_radio (whatever the production path is).

Optional evidence while it runs:
  --resources      every 10 s: `ha core stats` / MA add-on stats over SSH + RSSI
  --esphome-logs   device logs (DEBUG) via the ESPHome native API; needs
                   ESPHOME_NOISE_PSK in the environment (never printed/stored).

Token: $HA_TOKEN or ~/.config/wayne/ha_token. Restores the original volume.

  ./radio_probe.py --route esphome --station ser --duration 1800 --out run.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import subprocess
import sys
import threading
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

HA_URL = os.environ.get("HA_URL", "http://192.168.1.110:8123")
ESPHOME_PLAYER = "media_player.satellite1_c7ffe4_media_player"
MA_PLAYER = "media_player.satellite1"
RSSI_SENSOR = "sensor.satellite1_c7ffe4_wi_fi_signal_strength"
SATELLITE_HOST = os.environ.get("SATELLITE_HOST", "192.168.1.85")
HAOS_SSH = os.environ.get("HAOS_SSH", "root@192.168.1.110")

# Mirrors script.poner_radio (home-assistant/includes/scripts.yaml).
STATIONS = {
    "ser": "https://playerservices.streamtheworld.com/api/livestream-redirect/SER_MADRID.mp3",
    "radiovoz": "https://live.radiovoz.es/mp3/stream_lugo.mp3",
    "filispim": "https://streaming.cuacfm.org/filispim.mp3",
    "almenara": "https://cervera.eldialdigital.com:25211/stream",
    "radio3": "https://rtvelivestream.rtve.es/rtvesec/rne/rne_r3_main.m3u8",
}

PLAYING = {"playing"}


# --------------------------------------------------------------------------- #
# Pure analysis (unit-tested in tests/test_radio_probe.py)
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Sample:
    t: float
    state: str


@dataclass
class Result:
    start_latency_s: float | None
    drops: int
    total_gap_s: float
    longest_gap_s: float
    play_ratio: float
    duration_s: float
    gaps: list[tuple[float, float]] = field(default_factory=list)


@dataclass(frozen=True)
class Thresholds:
    max_start_latency_s: float = 5.0
    max_drops: int = 0


def analyze(samples: list[Sample], t_command: float) -> Result:
    """Start latency = first `playing` after the command; a drop = leaving
    `playing` after it started (any state, incl. unavailable); gap = time
    until it plays again (or end of run)."""
    samples = sorted(samples, key=lambda s: s.t)
    if not samples:
        return Result(None, 0, 0.0, 0.0, 0.0, 0.0)
    t_end = samples[-1].t
    duration = max(0.0, t_end - t_command)
    first_play = next((s.t for s in samples if s.state in PLAYING and s.t >= t_command), None)
    if first_play is None:
        return Result(None, 0, 0.0, 0.0, 0.0, duration)

    gaps: list[tuple[float, float]] = []
    gap_start: float | None = None
    for s in samples:
        if s.t < first_play:
            continue
        if s.state in PLAYING:
            if gap_start is not None:
                gaps.append((gap_start, s.t))
                gap_start = None
        elif gap_start is None:
            gap_start = s.t
    if gap_start is not None:
        gaps.append((gap_start, t_end))

    lengths = [b - a for a, b in gaps]
    total_gap = sum(lengths)
    # Ratio of the time since it first started that it was actually playing.
    play_window = max(1e-9, t_end - first_play)
    played = max(0.0, play_window - total_gap)
    return Result(
        start_latency_s=first_play - t_command,
        drops=len(gaps),
        total_gap_s=total_gap,
        longest_gap_s=max(lengths, default=0.0),
        play_ratio=min(1.0, played / play_window) if t_end > first_play else 1.0,
        duration_s=duration,
        gaps=gaps,
    )


def verdict(r: Result, th: Thresholds) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if r.start_latency_s is None:
        reasons.append("never started playing")
    elif r.start_latency_s > th.max_start_latency_s:
        reasons.append(f"start latency {r.start_latency_s:.1f}s > {th.max_start_latency_s}s")
    if r.drops > th.max_drops:
        reasons.append(f"{r.drops} drop(s) > {th.max_drops} (longest gap {r.longest_gap_s:.0f}s)")
    return (not reasons, reasons)


# --------------------------------------------------------------------------- #
# Live runner
# --------------------------------------------------------------------------- #
def _token() -> str:
    tok = os.environ.get("HA_TOKEN", "").strip()
    if not tok:
        p = Path.home() / ".config" / "wayne" / "ha_token"
        tok = p.read_text().strip() if p.is_file() else ""
    if not tok:
        sys.exit("HA token missing: export HA_TOKEN or create ~/.config/wayne/ha_token")
    return tok


class HA:
    def __init__(self, token: str) -> None:
        import requests  # local import: unit tests do not need it

        self.s = requests.Session()
        self.s.headers["Authorization"] = f"Bearer {token}"

    def state(self, entity: str) -> dict:
        r = self.s.get(f"{HA_URL}/api/states/{entity}", timeout=5)
        r.raise_for_status()
        return r.json()

    def call(self, domain: str, service: str, data: dict) -> None:
        r = self.s.post(f"{HA_URL}/api/services/{domain}/{service}", json=data, timeout=30)
        r.raise_for_status()


def _ssh_stats() -> dict:
    cmd = (
        "printf 'core '; ha core stats --raw-json; echo; "
        "printf 'ma '; ha apps stats d5369777_music_assistant --raw-json; echo; free -m | awk '/Mem/{print \"vm_avail_mb\",$7}'"
    )
    out = subprocess.run(["ssh", "-o", "BatchMode=yes", HAOS_SSH, cmd], capture_output=True, text=True, timeout=20).stdout
    res: dict = {}
    for line in out.splitlines():
        if line.startswith(("core ", "ma ")):
            name, blob = line.split(" ", 1)
            try:
                d = json.loads(blob)["data"]
                res[f"{name}_cpu"] = d.get("cpu_percent")
                res[f"{name}_mem_mb"] = round(d.get("memory_usage", 0) / 2**20)
            except (ValueError, KeyError):
                pass
        elif line.startswith("vm_avail_mb"):
            res["vm_avail_mb"] = int(line.split()[1])
    return res


def _esphome_logs(stop: threading.Event, sink: list[str]) -> None:
    psk = os.environ.get("ESPHOME_NOISE_PSK", "")
    if not psk:
        sink.append("esphome-logs disabled: ESPHOME_NOISE_PSK not set")
        return
    import aioesphomeapi
    from aioesphomeapi import LogLevel

    # Everything except the ambient-light sensor spam (ltr_als_ps warns every second).
    noise = re.compile(r"ltr_als_ps")

    async def run() -> None:
        cli = aioesphomeapi.APIClient(SATELLITE_HOST, 6053, None, noise_psk=psk)
        await cli.connect(login=True)

        def on_log(msg) -> None:  # noqa: ANN001
            text = msg.message.decode(errors="replace") if isinstance(msg.message, bytes) else str(msg.message)
            text = re.sub(r"\x1b\[[0-9;]*m", "", text)
            if not noise.search(text):
                sink.append(f"{time.time():.1f} {text}")

        unsub = cli.subscribe_logs(on_log, log_level=LogLevel.LOG_LEVEL_VERY_VERBOSE)
        while not stop.is_set():
            await asyncio.sleep(0.5)
        if callable(unsub):
            unsub()
        await cli.disconnect()

    try:
        asyncio.run(run())
    except Exception as exc:  # noqa: BLE001 — evidence collector must never kill the run
        sink.append(f"esphome-logs error: {exc!r}")


def run_live(args: argparse.Namespace) -> int:
    ha = HA(_token())
    # script.poner_radio plays via Music Assistant since F1b (ESPHome only as fallback)
    player = ESPHOME_PLAYER if args.route == "esphome" else MA_PLAYER
    url = STATIONS[args.station]
    original_volume = ha.state(player)["attributes"].get("volume_level")

    stop = threading.Event()
    logs: list[str] = []
    resources: list[dict] = []
    threads: list[threading.Thread] = []
    if args.esphome_logs:
        threads.append(threading.Thread(target=_esphome_logs, args=(stop, logs), daemon=True))
    if args.resources:
        def res_loop() -> None:
            while not stop.is_set():
                try:
                    d = _ssh_stats()
                    d["rssi"] = ha.state(RSSI_SENSOR)["state"]
                    d["t"] = round(time.time(), 1)
                    resources.append(d)
                except Exception as exc:  # noqa: BLE001
                    resources.append({"t": time.time(), "error": repr(exc)})
                stop.wait(10)
        threads.append(threading.Thread(target=res_loop, daemon=True))
    for th in threads:
        th.start()

    samples: list[Sample] = []
    try:
        if args.volume is not None:
            ha.call("media_player", "volume_set", {"entity_id": player, "volume_level": args.volume})
        t_cmd = time.time()
        if args.route == "script":
            ha.call("script", "poner_radio", {"emisora": args.station})
        else:
            ha.call("media_player", "play_media", {"entity_id": player, "media_content_type": "music", "media_content_id": url})
        t_end = t_cmd + args.duration
        last = None
        while time.time() < t_end:
            try:
                st = ha.state(player)["state"]
            except Exception:  # noqa: BLE001
                st = "probe_error"
            now = time.time()
            samples.append(Sample(now, st))
            if st != last:
                print(f"[{now - t_cmd:7.1f}s] {player} -> {st}", flush=True)
                last = st
            time.sleep(args.interval)
    finally:
        if not args.keep_playing:
            for p in {player, ESPHOME_PLAYER}:
                try:
                    ha.call("media_player", "media_stop", {"entity_id": p})
                except Exception:  # noqa: BLE001
                    pass
        if original_volume is not None and args.volume is not None:
            ha.call("media_player", "volume_set", {"entity_id": player, "volume_level": original_volume})
        stop.set()
        for th in threads:
            th.join(timeout=15)

    result = analyze(samples, t_cmd)
    ok, reasons = verdict(result, Thresholds(args.max_start_latency, args.max_drops))
    report = {
        "route": args.route,
        "station": args.station,
        "started": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(t_cmd)),
        "result": asdict(result) | {"gaps": [(round(a - t_cmd, 1), round(b - t_cmd, 1)) for a, b in result.gaps]},
        "thresholds": {"max_start_latency_s": args.max_start_latency, "max_drops": args.max_drops},
        "pass": ok,
        "reasons": reasons,
        "resources": resources,
        "esphome_log_lines": logs[-400:],
    }
    if args.out:
        Path(args.out).write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(json.dumps({k: report[k] for k in ("route", "station", "result", "pass", "reasons")}, indent=2, ensure_ascii=False))
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--route", choices=("esphome", "ma", "script"), default="script")
    ap.add_argument("--station", choices=sorted(STATIONS), default="ser")
    ap.add_argument("--duration", type=float, default=1800.0, help="seconds (default 30 min)")
    ap.add_argument("--interval", type=float, default=1.0)
    ap.add_argument("--volume", type=float, default=None, help="temporary volume 0-1 (restored afterwards)")
    ap.add_argument("--max-start-latency", type=float, default=5.0)
    ap.add_argument("--max-drops", type=int, default=0)
    ap.add_argument("--resources", action="store_true")
    ap.add_argument("--esphome-logs", action="store_true")
    ap.add_argument("--keep-playing", action="store_true")
    ap.add_argument("--out", default="")
    return run_live(ap.parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
