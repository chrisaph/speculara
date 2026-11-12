FROM node:24-bookworm-slim AS node
FROM python:3.12-slim-bookworm AS runtime
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    SPECULARA_COLLECTOR_DATA_DIR=/data/socialmonitor \
    DISPLAY=:99
COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY --from=node /usr/local/lib/node_modules/npm /usr/local/lib/node_modules/npm
RUN ln -s /usr/local/lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
    && ln -s /usr/local/lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx
WORKDIR /srv
COPY backend/requirements.txt /srv/backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt
COPY integrations/socialmonitor/package*.json /srv/integrations/socialmonitor/
RUN cd integrations/socialmonitor \
    && npm ci --omit=dev \
    && npx playwright install --with-deps chromium
RUN apt-get update && apt-get install -y --no-install-recommends xvfb x11-utils x11vnc novnc websockify util-linux \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10001 speculara \
    && useradd --create-home --uid 10001 --gid 10001 speculara \
    && mkdir -p /data/socialmonitor \
    && chown -R speculara:speculara /data /ms-playwright
COPY backend/app /srv/backend/app
COPY integrations/socialmonitor /srv/integrations/socialmonitor
COPY deploy/entrypoint.sh /srv/entrypoint.sh
COPY deploy/collector-admin.py /srv/collector-admin.py
RUN sed -i 's/\r$//' /srv/entrypoint.sh
USER speculara
EXPOSE 8000 6080
ENTRYPOINT ["/bin/sh", "/srv/entrypoint.sh"]

FROM caddy:2-alpine AS gateway
FROM runtime AS render
USER root
COPY --from=gateway /usr/bin/caddy /usr/local/bin/caddy
COPY deploy/RenderCaddyfile /srv/RenderCaddyfile
COPY deploy/render-start.sh /srv/render-start.sh
RUN sed -i 's/\r$//' /srv/render-start.sh
ENV SPECULARA_RENDER_GATEWAY=1 SPECULARA_INTERNAL_API_PORT=8001
ENTRYPOINT ["/bin/sh", "/srv/render-start.sh"]
