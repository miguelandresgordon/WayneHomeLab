#!/usr/bin/env python3
"""nlu_live_check.py — Ask the *live* HA conversation agent how it would
interpret each sentence (websocket `conversation/agent/homeassistant/debug`:
recognises only, never executes) and compare with the versioned expectations
in home-assistant/voice/nlu_expectations.yaml.

Catches what offline hassil tests cannot: HA's fuzzy-matching fallback,
exposed entity names/aliases and built-in intents of the running version.

  ./nlu_live_check.py            # exit 1 on any mismatch
  ./nlu_live_check.py -v         # print every case
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
EXPECTATIONS = REPO / "home-assistant" / "voice" / "nlu_expectations.yaml"
HA_WS = os.environ.get("HA_WS", "ws://192.168.1.110:8123/api/websocket")


def evaluate(cases: list[dict], results: list[dict | None]) -> list[str]:
    failures: list[str] = []
    for case, res in zip(cases, results):
        want = case.get("intent")
        allowed = set(want) if isinstance(want, list) else {want}
        got = (res or {}).get("intent", {}).get("name") if res else None
        if got not in allowed:
            how = (res or {}).get("source", "")
            fuzzy = " (fuzzy)" if res and res.get("match") is False else ""
            failures.append(f"{case['text']!r}: expected {sorted(map(str, allowed))}, got {got}{fuzzy} {how}".rstrip())
    return failures


def _token() -> str:
    tok = os.environ.get("HA_TOKEN", "").strip()
    p = Path.home() / ".config" / "wayne" / "ha_token"
    if not tok and p.is_file():
        tok = p.read_text().strip()
    if not tok:
        sys.exit("HA token missing")
    return tok


async def _debug(sentences: list[str]) -> list[dict | None]:
    import websockets

    out: list[dict | None] = []
    async with websockets.connect(HA_WS, max_size=2**24) as ws:
        await ws.recv()
        await ws.send(json.dumps({"type": "auth", "access_token": _token()}))
        await ws.recv()
        # One sentence per call: a single failing sentence makes HA fail the whole batch.
        for i, s in enumerate(sentences, start=1):
            await ws.send(json.dumps({"id": i, "type": "conversation/agent/homeassistant/debug", "sentences": [s], "language": "es"}))
            r = json.loads(await ws.recv())
            out.append(r["result"]["results"][0] if r.get("success") else {"intent": {"name": f"ERROR:{r.get('error', {}).get('message')}"}})
    return out


def main() -> int:
    import yaml

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-v", "--verbose", action="store_true")
    ap.add_argument("--file", default=str(EXPECTATIONS))
    args = ap.parse_args()
    cases = yaml.safe_load(Path(args.file).read_text(encoding="utf-8"))["cases"]
    results = asyncio.run(_debug([c["text"] for c in cases]))
    if args.verbose:
        for c, r in zip(cases, results):
            print(f"{c['text']!r:48} -> {(r or {}).get('intent', {}).get('name')}")
    failures = evaluate(cases, results)
    for f in failures:
        print("FAIL", f)
    print(f"{len(cases) - len(failures)}/{len(cases)} live NLU cases OK")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
