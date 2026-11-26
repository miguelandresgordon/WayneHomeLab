#!/usr/bin/env python3
"""screenshot_dashboards.py — Real screenshots of the YAML dashboards at
laptop (1440x900) and phone (390x844, DPR 3) widths, for visual review.

Runs inside the official Playwright image (no browser install on the Mac):

  docker run --rm -e HA_TOKEN -v "$PWD":/repo -v /Volumes/EXTERNALSTG/Desarrollo/wayne-shots:/out \
    mcr.microsoft.com/playwright/python:v1.55.0-noble \
    sh -c "pip install -q playwright==1.55.0 && python /repo/infrastructure/ha/screenshot_dashboards.py --out /out"

Auth: injects the long-lived token into the frontend's localStorage (never
written to disk). Also reports cards that failed to render (hui-error-card).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

HA = os.environ.get("HA_URL", "http://192.168.1.110:8123")
DASHBOARDS = ["wayne-casa/inicio", "wayne-tiempo/inicio", "wayne-mariano/inicio"]
VIEWPORTS = {"laptop": ({"width": 1440, "height": 900}, 1), "movil": ({"width": 390, "height": 844}, 3)}

COUNT_ERRORS_JS = """
() => {
  const out = [];
  const walk = (root) => {
    root.querySelectorAll('*').forEach(el => {
      if (el.tagName && el.tagName.toLowerCase() === 'hui-error-card') out.push((el.textContent || '').slice(0, 160));
      if (el.shadowRoot) walk(el.shadowRoot);
    });
  };
  walk(document);
  return out;
}
"""


def main() -> int:
    from playwright.sync_api import sync_playwright

    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="/out")
    ap.add_argument("--only", default="")
    args = ap.parse_args()
    token = os.environ["HA_TOKEN"]
    tokens = {
        "access_token": token, "token_type": "Bearer", "expires_in": 315360000,
        "hassUrl": HA, "clientId": f"{HA}/", "expires": int(time.time() * 1000) + 315360000000,
        "refresh_token": "",
    }
    report = {}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for vname, (vp, dpr) in VIEWPORTS.items():
            ctx = browser.new_context(viewport=vp, device_scale_factor=dpr, locale="es-ES", timezone_id="Europe/Madrid", color_scheme="dark")
            ctx.add_init_script(
                f"window.localStorage.setItem('hassTokens', {json.dumps(json.dumps(tokens))});"
            )
            page = ctx.new_page()
            for dash in DASHBOARDS:
                if args.only and args.only not in dash:
                    continue
                page.goto(f"{HA}/{dash}", wait_until="networkidle", timeout=60000)
                page.wait_for_timeout(6000)  # cards + apexcharts animations
                name = f"{dash.split('/')[0]}-{vname}.png"
                page.screenshot(path=f"{args.out}/{name}", full_page=True)
                errs = page.evaluate(COUNT_ERRORS_JS)
                report[name] = errs
                print(f"{name}: {len(errs)} card errors {errs[:3]}", flush=True)
            ctx.close()
        browser.close()
    return 1 if any(report.values()) else 0


if __name__ == "__main__":
    sys.exit(main())
