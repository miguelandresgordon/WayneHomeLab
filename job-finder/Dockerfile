# syntax=docker/dockerfile:1
# linux/arm64 (Mac M3 local + RPi 5 host). Debian slim for glibc wheels.
FROM python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    JOB_FINDER_HOST=0.0.0.0 \
    JOB_FINDER_PORT=8473 \
    JOB_FINDER_DATABASE_URL=sqlite:////data/jobfinder.db \
    JOB_FINDER_RESUMES_DIR=/data/resumes

RUN groupadd --gid 1000 app \
    && useradd --uid 1000 --gid app --create-home --home-dir /home/app \
        --shell /usr/sbin/nologin app \
    && mkdir -p /data /app \
    && chown -R app:app /data /app

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY --chown=app:app app /app/app
COPY --chown=app:app alembic /app/alembic
COPY --chown=app:app alembic.ini /app/alembic.ini
COPY --chown=app:app docker-entrypoint.sh /app/docker-entrypoint.sh

RUN chmod 0755 /app/docker-entrypoint.sh

USER app
EXPOSE 8473

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8473/api/v1/health', timeout=3)"

ENTRYPOINT ["/app/docker-entrypoint.sh"]
