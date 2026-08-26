#!/usr/bin/with-contenv bashio
# shellcheck shell=bash
set -euo pipefail

export LOG_LEVEL="$(bashio::config 'log_level')"
export THRESHOLD="$(bashio::config 'threshold')"
export MARGIN="$(bashio::config 'margin')"
export MODEL_PATH="$(bashio::config 'model_path')"
export PROFILES_PATH="$(bashio::config 'profiles_dir')/speaker_profiles.json"
export NUM_THREADS="$(bashio::config 'num_threads')"

bashio::log.info "Starting Speaker ID Mariano on port 10400"
bashio::log.info "Profiles: ${PROFILES_PATH}"
bashio::log.info "Model: ${MODEL_PATH}"
bashio::log.info "Threshold: ${THRESHOLD}, margin: ${MARGIN}"

exec python3 -m uvicorn app:app --host 0.0.0.0 --port 10400 --log-level "${LOG_LEVEL}"
