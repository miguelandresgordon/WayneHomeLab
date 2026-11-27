import type { CasaView, HomeAction, HomeView } from "../../server/types.ts";

async function asJson<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = (await res.json().catch(() => ({}))) as { error?: string };
    throw new Error(body.error || `HTTP ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export function fetchHome(): Promise<HomeView> {
  return fetch("/api/home").then((r) => asJson<HomeView>(r));
}

export function fetchCasa(): Promise<CasaView> {
  return fetch("/api/casa").then((r) => asJson<CasaView>(r));
}

export function postAction(action: HomeAction): Promise<{ ok: boolean }> {
  return fetch("/api/casa/actions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action }),
  }).then((r) => asJson<{ ok: boolean }>(r));
}

export function postBrightness(brightness: number): Promise<{ ok: boolean }> {
  return fetch("/api/casa/actions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ brightness }),
  }).then((r) => asJson<{ ok: boolean }>(r));
}
