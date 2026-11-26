#!/usr/bin/env bash
# ha_backup_config.sh — Timestamped backup of the HA YAML we deploy, before any
# live change. Lands in /share/wayne-backups/config-YYYYmmdd-HHMMSS.tar.gz on
# HAOS (secrets excluded). Prints the path; restore with --restore <path>.
#
#   ./ha_backup_config.sh                 # create backup
#   ./ha_backup_config.sh --dry-run       # show what would run
#   ./ha_backup_config.sh --restore /share/wayne-backups/config-....tar.gz
set -euo pipefail

HA_HOST="${HA_HOST:-192.168.1.110}"
HA_USER="${HA_USER:-root}"
BACKUP_DIR="/share/wayne-backups"
PATHS=(configuration.yaml includes custom_sentences packages themes dashboards esphome www/wayne)

log() { printf '[ha-backup] %s\n' "$*" >&2; }

backup_cmd() {
  local stamp="$1"
  # busybox tar (HAOS SSH add-on): no --ignore-failed-read, so keep existing paths only.
  # shellcheck disable=SC2016 # $p/$P expand on the remote side on purpose
  printf 'mkdir -p %s && cd /config && P=""; for p in %s; do [ -e "$p" ] && P="$P $p"; done; tar czf %s/config-%s.tar.gz --exclude=secrets.yaml --exclude=esphome/secrets.yaml --exclude=esphome/.esphome $P && ls -l %s/config-%s.tar.gz' \
    "$BACKUP_DIR" "${PATHS[*]}" "$BACKUP_DIR" "$stamp" "$BACKUP_DIR" "$stamp"
}

main() {
  local mode="backup" target=""
  case "${1:-}" in
    --dry-run) mode="dry" ;;
    --restore) mode="restore"; target="${2:?path required}" ;;
    "") ;;
    *) log "unknown option: $1"; exit 2 ;;
  esac

  local stamp
  stamp="$(date +%Y%m%d-%H%M%S)"
  case "$mode" in
    dry)
      printf '%s\n' "$(backup_cmd "$stamp")"
      ;;
    backup)
      ssh -o BatchMode=yes "${HA_USER}@${HA_HOST}" "$(backup_cmd "$stamp")" >&2
      printf '%s/config-%s.tar.gz\n' "$BACKUP_DIR" "$stamp"
      ;;
    restore)
      [[ "$target" == "$BACKUP_DIR"/config-*.tar.gz ]] || { log "refusing: $target is not a wayne backup"; exit 2; }
      ssh -o BatchMode=yes "${HA_USER}@${HA_HOST}" "cd /config && tar xzf '$target' && ha core check"
      log "restored $target (restart/reload what you changed)"
      ;;
  esac
}

main "$@"
