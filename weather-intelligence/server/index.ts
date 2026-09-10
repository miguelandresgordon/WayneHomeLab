import { serve } from "@hono/node-server";
import { serveStatic } from "@hono/node-server/serve-static";
import { Hono } from "hono";
import { cors } from "hono/cors";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { config } from "./config.ts";
import { getDb } from "./db.ts";
import { startScheduler } from "./ingest.ts";
import { api } from "./routes.ts";

const here = path.dirname(fileURLToPath(import.meta.url));
const dist = path.resolve(here, "../web/dist");

const app = new Hono();

app.use(
  "/api/*",
  cors({
    origin: ["http://localhost:5173", "http://127.0.0.1:5173"],
    allowMethods: ["GET", "POST", "OPTIONS"],
    allowHeaders: ["Content-Type", "x-wic-token"],
  }),
);

app.route("/api", api);

if (config.isProd && fs.existsSync(dist)) {
  app.use(
    "/*",
    serveStatic({
      root: dist,
    }),
  );
  app.get("*", (c) => {
    const html = fs.readFileSync(path.join(dist, "index.html"), "utf8");
    return c.html(html);
  });
}

getDb();
startScheduler();

serve({ fetch: app.fetch, port: config.port, hostname: "0.0.0.0" }, (info) => {
  console.log(`WIC listening on http://0.0.0.0:${info.port}`);
});
