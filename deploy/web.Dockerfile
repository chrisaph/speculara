FROM node:24-bookworm-slim AS build
WORKDIR /srv
RUN npm install --global pnpm@10.34.3
COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY . .
# Empty API base means same-origin /api/*; no browser-side secret is built in.
ENV VITE_API_URL="" VITE_COLLECTOR_MODE=operator
RUN pnpm run build
FROM caddy:2-alpine
COPY --from=build /srv/dist /srv/www
COPY deploy/Caddyfile /etc/caddy/Caddyfile
