import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api, ApiError, store, type EventCard, type Tenant } from "../api";
import Camera from "../components/Camera";

const MAX_SELFIES = 3;

export default function EventPage({ tenant }: { tenant: Tenant | null }) {
  const { slug = "" } = useParams();
  const nav = useNavigate();
  const [event, setEvent] = useState<EventCard | null>(null);
  const [missing, setMissing] = useState(false);
  const [token, setToken] = useState<string | null>(store.get(`access.${slug}`));
  const [code, setCode] = useState("");
  const [codeError, setCodeError] = useState<string | null>(null);
  const [consent, setConsent] = useState(false);
  const [shots, setShots] = useState<{ blob: Blob; url: string }[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => { api.event(slug).then(setEvent).catch(() => setMissing(true)); }, [slug]);
  useEffect(() => () => shots.forEach((s) => URL.revokeObjectURL(s.url)), []); // eslint-disable-line

  const needsCode = !!event?.requires_code && !token;
  const canSearch = shots.length > 0 && consent && !busy;
  const terms = useMemo(() => tenant?.terms_url, [tenant]);

  async function unlock(e: React.FormEvent) {
    e.preventDefault();
    setCodeError(null);
    try {
      const r = await api.access(slug, code);
      if (r.token) { store.set(`access.${slug}`, r.token); setToken(r.token); }
    } catch (err) {
      setCodeError(err instanceof ApiError ? err.message : "Não foi possível validar o código.");
    }
  }

  function add(blob: Blob) {
    setError(null);
    setShots((s) => [...s, { blob, url: URL.createObjectURL(blob) }].slice(0, MAX_SELFIES));
  }
  function remove(i: number) {
    setShots((s) => { URL.revokeObjectURL(s[i].url); return s.filter((_, j) => j !== i); });
  }

  async function submit() {
    setBusy(true); setError(null);
    try {
      const r = await api.search(slug, shots.map((s) => s.blob), tenant?.terms_version ?? "2026-10", token);
      shots.forEach((s) => URL.revokeObjectURL(s.url));
      nav(`/g/${r.gallery_token}`, { replace: true });
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) { store.set(`access.${slug}`, ""); setToken(null); }
      setError(err instanceof ApiError ? err.message : "Sem conexão. Verifique a internet e tente de novo.");
      setBusy(false);
    }
  }

  if (missing) return <p className="empty">Evento não encontrado ou encerrado.</p>;
  if (!event) return <div className="skeleton-list"><div className="skeleton" /></div>;

  return (
    <section className="panel">
      <h1>{event.name}</h1>
      {event.status === "indexing" && (
        <p className="note">As fotos ainda estão chegando. Se faltar alguma, busque de novo mais tarde.</p>
      )}

      {needsCode ? (
        <form onSubmit={unlock} className="stack">
          <p>Este evento pede um código de acesso. Ele foi enviado à sua delegação ou escola.</p>
          <label className="field">
            <span>Código do evento</span>
            <input value={code} onChange={(e) => setCode(e.target.value)} autoCapitalize="characters"
                   autoComplete="off" required maxLength={64} />
          </label>
          {codeError && <p className="error" role="alert">{codeError}</p>}
          <button className="btn btn-primary btn-lg">Continuar</button>
        </form>
      ) : (
        <div className="stack">
          <ol className="steps">
            <li className={shots.length ? "done" : "current"}>Selfie</li>
            <li className={shots.length && !consent ? "current" : consent ? "done" : ""}>Aceite</li>
            <li className={canSearch ? "current" : ""}>Buscar</li>
          </ol>

          {shots.length > 0 && (
            <div className="shots">
              {shots.map((s, i) => (
                <figure key={s.url}>
                  <img src={s.url} alt={`Selfie ${i + 1}`} />
                  <button className="chip" onClick={() => remove(i)} disabled={busy} aria-label={`Remover selfie ${i + 1}`}>×</button>
                </figure>
              ))}
            </div>
          )}

          {shots.length < MAX_SELFIES && (
            <Camera onCapture={add} disabled={busy} />
          )}
          {shots.length > 0 && shots.length < MAX_SELFIES && (
            <p className="muted center">Opcional: mais uma selfie (de lado ou sorrindo) melhora o resultado.</p>
          )}

          <label className="check">
            <input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} />
            <span>
              Concordo em usar minha selfie para localizar minhas fotos neste evento. Ela é processada na hora e
              <strong> não é armazenada</strong>.{" "}
              {terms && <a href={terms} target="_blank" rel="noreferrer">Ler termos</a>}
              {event.has_minors && <> Se você tem menos de 18 anos, peça autorização ao seu responsável.</>}
            </span>
          </label>

          {error && <p className="error" role="alert">{error}</p>}
          <button className="btn btn-primary btn-lg" onClick={submit} disabled={!canSearch}>
            {busy ? "Procurando você nas fotos…" : "Achar minhas fotos"}
          </button>
        </div>
      )}
    </section>
  );
}
