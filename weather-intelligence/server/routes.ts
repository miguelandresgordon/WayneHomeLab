import { Hono } from "hono";
import { config } from "./config.ts";
import { getDb, logAction } from "./db.ts";
import { isAllowedAction, runAction, setLampBrightness } from "./ha.ts";
import { ingestAll } from "./ingest.ts";
import { buildCasaView, buildContextPack, buildHomeView } from "./views.ts";

export const api = new Hono();

api.use("/*", async (c, next) => {
  await next();
  c.header("Cache-Control", "private, max-age=30, stale-while-revalidate=120");
});

api.get("/health", (c) => {
  getDb();
  const rssMb = Math.round(process.memoryUsage().rss / 1024 / 1024);
  c.header("Cache-Control", "no-store");
  return c.json({
    ok: true,
    demo: config.demo || !config.aemetKey,
    rssMb,
    db: config.dbPath,
  });
});

api.get("/home", async (c) => c.json(await buildHomeView()));
api.get("/casa", async (c) => {
  c.header("Cache-Control", "private, max-age=5");
  return c.json(await buildCasaView());
});
api.get("/context", async (c) => c.json(await buildContextPack()));

api.post("/casa/actions", async (c) => {
  c.header("Cache-Control", "no-store");
  const body = (await c.req.json().catch(() => ({}))) as {
    action?: string;
    brightness?: number;
  };
  if (typeof body.brightness === "number") {
    try {
      await setLampBrightness(body.brightness);
      logAction("light.brightness", true, String(body.brightness));
      return c.json({ ok: true, action: "light.brightness" });
    } catch (err) {
      const detail = err instanceof Error ? err.message : String(err);
      logAction("light.brightness", false, detail);
      return c.json({ ok: false, error: "HA_UNREACHABLE", detail }, 502);
    }
  }
  if (!body.action || !isAllowedAction(body.action)) {
    return c.json({ ok: false, error: "ACTION_DENIED" }, 403);
  }
  try {
    await runAction(body.action);
    logAction(body.action, true, "ok");
    return c.json({ ok: true, action: body.action });
  } catch (err) {
    const detail = err instanceof Error ? err.message : String(err);
    logAction(body.action, false, detail);
    return c.json({ ok: false, error: "HA_UNREACHABLE", detail }, 502);
  }
});

function ingestAllowed(c: { req: { header: (n: string) => string | undefined } }): boolean {
  const token = c.req.header("x-wic-token") || "";
  if (config.ingestToken) return token === config.ingestToken;
  const forwarded = c.req.header("x-forwarded-for") || "";
  const ip = forwarded.split(",")[0]?.trim() || "";
  return ip === "" || ip === "127.0.0.1" || ip === "::1";
}

api.post("/ingest", async (c) => {
  c.header("Cache-Control", "no-store");
  if (!ingestAllowed(c)) {
    return c.json({ ok: false, error: "ACTION_DENIED" }, 403);
  }
  const result = await ingestAll();
  return c.json(result, result.ok ? 200 : 502);
});
