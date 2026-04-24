FROM node:22-slim

RUN npm install -g obsidian-headless@0.0.8

RUN groupadd -g 10000 obsidian && \
    useradd -u 10000 -g 10000 -d /home/obsidian -m obsidian && \
    mkdir -p /config /vault && \
    chown -R 10000:10000 /config /vault /home/obsidian

COPY --chown=10000:10000 entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

USER 10000:10000
ENV XDG_CONFIG_HOME=/config
WORKDIR /vault
ENTRYPOINT ["/entrypoint.sh"]
