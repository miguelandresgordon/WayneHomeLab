#!/usr/bin/env bash
# Guarantee the node name resolves to the LAN IP (never loopback) so pmxcfs can start.
# Installed as /usr/local/sbin/waynelab-ensure-hosts and run as ExecStartPre of
# pve-cluster (see systemd/pve-cluster-waynelab.conf). Idempotent and safe to run
# at any time: it only touches /etc/hosts when the name resolves wrongly.
set -euo pipefail

NODE_NAME="${NODE_NAME:-waynelab-core}"
BRIDGE="${BRIDGE:-vmbr0}"
FALLBACK_IP="${FALLBACK_IP:-192.168.1.100}"

log() { echo "[waynelab-ensure-hosts] $*"; }

detect_ip() {
    local ip
    ip="$(ip -4 -o addr show dev "${BRIDGE}" 2>/dev/null | awk '{sub(/\/.*/, "", $4); print $4; exit}')"
    echo "${ip:-${FALLBACK_IP}}"
}

resolves_to_lan() {
    local resolved
    resolved="$(getent hosts "${NODE_NAME}" | awk '{print $1; exit}')"
    [[ -n "${resolved}" && "${resolved}" != 127.* && "${resolved}" != "::1" ]]
}

write_hosts() {
    local host_ip="$1" tmp
    tmp="$(mktemp /etc/hosts.XXXXXX)"
    cat > "${tmp}" <<EOF
127.0.0.1 localhost
${host_ip} ${NODE_NAME}.local ${NODE_NAME}

::1 localhost ip6-localhost ip6-loopback
ff02::1 ip6-allnodes
ff02::2 ip6-allrouters
EOF
    chmod 0644 "${tmp}"
    mv -f "${tmp}" /etc/hosts
}

main() {
    if [[ "$(id -u)" -ne 0 ]]; then
        echo "Run as root" >&2
        exit 1
    fi
    if resolves_to_lan; then
        exit 0
    fi
    local host_ip
    host_ip="$(detect_ip)"
    log "${NODE_NAME} does not resolve to a LAN IP; rewriting /etc/hosts -> ${host_ip}"
    write_hosts "${host_ip}"
    resolves_to_lan || { log "ERROR: ${NODE_NAME} still unresolved"; exit 1; }
}

main "$@"
