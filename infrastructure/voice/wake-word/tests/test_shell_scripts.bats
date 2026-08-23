#!/usr/bin/env bats
# Shell script behavior tests (TDD) for wake-word tooling.

setup() {
  REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../../../.." && pwd)"
  WAKE_WORD_DIR="$REPO_ROOT/infrastructure/voice/wake-word"
  export PATH="/opt/homebrew/bin:$PATH"
}

@test "copy_model_from_trainer fails gracefully without artifacts" {
  run env MWW_TRAINER_DIR=/nonexistent/trainer "$WAKE_WORD_DIR/copy_model_from_trainer.sh"
  [ "$status" -eq 1 ]
  [[ "$output" == *"No se encontraron artefactos"* ]]
}

@test "serve_model fails without mariano files" {
  run "$WAKE_WORD_DIR/serve_model.sh" "$WAKE_WORD_DIR/models"
  [ "$status" -eq 1 ]
  [[ "$output" == *"Faltan mariano.json"* ]]
}

@test "serve_model starts when mock artifacts exist" {
  TMPDIR="$(mktemp -d)"
  TEST_PORT=18765
  cp "$WAKE_WORD_DIR/models/mariano.json.example" "$TMPDIR/mariano.json"
  echo "mock-tflite-content" > "$TMPDIR/mariano.tflite"

  MWW_SERVE_PORT="$TEST_PORT" "$WAKE_WORD_DIR/serve_model.sh" "$TMPDIR" &
  SERVER_PID=$!
  sleep 2

  run curl -sf "http://127.0.0.1:${TEST_PORT}/mariano.json"
  kill "$SERVER_PID" 2>/dev/null || true
  wait "$SERVER_PID" 2>/dev/null || true

  [ "$status" -eq 0 ]
  [[ "$output" == *"mariano"* ]]
  rm -rf "$TMPDIR"
}

@test "flash_mariano_firmware fails without copied model" {
  run "$WAKE_WORD_DIR/flash_mariano_firmware.sh"
  if [[ -f "$WAKE_WORD_DIR/models/mariano.json" ]]; then
    skip "mariano.json already present"
  fi
  [ "$status" -eq 1 ]
  [[ "$output" == *"copy_model_from_trainer"* ]]
}

@test "setup_trainer script validates usage" {
  run "$WAKE_WORD_DIR/setup_trainer_macos.sh" invalid-arg
  [ "$status" -eq 1 ]
  [[ "$output" == *"Uso:"* ]]
}

@test "train_mariano_local prints help" {
  run "$WAKE_WORD_DIR/train_mariano_local.sh" --help
  [ "$status" -eq 0 ]
  [[ "$output" == *"MWW_MAX_SAMPLES"* ]]
  [[ "$output" == *"--foreground"* ]]
}

@test "free_trainer_disk reports DATA_DIR" {
  run env FREE_TRAINER_SKIP_BREW=1 "$WAKE_WORD_DIR/free_trainer_disk.sh"
  [ "$status" -eq 0 ]
  [[ "$output" == *"DATA_DIR="* ]]
  [[ "$output" == *"Espacio libre"* ]]
}

@test "free_trainer_disk help mentions keep-personal" {
  run "$WAKE_WORD_DIR/free_trainer_disk.sh" --help
  [ "$status" -eq 0 ]
  [[ "$output" == *"--keep-personal"* ]]
}

@test "setup_trainer_nvidia prints help" {
  run "$WAKE_WORD_DIR/setup_trainer_nvidia.sh" --help
  [ "$status" -eq 0 ]
  [[ "$output" == *"--dry-run"* ]]
  [[ "$output" == *"blackwell"* ]]
  [[ "$output" == *"--cpu"* ]]
}

@test "setup_trainer_nvidia dry-run includes gpus by default" {
  run "$WAKE_WORD_DIR/setup_trainer_nvidia.sh" --dry-run
  [ "$status" -eq 0 ]
  [[ "$output" == *"--gpus all"* ]]
}

@test "setup_trainer_nvidia cpu dry-run omits gpus" {
  run "$WAKE_WORD_DIR/setup_trainer_nvidia.sh" --cpu --dry-run
  [ "$status" -eq 0 ]
  [[ "$output" != *"--gpus all"* ]]
  [[ "$output" == *"CPU"* ]] || [[ "$output" == *"cpu"* ]]
}

@test "train_mariano_nvidia prints help" {
  run "$WAKE_WORD_DIR/train_mariano_nvidia.sh" --help
  [ "$status" -eq 0 ]
  [[ "$output" == *"mariano"* ]]
}

@test "setup_trainer_runpod prints help" {
  run "$WAKE_WORD_DIR/setup_trainer_runpod.sh" --help
  [ "$status" -eq 0 ]
  [[ "$output" == *"--dry-run"* ]]
  [[ "$output" == *"Spot"* ]] || [[ "$output" == *"spot"* ]]
}

@test "setup_trainer_runpod dry-run prints tater image and stop-after" {
  run "$WAKE_WORD_DIR/setup_trainer_runpod.sh" --dry-run
  [ "$status" -eq 0 ]
  [[ "$output" == *"ghcr.io/tatertotterson/microwakeword"* ]]
  [[ "$output" == *"/data"* ]]
  [[ "$output" == *"--stop-after"* ]]
  [[ "$output" == *"COMMUNITY"* ]] || [[ "$output" == *"Community"* ]]
  [[ "$output" != *"--spot"* ]]
}

@test "train_mariano_runpod prints help" {
  run "$WAKE_WORD_DIR/train_mariano_runpod.sh" --help
  [ "$status" -eq 0 ]
  [[ "$output" == *"mariano"* ]]
  [[ "$output" == *"personal_samples"* ]]
}

@test "teardown_runpod_trainer prints help" {
  run "$WAKE_WORD_DIR/teardown_runpod_trainer.sh" --help
  [ "$status" -eq 0 ]
  [[ "$output" == *"--dry-run"* ]]
  [[ "$output" == *"--delete-volume"* ]]
  [[ "$output" == *"--watch"* ]]
}

@test "teardown_runpod_trainer dry-run prints pod stop without volume delete" {
  run "$WAKE_WORD_DIR/teardown_runpod_trainer.sh" --dry-run
  [ "$status" -eq 0 ]
  [[ "$output" == *"pod stop"* ]]
  [[ "$output" != *"network-volume delete"* ]] || [[ "$output" == *"omit"* ]]
}

@test "pad_personal_samples copies wav with extra duration" {
  SRC="$(mktemp -d)"
  DEST="$(mktemp -d)"
  python3 - <<PY
import math, struct, wave
from pathlib import Path
path = Path("$SRC") / "clip.wav"
nframes = 1600
with wave.open(str(path), "wb") as wf:
    wf.setnchannels(1)
    wf.setsampwidth(2)
    wf.setframerate(16000)
    frames = b"".join(struct.pack("<h", int(8000 * math.sin(i / 10))) for i in range(nframes))
    wf.writeframes(frames)
PY
  run python3 "$WAKE_WORD_DIR/pad_personal_samples.py" "$SRC" "$DEST" --pad-ms 100
  [ "$status" -eq 0 ]
  [[ "$output" == *"padded_personal_wavs=1"* ]]
  run python3 - <<PY
import wave
from pathlib import Path
with wave.open(str(Path("$DEST") / "personal_000.wav"), "rb") as wf:
    duration_ms = 1000.0 * wf.getnframes() / wf.getframerate()
assert abs(duration_ms - 200.0) < 2.0, duration_ms
print("ok")
PY
  [ "$status" -eq 0 ]
  rm -rf "$SRC" "$DEST"
}

@test "flash_capture_firmware prints trainer URL guidance" {
  run "$WAKE_WORD_DIR/flash_capture_firmware.sh"
  [ "$status" -eq 0 ]
  [[ "$output" == *"Trainer App URL"* ]]
  [[ "$output" == *"Capture Wake Audio"* ]]
}
