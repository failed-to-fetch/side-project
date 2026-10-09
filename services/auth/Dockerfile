FROM node:24-alpine
WORKDIR /app

RUN npm install -g pnpm@12.10.1

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile

COPY tsconfig.json ./
COPY src ./src

RUN pnpm run build

EXPOSE 3001
CMD ["pnpm", "run", "start"]
