# https://developers.home-assistant.io/docs/apps/configuration#app-dockerfile
# Supervisor 2026.04+ no longer injects BUILD_FROM — base image must be explicit.
# sherpa-onnx ships manylinux wheels (glibc) only — Alpine/musl fails to compile from source.
ARG BUILD_FROM=ghcr.io/home-assistant/aarch64-base-debian:bookworm
FROM ${BUILD_FROM}

LABEL \
  io.hass.version="1.0.0" \
  io.hass.type="app" \
  io.hass.arch="aarch64"

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_BREAK_SYSTEM_PACKAGES=1 \
    APP_DIR=/app

WORKDIR ${APP_DIR}

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ${APP_DIR}/
RUN pip3 install --no-cache-dir -r requirements.txt

COPY recognizer.py core.py app.py ${APP_DIR}/

COPY run.sh /
RUN chmod a+x /run.sh

CMD [ "/run.sh" ]
