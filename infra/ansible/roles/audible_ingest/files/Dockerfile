FROM python:3.12-slim

# ffmpeg with -audible_key/-audible_iv decryption (Debian's ffmpeg has it).
RUN apt-get update \
 && apt-get install -y --no-install-recommends ffmpeg ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# audible-cli in an isolated venv so future Python upgrades don't break it.
# Config dir is pinned via the AUDIBLE_CONFIG_DIR env var (set in compose);
# audible-cli has no -c/--config-dir flag, only the env var, so plain
# symlink the entrypoint into /usr/local/bin.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
RUN uv venv /opt/audible-venv \
 && uv pip install --python /opt/audible-venv/bin/python --no-cache audible-cli \
 && mkdir -p /var/lib/audible-cli /var/lib/audible-ingest \
 && ln -sf /opt/audible-venv/bin/audible /usr/local/bin/audible

COPY audible-ingest /usr/local/bin/audible-ingest
RUN chmod +x /usr/local/bin/audible-ingest
