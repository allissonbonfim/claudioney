export type Brand = { primary?: string; accent?: string; tagline?: string; logo?: string };
export type Tenant = {
  slug: string; name: string; brand: Brand; texts: Record<string, string>;
  terms_url: string | null; terms_version: string;
};
export type EventCard = {
  slug: string; name: string; status: string; starts_on: string | null; ends_on: string | null;
  requires_code: boolean; has_minors: boolean; photos: number; description: string | null;
};
export type GalleryItem = {
  id: string; name: string; tier: string; taken_at: string | null;
  facets: Record<string, string>; width: number | null; height: number | null; thumb: string; preview: string; original: string;
};
export type Gallery = {
  event: { slug: string; name: string }; counts: { certain: number; maybe: number };
  tier: string; offset: number; items: GalleryItem[];
};

export class ApiError extends Error {
  constructor(public status: number, message: string, public reason?: string) {
    super(message);
  }
}

function safeStorage(kind: "local" | "session"): Storage | null {
  try { return kind === "local" ? window.localStorage : window.sessionStorage; } catch { return null; }
}

export function deviceId(): string {
  const s = safeStorage("local");
  let id = s?.getItem("flash.device");
  if (!id) {
    id = crypto.randomUUID().replace(/-/g, "");
    s?.setItem("flash.device", id);
  }
  return id;
}

export const store = {
  get: (k: string) => safeStorage("session")?.getItem(k) ?? null,
  set: (k: string, v: string) => safeStorage("session")?.setItem(k, v),
};

async function parse(res: Response) {
  if (res.ok) return res.json();
  let message = "Algo deu errado. Tente de novo.";
  let reason: string | undefined;
  try {
    const body = await res.json();
    const d = body.detail;
    if (typeof d === "string") message = d;
    else if (d && typeof d === "object" && !Array.isArray(d)) { message = d.message ?? message; reason = d.reason; }
  } catch { /* corpo vazio */ }
  throw new ApiError(res.status, message, reason);
}

export const api = {
  tenant: (): Promise<Tenant> => fetch("/v1/public/tenant").then(parse),
  events: (): Promise<EventCard[]> => fetch("/v1/public/events").then(parse),
  event: (slug: string): Promise<EventCard> => fetch(`/v1/public/events/${slug}`).then(parse),
  access: (slug: string, code: string): Promise<{ token: string | null }> =>
    fetch(`/v1/public/events/${slug}/access`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ code }),
    }).then(parse),
  search: (slug: string, selfies: Blob[], termsVersion: string, accessToken: string | null) => {
    const fd = new FormData();
    selfies.forEach((b, i) => fd.append("selfie", b, `selfie${i}.jpg`));
    fd.append("consent", "true");
    fd.append("terms_version", termsVersion);
    const headers: Record<string, string> = { "X-Device-Id": deviceId() };
    if (accessToken) headers.Authorization = `Bearer ${accessToken}`;
    return fetch(`/v1/public/events/${slug}/search`, { method: "POST", body: fd, headers }).then(parse) as
      Promise<{ search_id: string; counts: { certain: number; maybe: number }; gallery_token: string }>;
  },
  gallery: (token: string, tier: string, offset = 0, limit = 60): Promise<Gallery> =>
    fetch(`/v1/public/galleries/${token}?tier=${tier}&offset=${offset}&limit=${limit}`).then(parse),
  feedback: (token: string, photoId: string, kind: "not_me" | "remove") =>
    fetch(`/v1/public/galleries/${token}/photos/${photoId}/feedback`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ kind }),
    }).then(parse),
  zipUrl: (token: string, tier: string, ids?: string[]) =>
    `/v1/public/galleries/${token}/zip?tier=${tier}${ids?.length ? `&ids=${ids.join(",")}` : ""}`,
};

// ---- admin
const ADMIN_KEY = "flash.admin";
export const adminToken = {
  get: () => safeStorage("local")?.getItem(ADMIN_KEY) ?? "",
  set: (v: string) => safeStorage("local")?.setItem(ADMIN_KEY, v),
  clear: () => safeStorage("local")?.removeItem(ADMIN_KEY),
};
export async function admin<T = any>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Authorization", `Bearer ${adminToken.get()}`);
  if (init.body && !(init.body instanceof FormData)) headers.set("Content-Type", "application/json");
  return fetch(`/v1/admin${path}`, { ...init, headers }).then(parse);
}
