import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, ApiError, type Gallery as G, type GalleryItem } from "../api";
import Lightbox from "../components/Lightbox";

const PAGE = 60;

export default function Gallery() {
  const { token = "" } = useParams();
  const [tier, setTier] = useState<"certain" | "maybe">("certain");
  const [data, setData] = useState<G | null>(null);
  const [items, setItems] = useState<GalleryItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState<number | null>(null);
  const [selecting, setSelecting] = useState(false);
  const [picked, setPicked] = useState<Set<string>>(new Set());
  const [toast, setToast] = useState<string | null>(null);
  const [autoSwitched, setAutoSwitched] = useState(false);

  const load = useCallback(async (t: "certain" | "maybe", offset: number) => {
    setLoading(true);
    try {
      const g = await api.gallery(token, t, offset, PAGE);
      setData(g);
      setItems((prev) => (offset === 0 ? g.items : [...prev, ...g.items]));
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Não foi possível carregar a galeria.");
    } finally { setLoading(false); }
  }, [token]);

  useEffect(() => { setItems([]); void load(tier, 0); }, [tier, load]);

  // sem "certeza" mas com "talvez": mostra as parecidas em vez de uma tela vazia
  useEffect(() => {
    if (data && !autoSwitched && tier === "certain" && data.counts.certain === 0 && data.counts.maybe > 0) {
      setAutoSwitched(true); setTier("maybe");
    }
  }, [data, tier, autoSwitched]);

  useEffect(() => { if (toast) { const t = setTimeout(() => setToast(null), 3500); return () => clearTimeout(t); } }, [toast]);

  async function feedback(item: GalleryItem, kind: "not_me" | "remove") {
    if (kind === "remove" && !confirm("Ocultar esta foto para todos? A equipe vai revisar o pedido.")) return;
    try {
      await api.feedback(token, item.id, kind);
      setToast(kind === "remove" ? "Foto ocultada. Obrigado por avisar." : "Anotado, obrigado! Isso melhora a busca.");
      if (kind === "remove" || tier === "maybe") {
        setItems((p) => p.filter((i) => i.id !== item.id)); setOpen(null);
      }
    } catch { setToast("Não foi possível enviar agora."); }
  }

  function toggle(id: string) {
    setPicked((p) => { const n = new Set(p); n.has(id) ? n.delete(id) : n.add(id); return n; });
  }

  if (error && !data) {
    return (
      <div className="empty">
        <p>{error}</p>
        <Link className="btn btn-primary" to="/">Fazer nova busca</Link>
      </div>
    );
  }
  if (!data) return <div className="skeleton-grid">{Array.from({ length: 8 }, (_, i) => <div key={i} className="skeleton sq" />)}</div>;

  const total = data.counts.certain + data.counts.maybe;
  const shown = data.counts[tier];

  return (
    <section>
      <div className="gal-head">
        <div>
          <h1>{data.event.name}</h1>
          <p className="muted">
            {total === 0 ? "Nenhuma foto encontrada" : `${data.counts.certain} foto${data.counts.certain === 1 ? "" : "s"} com você`}
            {data.counts.maybe > 0 && ` · ${data.counts.maybe} parecidas`}
          </p>
        </div>
        {total > 0 && (
          <div className="row">
            <button className={`btn ${selecting ? "btn-active" : ""}`}
                    onClick={() => { setSelecting((s) => !s); setPicked(new Set()); }}>
              {selecting ? "Cancelar seleção" : "Selecionar"}
            </button>
            {selecting && picked.size > 0 ? (
              <a className="btn btn-primary" href={api.zipUrl(token, tier, [...picked])}>Baixar {picked.size} (ZIP)</a>
            ) : (
              <a className="btn btn-primary" href={api.zipUrl(token, tier)}>Baixar todas (ZIP)</a>
            )}
          </div>
        )}
      </div>

      {data.counts.maybe > 0 && data.counts.certain > 0 && (
        <div className="tabs" role="tablist">
          <button role="tab" aria-selected={tier === "certain"} className={tier === "certain" ? "on" : ""} onClick={() => setTier("certain")}>
            Com você ({data.counts.certain})
          </button>
          <button role="tab" aria-selected={tier === "maybe"} className={tier === "maybe" ? "on" : ""} onClick={() => setTier("maybe")}>
            Talvez seja você ({data.counts.maybe})
          </button>
        </div>
      )}
      {tier === "maybe" && <p className="note">Estas fotos têm rostos parecidos com o seu, mas sem certeza. Confira antes de baixar.</p>}

      {total === 0 ? (
        <div className="empty">
          <p><strong>Não encontramos você nas fotos ainda.</strong></p>
          <ul className="tips">
            <li>As fotos podem estar chegando — tente de novo mais tarde.</li>
            <li>Use uma selfie bem iluminada, de frente, sem óculos escuros ou boné.</li>
            <li>Envie 2 ou 3 selfies diferentes para melhorar a busca.</li>
          </ul>
          <Link className="btn btn-primary" to={`/e/${data.event.slug}`}>Tentar outra selfie</Link>
        </div>
      ) : (
        <>
          <ul className="grid">
            {items.map((it, i) => (
              <li key={it.id}>
                <button className={`tile ${picked.has(it.id) ? "picked" : ""}`}
                        style={{ aspectRatio: it.width && it.height ? `${it.width} / ${it.height}` : "3 / 2" }}
                        onClick={() => (selecting ? toggle(it.id) : setOpen(i))}
                        aria-label={selecting ? `Selecionar ${it.name}` : `Abrir ${it.name}`}
                        aria-pressed={selecting ? picked.has(it.id) : undefined}>
                  <img src={it.thumb} alt="" loading="lazy" decoding="async" />
                  {selecting && <span className="tick" aria-hidden="true">{picked.has(it.id) ? "✓" : ""}</span>}
                </button>
              </li>
            ))}
          </ul>
          {items.length < shown && (
            <div className="center">
              <button className="btn" disabled={loading} onClick={() => load(tier, items.length)}>
                {loading ? "Carregando…" : `Carregar mais (${shown - items.length})`}
              </button>
            </div>
          )}
          <p className="muted center small">Guarde o endereço desta página: ele abre suas fotos de novo por 30 dias.</p>
        </>
      )}

      {open !== null && (
        <Lightbox items={items} index={open} onIndex={setOpen} onClose={() => setOpen(null)} onFeedback={feedback} />
      )}
      {toast && <div className="toast" role="status">{toast}</div>}
    </section>
  );
}
