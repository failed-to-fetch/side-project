import { createAuthClient } from "better-auth/client";

// No baseURL: the auth service is reached on this origin at /api/auth, through
// Caddy in Docker or the Vite dev proxy.
export const authClient = createAuthClient();
