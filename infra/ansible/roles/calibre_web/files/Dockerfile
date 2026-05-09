FROM crocodilestick/calibre-web-automated:latest

# Patch CWA's cwa-ingest-service to drop privileges before invoking the
# python workers. Upstream wraps only `inotifywait` with `s6-setuidgid abc`;
# the pipe consumer (and therefore `calibredb add` + the post-import
# `chown -R abc:abc /calibre-library`) runs as root, which blows up on
# root_squash NFS exports with EPERM. On non-NFS setups the same bug lands
# imported books as root:root, breaking subsequent web-UI deletes.
# Same fix as crocodilestick/Calibre-Web-Automated#1290 (open as of
# 2026-05-09); drop this patch once that lands.
RUN sed -i \
      -e 's|^\(\s*\)timeout \$safety_timeout python3 /app/calibre-web-automated/scripts/ingest_processor\.py|\1s6-setuidgid abc timeout $safety_timeout python3 /app/calibre-web-automated/scripts/ingest_processor.py|' \
      -e 's|^\(\s*\)python3 /app/calibre-web-automated/scripts/watch_fallback\.py|\1s6-setuidgid abc python3 /app/calibre-web-automated/scripts/watch_fallback.py|' \
      /etc/s6-overlay/s6-rc.d/cwa-ingest-service/run \
 && grep -c 's6-setuidgid abc' /etc/s6-overlay/s6-rc.d/cwa-ingest-service/run | grep -qx 4

# kobodl for ad-hoc Kobo download access. Isolated venv to avoid colliding
# with calibre-web's Python env. The wrapper at /usr/local/bin/kobodl pins
# the config path to where compose mounts the kobodl_config volume — kobodl's
# default search path is ~/.config/kobodl.json (file directly in .config/),
# which doesn't compose well with a mounted directory volume.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
RUN uv venv /opt/kobodl-venv \
 && uv pip install --python /opt/kobodl-venv/bin/python --no-cache kobodl \
 && mkdir -p /var/lib/kobodl \
 && printf '#!/bin/sh\nexec /opt/kobodl-venv/bin/kobodl --config /var/lib/kobodl/kobodl.json "$@"\n' \
      > /usr/local/bin/kobodl \
 && chmod +x /usr/local/bin/kobodl

# State directory for the kobo-ingest cron — owned by `abc` (the linuxserver
# user, PUID/PGID-remapped to the compose values at runtime).
RUN mkdir -p /var/lib/kobo-ingest \
 && chown abc:abc /var/lib/kobo-ingest
COPY kobo-ingest /usr/local/bin/kobo-ingest
RUN chmod +x /usr/local/bin/kobo-ingest
