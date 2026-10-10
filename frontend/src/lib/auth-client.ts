import { createAuthClient } from "better-auth/client";

export const authClient = createAuthClient({
  // Set at build time (frontend/Dockerfile ARG, or frontend/.env for `pnpm dev`).
  baseURL: import.meta.env.VITE_AUTH_URL ?? "http://localhost:3001",
});
