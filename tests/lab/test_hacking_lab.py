"""F7 hacking lab: isolation by construction (static checks of the compose)."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
LAB = REPO / "hacking-lab"


def _compose() -> dict:
    return yaml.safe_load((LAB / "docker-compose.yaml").read_text(encoding="utf-8"))


def _svc(name: str) -> dict:
    return _compose()["services"][name]


TARGETS = ("juice-shop", "dvwa", "dvwa-db", "webgoat")


def test_gluetun_official_image_pinned_with_mullvad_wireguard() -> None:
    g = _svc("gluetun")
    assert g["image"] == "qmcgaw/gluetun:v3.41.3"
    assert "NET_ADMIN" in g["cap_add"]
    assert any("/dev/net/tun" in d for d in g["devices"])
    env = g["environment"]
    assert env["VPN_SERVICE_PROVIDER"] == "mullvad"
    assert env["VPN_TYPE"] == "wireguard"
    assert "${WIREGUARD_PRIVATE_KEY" in env["WIREGUARD_PRIVATE_KEY"]


def test_tunnel_dns_not_pihole_nor_router() -> None:
    blob = (LAB / "docker-compose.yaml").read_text(encoding="utf-8")
    assert "192.168.1.53" not in blob and "192.168.1.1" not in blob
    env = _svc("gluetun")["environment"]
    assert env["DNS_ADDRESS"] == "10.64.0.1"  # Mullvad resolver, only reachable inside the tunnel
    assert str(env["DOT"]).lower() == "off"


def test_kali_and_tor_only_egress_through_gluetun() -> None:
    for name in ("kali", "tor"):
        s = _svc(name)
        assert s["network_mode"] == "service:gluetun", name
        assert "networks" not in s and "ports" not in s, name


def test_targets_live_on_internal_network_without_egress() -> None:
    c = _compose()
    assert c["networks"]["lab_internal"]["internal"] is True
    for t in TARGETS:
        s = c["services"][t]
        assert list(s["networks"]) == ["lab_internal"], t
        assert "ports" not in s, f"{t} must not be published on the LAN"
    assert "lab_internal" in c["services"]["gluetun"]["networks"]


def test_firewall_only_allows_the_lab_subnet_outside_the_tunnel() -> None:
    c = _compose()
    subnet = c["networks"]["lab_internal"]["ipam"]["config"][0]["subnet"]
    assert c["services"]["gluetun"]["environment"]["FIREWALL_OUTBOUND_SUBNETS"] == subnet


def test_all_images_pinned_and_limited() -> None:
    c = _compose()
    for name, s in c["services"].items():
        img = s.get("image") or s["build"]
        if "image" in s:
            assert ":latest" not in s["image"] and (":" in s["image"] or "@sha256:" in s["image"]), name
        lim = s["deploy"]["resources"]["limits"]
        assert "memory" in lim and "cpus" in lim, name
        assert img


def test_profiles_for_raspberry_pi_3() -> None:
    c = _compose()
    assert "full" in c["services"]["webgoat"]["profiles"]
    assert "tor" in c["services"]["tor"]["profiles"]
    rpi = (LAB / ".env.rpi3.example").read_text(encoding="utf-8")
    for key in ("KALI_MEM", "JUICE_MEM", "DVWA_MEM", "DB_MEM", "GLUETUN_MEM"):
        assert key in rpi


def test_kali_and_tor_dockerfiles_pin_base_by_digest_and_use_apt() -> None:
    k = (LAB / "kali" / "Dockerfile").read_text(encoding="utf-8")
    assert re.search(r"FROM kalilinux/kali-rolling@sha256:[0-9a-f]{64}", k)
    assert "apt-get install" in k
    t = (LAB / "tor" / "Dockerfile").read_text(encoding="utf-8")
    assert re.search(r"FROM debian:bookworm-slim@sha256:[0-9a-f]{64}", t)


def test_env_template_has_no_secrets() -> None:
    env = (LAB / ".env.example").read_text(encoding="utf-8")
    m = re.search(r"^WIREGUARD_PRIVATE_KEY=(.*)$", env, re.M)
    assert m and m.group(1).strip() == ""
    gi = (REPO / ".gitignore").read_text(encoding="utf-8")
    assert "hacking-lab/.env" in gi


def test_docs_state_the_rules() -> None:
    doc = (REPO / "docs" / "hacking-lab.md").read_text(encoding="utf-8").lower()
    for needle in ("solo objetivos propios", "legal", "deliberadamente vulnerables", "kill switch", "fuga de dns"):
        assert needle in doc, needle


def test_verify_script_checks_ip_dns_and_killswitch() -> None:
    sh = (LAB / "verify_lab.sh").read_text(encoding="utf-8")
    assert "set -euo pipefail" in sh
    for needle in ("am.i.mullvad.net", "whoami.akamai.net", "kill", "ip link set wg0 down"):
        assert needle in sh, needle
