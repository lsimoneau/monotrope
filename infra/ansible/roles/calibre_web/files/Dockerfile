FROM crocodilestick/calibre-web-automated:latest

# kobodl for ad-hoc Kobo download access. Isolated venv to avoid colliding
# with calibre-web's Python env. The wrapper at /usr/local/bin/kobodl pins
# the config path to where compose mounts the kobodl_config volume — kobodl's
# default search path is ~/.config/kobodl.json (file directly in .config/),
# which doesn't compose well with a mounted directory volume.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
RUN uv venv /opt/kobodl-venv \
 && uv pip install --python /opt/kobodl-venv/bin/python --no-cache kobodl \
 && printf '#!/bin/sh\nexec /opt/kobodl-venv/bin/kobodl --config /root/.config/kobodl/kobodl.json "$@"\n' \
      > /usr/local/bin/kobodl \
 && chmod +x /usr/local/bin/kobodl
