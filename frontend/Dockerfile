# Build stage
FROM node:24-alpine AS build
WORKDIR /app

RUN npm install -g pnpm@12.10.1

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile

ARG VITE_AUTH_URL=http://localhost:3001
ENV VITE_AUTH_URL=$VITE_AUTH_URL

COPY . .
RUN pnpm build

# Serve stage
FROM caddy:2.11-alpine
COPY Caddyfile /etc/caddy/Caddyfile
COPY --from=build /app/dist /srv

EXPOSE 80
