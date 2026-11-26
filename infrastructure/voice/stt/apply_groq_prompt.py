#!/usr/bin/env python3
"""apply_groq_prompt.py — Push home-assistant/voice/groq_stt_prompt.txt to the
openai_whisper_cloud (Groq) integration through the HA options flow.

  ./apply_groq_prompt.py --dry-run   # show current vs new, change nothing
  ./apply_groq_prompt.py             # backup current options to /share, then apply

Model is always whisper-large-v3 (never turbo: worse Spanish WER).
Token: $HA_TOKEN or ~/.config/wayne/ha_token (never printed).
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
PROMPT_FILE = REPO_ROOT / "home-assistant" / "voice" / "groq_stt_prompt.txt"
HA_URL = os.environ.get("HA_URL", "http://192.168.1.110:8123")
HAOS_SSH = os.environ.get("HAOS_SSH", "root@192.168.1.110")
DOMAIN = "openai_whisper_cloud"
MODEL = "whisper-large-v3"


def build_options(current: dict, prompt: str) -> dict:
    return {"model": MODEL, "prompt": prompt, "temperature": float(current.get("temperature", 0.0))}


def _token() -> str:
    tok = os.environ.get("HA_TOKEN", "").strip()
    p = Path.home() / ".config" / "wayne" / "ha_token"
    if not tok and p.is_file():
        tok = p.read_text().strip()
    if not tok:
        sys.exit("HA token missing")
    return tok


def _schema_defaults(schema: list[dict]) -> dict:
    out = {}
    for field in schema:
        sv = (field.get("description") or {}).get("suggested_value")
        out[field["name"]] = sv if sv is not None else field.get("default")
    return out


def main() -> int:
    import requests

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    s = requests.Session()
    s.headers["Authorization"] = f"Bearer {_token()}"
    entries = s.get(f"{HA_URL}/api/config/config_entries/entry", params={"domain": DOMAIN}, timeout=10).json()
    if not entries:
        sys.exit(f"no {DOMAIN} config entry")
    entry_id = entries[0]["entry_id"]

    flow = s.post(f"{HA_URL}/api/config/config_entries/options/flow", json={"handler": entry_id}, timeout=10).json()
    current = _schema_defaults(flow.get("data_schema") or [])
    prompt = PROMPT_FILE.read_text(encoding="utf-8").strip()
    new = build_options(current, prompt)
    print("current:", json.dumps({k: current.get(k) for k in ("model", "temperature", "prompt")}, ensure_ascii=False))
    print("new:    ", json.dumps(new, ensure_ascii=False))

    if args.dry_run or current.get("prompt") == prompt and current.get("model") == MODEL:
        s.delete(f"{HA_URL}/api/config/config_entries/options/flow/{flow['flow_id']}", timeout=10)
        print("dry-run / already applied: nothing changed")
        return 0

    stamp = time.strftime("%Y%m%d-%H%M%S")
    backup = json.dumps({"entry_id": entry_id, "options": current}, ensure_ascii=False)
    subprocess.run(
        ["ssh", "-o", "BatchMode=yes", HAOS_SSH, f"mkdir -p /share/wayne-backups && cat > /share/wayne-backups/groq_options_{stamp}.json"],
        input=backup, text=True, check=True,
    )
    print(f"backup: /share/wayne-backups/groq_options_{stamp}.json")
    res = s.post(f"{HA_URL}/api/config/config_entries/options/flow/{flow['flow_id']}", json=new, timeout=15).json()
    if res.get("type") != "create_entry":
        print(json.dumps(res, ensure_ascii=False), file=sys.stderr)
        return 1
    print("applied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
