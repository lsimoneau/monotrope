FROM python:3.12-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# librofm in an isolated uv venv — same pattern as audible-ingest, so
# future Python bumps don't break it. Deps: requests, pydantic,
# pydantic-settings.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
RUN uv venv /opt/libro-venv \
 && uv pip install --python /opt/libro-venv/bin/python --no-cache librofm \
 && mkdir -p /var/lib/libro-ingest

COPY libro-ingest /opt/libro-venv/bin/libro-ingest
RUN chmod +x /opt/libro-venv/bin/libro-ingest
