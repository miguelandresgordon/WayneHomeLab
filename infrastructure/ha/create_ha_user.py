#!/usr/bin/env python3
"""create_ha_user.py — Create a NON-admin Home Assistant user with a linked
person entity and a random temporary password.

The password is never printed or logged: it is written to --secret-file
(mode 0600, outside the repo) so it can be handed over once and deleted.

  ./create_ha_user.py --name Alicia --secret-file ~/.config/wayne/alicia_tmp_password

Idempotent: if a user with that name already exists it stops without changes.
Manual equivalent (if the API ever refuses): Ajustes -> Personas -> Añadir
persona -> «Permitir iniciar sesión» -> usuario `alicia`, sin «Administrador».
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import secrets
import string
import sys
from pathlib import Path

HA_WS = os.environ.get("HA_WS", "ws://192.168.1.110:8123/api/websocket")
ALPHABET = string.ascii_letters + string.digits + "-_.!?"


def generate_password(length: int = 24) -> str:
    while True:
        pw = "".join(secrets.choice(ALPHABET) for _ in range(length))
        if any(c.islower() for c in pw) and any(c.isupper() for c in pw) and any(c.isdigit() for c in pw):
            return pw


def user_payload(name: str) -> dict:
    # system-users = regular user (no admin). local_only False: VPN app access.
    return {"type": "config/auth/create", "name": name, "group_ids": ["system-users"], "local_only": False}


def credentials_payload(user_id: str, name: str, password: str) -> dict:
    return {"type": "config/auth_provider/homeassistant/create", "user_id": user_id, "username": name.lower(), "password": password}


def person_payload(name: str, user_id: str) -> dict:
    return {"type": "person/create", "name": name, "user_id": user_id}


def write_secret(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as fh:
        fh.write(value + "\n")
    os.chmod(path, 0o600)


def _token() -> str:
    tok = os.environ.get("HA_TOKEN", "").strip()
    p = Path.home() / ".config" / "wayne" / "ha_token"
    if not tok and p.is_file():
        tok = p.read_text().strip()
    if not tok:
        sys.exit("HA token missing")
    return tok


async def _run(name: str, secret_file: Path) -> int:
    import websockets

    async with websockets.connect(HA_WS) as ws:
        await ws.recv()
        await ws.send(json.dumps({"type": "auth", "access_token": _token()}))
        await ws.recv()
        n = 0

        async def call(msg: dict) -> dict:
            nonlocal n
            n += 1
            await ws.send(json.dumps({**msg, "id": n}))
            while True:
                r = json.loads(await ws.recv())
                if r.get("id") == n:
                    if not r.get("success"):
                        raise RuntimeError(f"{msg['type']}: {r.get('error')}")
                    return r["result"]

        users = await call({"type": "config/auth/list"})
        if any(u["name"].lower() == name.lower() for u in users):
            print(f"User {name!r} already exists — nothing to do")
            return 0

        password = generate_password()
        user = (await call(user_payload(name)))["user"]
        await call(credentials_payload(user["id"], name, password))
        write_secret(secret_file, password)
        person = await call(person_payload(name, user["id"]))
        print(f"Created user {name!r} (non-admin, id {user['id']}) and person {person.get('id')}; "
              f"temporary password in {secret_file} (0600)")
        return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--name", required=True)
    ap.add_argument("--secret-file", type=Path, required=True)
    args = ap.parse_args()
    return asyncio.run(_run(args.name, args.secret_file.expanduser()))


if __name__ == "__main__":
    raise SystemExit(main())
