import { createServer } from "node:http";
import { toNodeHandler } from "better-auth/node";
import { auth } from "./auth.js";

const port = Number(process.env.PORT ?? 3001);

// No CORS handling: the browser reaches this service through the frontend's
// Caddy (or the Vite dev proxy) on the same origin as the app.
const server = createServer(toNodeHandler(auth));

server.listen(port, "0.0.0.0", () => {
    console.log(`Better Auth listening on port ${port}`);
});
