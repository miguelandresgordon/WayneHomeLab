#!/usr/bin/with-contenv bashio
# shellcheck shell=bash
set -euo pipefail

LOG_LEVEL="$(bashio::config 'log_level')"
export LOG_LEVEL
THRESHOLD="$(bashio::config 'threshold')"
export THRESHOLD
MARGIN="$(bashio::config 'margin')"
export MARGIN
MODEL_PATH="$(bashio::config 'model_path')"
export MODEL_PATH
PROFILES_PATH="$(bashio::config 'profiles_dir')/speaker_profiles.json"
export PROFILES_PATH
NUM_THREADS="$(bashio::config 'num_threads')"
export NUM_THREADS

bashio::log.info "Starting Speaker ID Mariano on port 10400"
bashio::log.info "Profiles: ${PROFILES_PATH}"
bashio::log.info "Model: ${MODEL_PATH}"
bashio::log.info "Threshold: ${THRESHOLD}, margin: ${MARGIN}"

exec python3 -m uvicorn app:app --host 0.0.0.0 --port 10400 --log-level "${LOG_LEVEL}"
