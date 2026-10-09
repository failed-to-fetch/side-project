import { createServer } from "node:http";
import { toNodeHandler } from "better-auth/node";
import { auth } from "./auth.js";

const port = Number(process.env.PORT ?? 3001);

const allowedOrigins = new Set([
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]);

const authHandler = toNodeHandler(auth);

const server = createServer((req, res) => {
    const origin = req.headers.origin;


    if (origin && allowedOrigins.has(origin)) {
        res.setHeader("Access-Control-Allow-Origin", origin);
        res.setHeader("Access-Control-Allow-Credentials", "true");
        res.setHeader(
            "Access-Control-Allow-Methods",
            "GET, POST, PUT, PATCH, DELETE, OPTIONS"
        );
        res.setHeader(
            "Access-Control-Allow-Headers",
            "Content-Type, Authorization"
        );
        res.setHeader("Vary", "Origin");
    }

    if (req.method === "OPTIONS") {
        if (!origin || !allowedOrigins.has(origin)) {
            res.writeHead(403);
            res.end();
            return;
        }

        res.writeHead(204);
        res.end();
        return;
    }

    authHandler(req, res);

});

server.listen(port, "0.0.0.0", () => {
    console.log(`Better Auth listening on port ${port}`);
});
