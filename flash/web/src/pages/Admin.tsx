import { useCallback, useEffect, useState } from "react";
import { admin, adminToken, ApiError } from "../api";

type Ev = {
  id: string; slug: string; name: string; status: string; source_type: string; source_ref: string;
  has_minors: boolean; requires_code: boolean;
};
type Progress = { total: number; indexed: number; pending: number; error: number; faces: number };
type Photo = { id: string; name: string; status: string; error: string | null; visible: boolean; thumb: string };

function AdminImg({ src }: { src: string }) {
  const [url, setUrl] = useState<string>();
  useEffect(() => {
    let alive = true; let obj: string | undefined;
    fetch(`${src}`, { headers: { Authorization: `Bearer ${adminToken.get()}` } })
      .then((r) => (r.ok ? r.blob() : Promise.reject()))
      .then((b) => { if (alive) { obj = URL.createObjectURL(b); setUrl(obj); } })
      .catch(() => {});
    return () => { alive = false; if (obj) URL.revokeObjectURL(obj); };
  }, [src]);
  return url ? <img src={url} alt="" /> : <div className="skeleton sq" />;
}

function Login({ onOk }: { onOk: () => void }) {
  const [v, setV] = useState("");
  const [err, setErr] = useState("");
  async function go(e: React.FormEvent) {
    e.preventDefault(); adminToken.set(v);
    try { await admin("/tenants"); onOk(); } catch { adminToken.clear(); setErr("Token inválido."); }
  }
  return (
    <form className="panel stack" onSubmit={go}>
      <h1>Painel</h1>
      <label className="field"><span>Token de administrador</span>
        <input type="password" value={v} onChange={(e) => setV(e.target.value)} required autoComplete="off" /></label>
      {err && <p className="error">{err}</p>}
      <button className="btn btn-primary">Entrar</button>
    </form>
  );
}

function NewEvent({ onDone }: { onDone: () => void }) {
  const [f, setF] = useState({ name: "", slug: "", source_type: "drive", source_ref: "", code: "", minors: true });
  const [err, setErr] = useState("");
  const set = (k: string, v: string | boolean) => setF((p) => ({ ...p, [k]: v }));
  async function go(e: React.FormEvent) {
    e.preventDefault(); setErr("");
    try {
      await admin("/events", { method: "POST", body: JSON.stringify({
        tenant_slug: "cbde", slug: f.slug, name: f.name, source_type: f.source_type, source_ref: f.source_ref,
        has_minors: f.minors, access_code: f.code || null }) });
      onDone();
    } catch (x) { setErr(x instanceof ApiError ? x.message : "Erro ao criar."); }
  }
  return (
    <form className="panel stack" onSubmit={go}>
      <h2>Novo evento</h2>
      <label className="field"><span>Nome</span><input value={f.name} required onChange={(e) => {
        set("name", e.target.value);
        if (!f.slug) set("slug", e.target.value.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, ""));
      }} /></label>
      <label className="field"><span>Endereço (slug)</span><input value={f.slug} required pattern="[a-z0-9][a-z0-9\-]{1,78}" onChange={(e) => set("slug", e.target.value)} /></label>
      <label className="field"><span>Fonte das fotos</span>
        <select value={f.source_type} onChange={(e) => set("source_type", e.target.value)}>
          <option value="drive">Google Drive</option><option value="local">Pasta no servidor</option></select></label>
      <label className="field"><span>{f.source_type === "drive" ? "ID da pasta do Drive" : "Caminho da pasta"}</span>
        <input value={f.source_ref} required onChange={(e) => set("source_ref", e.target.value)} /></label>
      <label className="check"><input type="checkbox" checked={f.minors} onChange={(e) => set("minors", e.target.checked)} />
        <span>Evento com menores de idade (modo restrito)</span></label>
      <label className="field"><span>Código de acesso (opcional)</span><input value={f.code} onChange={(e) => set("code", e.target.value)} /></label>
      {err && <p className="error">{err}</p>}
      <button className="btn btn-primary">Criar evento</button>
    </form>
  );
}

function EventDetail({ id, onBack }: { id: string; onBack: () => void }) {
  const [ev, setEv] = useState<Ev | null>(null);
  const [prog, setProg] = useState<Progress | null>(null);
  const [metrics, setMetrics] = useState<any>(null);
  const [photos, setPhotos] = useState<Photo[]>([]);
  const [msg, setMsg] = useState("");

  const refresh = useCallback(async () => {
    const [e, p, m, ph] = await Promise.all([
      admin<Ev>(`/events/${id}`), admin<Progress>(`/events/${id}/progress`),
      admin(`/events/${id}/metrics`), admin<Photo[]>(`/events/${id}/photos?limit=60`),
    ]);
    setEv(e); setProg(p); setMetrics(m); setPhotos(ph);
  }, [id]);

  useEffect(() => { void refresh(); const t = setInterval(refresh, 4000); return () => clearInterval(t); }, [refresh]);

  async function act(fn: () => Promise<unknown>, ok: string) {
    try { await fn(); setMsg(ok); await refresh(); } catch (x) { setMsg(x instanceof ApiError ? x.message : "Erro."); }
  }
  if (!ev || !prog) return <p className="muted">Carregando…</p>;
  const pct = prog.total ? Math.round((prog.indexed / prog.total) * 100) : 0;
  const link = `${location.origin}/e/${ev.slug}`;

  return (
    <div className="stack">
      <button className="btn" onClick={onBack}>← Eventos</button>
      <h1>{ev.name} <span className="badge">{ev.status}</span></h1>
      <p className="muted">Link para o público: <a href={link}>{link}</a></p>

      <div className="panel stack">
        <h2>Indexação</h2>
        <div className="bar"><div style={{ width: `${pct}%` }} /></div>
        <p>{prog.indexed} de {prog.total} fotos ({pct}%) · {prog.faces} rostos · {prog.pending} na fila · {prog.error} com erro</p>
        <div className="row">
          <button className="btn btn-primary" onClick={() => act(async () => { const r = await admin(`/events/${id}/scan`, { method: "POST" }); setMsg(`${r.new} novas, ${r.unchanged} já indexadas`); }, "")}>Buscar fotos novas</button>
          {ev.status !== "open" && <button className="btn" onClick={() => act(() => admin(`/events/${id}`, { method: "PATCH", body: JSON.stringify({ status: "open" }) }), "Evento aberto ao público")}>Abrir ao público</button>}
          {ev.status === "open" && <button className="btn" onClick={() => act(() => admin(`/events/${id}`, { method: "PATCH", body: JSON.stringify({ status: "closed", retention_days: 90 }) }), "Evento encerrado")}>Encerrar</button>}
        </div>
        {msg && <p className="note" role="status">{msg}</p>}
      </div>

      {metrics && (
        <div className="panel">
          <h2>Uso</h2>
          <p>{metrics.searches} buscas · {metrics.with_results} com resultado
            {metrics.success_rate !== null && ` (${Math.round(metrics.success_rate * 100)}%)`} · {metrics.avg_latency_ms} ms médios</p>
          {Object.keys(metrics.feedback).length > 0 && <p className="muted">Avisos: {Object.entries(metrics.feedback).map(([k, v]) => `${k}: ${v}`).join(" · ")}</p>}
        </div>
      )}

      <div className="panel">
        <h2>Fotos recentes</h2>
        <ul className="grid admin-grid">
          {photos.map((p) => (
            <li key={p.id} className="tile static">
              <AdminImg src={p.thumb} />
              <div className="tile-foot">
                <small title={p.error ?? ""}>{p.status === "error" ? "erro" : p.name}</small>
                <button className="chip" onClick={() => act(() => admin(`/photos/${p.id}/hide`, { method: "POST" }), "Foto ocultada")}>ocultar</button>
              </div>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

export default function Admin() {
  const [auth, setAuth] = useState(!!adminToken.get());
  const [events, setEvents] = useState<Ev[]>([]);
  const [sel, setSel] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);

  const load = useCallback(async () => {
    try { setEvents(await admin<Ev[]>("/events")); } catch { adminToken.clear(); setAuth(false); }
  }, []);
  useEffect(() => { if (auth) void load(); }, [auth, load]);

  if (!auth) return <Login onOk={() => setAuth(true)} />;
  if (sel) return <EventDetail id={sel} onBack={() => { setSel(null); void load(); }} />;
  if (creating) return <NewEvent onDone={() => { setCreating(false); void load(); }} />;
  return (
    <div className="stack">
      <div className="gal-head"><h1>Eventos</h1>
        <div className="row"><button className="btn btn-primary" onClick={() => setCreating(true)}>Novo evento</button>
          <button className="btn" onClick={() => { adminToken.clear(); setAuth(false); }}>Sair</button></div></div>
      {events.length === 0 && <p className="empty">Nenhum evento ainda.</p>}
      <ul className="cards">
        {events.map((e) => (
          <li key={e.id}><button className="card as-button" onClick={() => setSel(e.id)}>
            <div className="card-body"><h2>{e.name}</h2>
              <p className="muted">{e.source_type === "drive" ? "Google Drive" : "Pasta local"} · {e.has_minors ? "com menores" : "adultos"}{e.requires_code ? " · com código" : ""}</p></div>
            <span className="badge">{e.status}</span></button></li>
        ))}
      </ul>
    </div>
  );
}
