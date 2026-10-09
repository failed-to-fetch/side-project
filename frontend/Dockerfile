# Build stage
FROM node:26-alpine AS build
WORKDIR /app

RUN npm install -g pnpm@12.10.1

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./

# lock the pnpm-lock.yml so that all dependencies are installed exactly as specified in the lockfile
RUN pnpm install --frozen-lockfile

# copys /frontend
COPY . .
RUN pnpm build

# Serve stage
FROM caddy:2.11-alpine
COPY Caddyfile /etc/caddy/Caddyfile
COPY --from=build /app/dist /srv

EXPOSE 80
