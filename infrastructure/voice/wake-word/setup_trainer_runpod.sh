#!/usr/bin/env bash
# setup_trainer_runpod.sh — Checklist para GPU Pod RunPod (imagen Tater NVIDIA)
#
# NO crea el pod (hace falta la API key / consola del usuario). Imprime el
# deploy on-demand: 1× RTX 4090 Community, volume /data, --stop-after, sin Spot.
# Instant Cluster no aplica: MicroWakeWord cabe en 1 GPU.
#
# Uso:
#   ./setup_trainer_runpod.sh
#   ./setup_trainer_runpod.sh --dry-run
#   ./setup_trainer_runpod.sh --blackwell   # solo si eliges RTX 5090 / sm_120
# macOS zsh: zsh ./setup_trainer_runpod.sh --dry-run

set -euo pipefail

_this="$0"
if [ -n "${BASH_VERSION:-}" ]; then
  _this="${BASH_SOURCE[0]}"
fi
SCRIPT_DIR="$(cd "$(dirname "$_this")" && pwd)"
IMAGE_LATEST="ghcr.io/tatertotterson/microwakeword:latest"
IMAGE_BLACKWELL="ghcr.io/tatertotterson/microwakeword:blackwell"
IMAGE="$IMAGE_LATEST"
GPU_TYPE="${MWW_RUNPOD_GPU:-NVIDIA GeForce RTX 4090}"
CLOUD="${MWW_RUNPOD_CLOUD:-COMMUNITY}"
STOP_AFTER="${MWW_RUNPOD_STOP_AFTER:-48h}"
VOLUME_GB="${MWW_RUNPOD_VOLUME_GB:-100}"
CONTAINER_DISK_GB="${MWW_RUNPOD_CONTAINER_DISK_GB:-50}"
POD_NAME="${MWW_RUNPOD_POD_NAME:-waynelab-mww-mariano}"
VOLUME_NAME="${MWW_RUNPOD_VOLUME_NAME:-waynelab-mww-data}"
MOUNT_PATH="/data"
REC_PORT="${REC_PORT:-8789}"
WAKE_WORD="${MWW_WAKE_WORD:-mariano}"
DRY_RUN=0
BLACKWELL=0

log() { printf '[setup-trainer-runpod] %s\n' "$*"; }
die() { log "ERROR: $*"; exit 1; }

usage() {
  cat <<EOF
Uso: $0 [--dry-run] [--blackwell] [--help]

Imprime el checklist y el comando runpodctl para un GPU Pod on-demand.
Este script no crea el pod: no envía la API key ni llama a RunPod.

  --dry-run     Igual que el default: solo imprime (nunca despliega)
  --blackwell   Imagen CUDA 12.8 para RTX 50-series (sm_120)
  --help        Esta ayuda

Nunca Spot (preemptible, SIGTERM a 5 s). Nunca Instant Cluster.
Techo de gasto: cartera prepago \$50–55, Auto-pay OFF, alerta \$10.
Kill switch: --stop-after ${STOP_AFTER} (conserva el network volume).

Variables:
  MWW_RUNPOD_GPU=$GPU_TYPE
  MWW_RUNPOD_CLOUD=$CLOUD
  MWW_RUNPOD_STOP_AFTER=$STOP_AFTER
  MWW_RUNPOD_VOLUME_GB=$VOLUME_GB
  MWW_RUNPOD_CONTAINER_DISK_GB=$CONTAINER_DISK_GB
  MWW_WAKE_WORD=$WAKE_WORD
  REC_PORT=$REC_PORT
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)    DRY_RUN=1; shift ;;
    --blackwell)  BLACKWELL=1; IMAGE="$IMAGE_BLACKWELL"; shift ;;
    -h|--help)    usage; exit 0 ;;
    *)            die "Argumento desconocido: $1 (usa --help)" ;;
  esac
done

if [[ "$BLACKWELL" -eq 1 ]]; then
  log "Imagen Blackwell (RTX 50-series): $IMAGE"
else
  log "Imagen CUDA estándar: $IMAGE"
fi

log "GPU Pod on-demand 1× $GPU_TYPE ($CLOUD). Volume ${VOLUME_GB}G → $MOUNT_PATH"
log "personal_samples y artefactos viven en ${MOUNT_PATH}/personal_samples y ${MOUNT_PATH}/trained_wake_words"
log "UI trainer HTTP :${REC_PORT}  wake word=${WAKE_WORD}  language=Spanish"

cat <<EOF

--- Checklist consola (https://www.console.runpod.io) ---
1. Billing: recarga un solo tramo \$50–55. Auto-pay OFF. Low balance alert \$10.
2. Network volume ${VOLUME_GB} GB, nombre ${VOLUME_NAME}, mismo datacenter que el GPU (p.ej. EU-RO-1).
3. Deploy Pod → On-demand (nunca Spot) → Community Cloud (${CLOUD}).
   GPU: ${GPU_TYPE} (fallback: RTX A4000 / A5000 / 3090 si no hay stock).
   Template custom / imagen: ${IMAGE}
   Container disk: ${CONTAINER_DISK_GB} GB
   Network volume montado en ${MOUNT_PATH}  (contrato Tater; no solo /workspace)
   HTTP ports: ${REC_PORT}/http
   TCP ports: 22/tcp (SSH opcional; la imagen Tater no trae /start.sh de RunPod)
4. No Instant Cluster: MicroWakeWord no escala a multi-nodo.
5. Al terminar: Stop el pod, runpodctl receive de ${WAKE_WORD}.{tflite,json}, borra el volume.

--- runpodctl (pega el volume ID real) ---
runpodctl pod create \\
  --name ${POD_NAME} \\
  --gpu-type "${GPU_TYPE}" \\
  --image ${IMAGE} \\
  --container-disk ${CONTAINER_DISK_GB} \\
  --volume-mount-path ${MOUNT_PATH} \\
  --network-volume-id VOLUME_ID \\
  --ports ${REC_PORT}/http,22/tcp \\
  --stop-after ${STOP_AFTER} \\
  --cloud ${CLOUD}

SSH custom (si Web Terminal no arranca; ver docs RunPod use-ssh):
  instalar openssh-server, inyectar \$PUBLIC_KEY, service ssh start, luego el trainer.

Siguiente: $SCRIPT_DIR/train_mariano_runpod.sh --dry-run
EOF

if [[ "$DRY_RUN" -eq 1 ]]; then
  log "dry-run: no se ha creado el pod (hace falta API key / consola del usuario)"
else
  log "Este script no crea el pod. Usa --dry-run o pega el comando runpodctl tras autenticarte."
fi
