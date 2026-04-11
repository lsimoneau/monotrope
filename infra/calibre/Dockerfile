FROM lscr.io/linuxserver/calibre-web:latest

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock mcp_server.py /app/mcp/
RUN cd /app/mcp && uv sync --frozen

# s6 service to run MCP server alongside calibre-web
RUN mkdir -p /etc/s6-overlay/s6-rc.d/mcp-server/dependencies.d && \
    echo "longrun" > /etc/s6-overlay/s6-rc.d/mcp-server/type && \
    touch /etc/s6-overlay/s6-rc.d/mcp-server/dependencies.d/init-services && \
    touch /etc/s6-overlay/s6-rc.d/user/contents.d/mcp-server

COPY mcp-server-run /etc/s6-overlay/s6-rc.d/mcp-server/run

EXPOSE 8000
