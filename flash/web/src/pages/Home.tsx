import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, type EventCard, type Tenant } from "../api";

function dates(e: EventCard) {
  const fmt = (d: string) => new Date(d + "T12:00:00").toLocaleDateString("pt-BR", { day: "2-digit", month: "short" });
  if (e.starts_on && e.ends_on && e.starts_on !== e.ends_on) return `${fmt(e.starts_on)} – ${fmt(e.ends_on)}`;
  return e.starts_on ? fmt(e.starts_on) : null;
}

export default function Home({ tenant, failed }: { tenant: Tenant | null; failed: boolean }) {
  const [events, setEvents] = useState<EventCard[] | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => { api.events().then(setEvents).catch(() => setError(true)); }, []);

  if (failed || error) return <p className="empty">Não foi possível carregar agora. Tente novamente em instantes.</p>;

  return (
    <>
      <section className="hero">
        <h1>{tenant?.brand.tagline ?? "Ache suas fotos em segundos"}</h1>
        <p>Escolha o evento, tire uma selfie e receba todas as fotos em que você aparece.</p>
      </section>
      {events === null && <div className="skeleton-list"><div className="skeleton" /><div className="skeleton" /></div>}
      {events?.length === 0 && <p className="empty">Nenhum evento aberto no momento.</p>}
      <ul className="cards">
        {events?.map((e) => (
          <li key={e.slug}>
            <Link to={`/e/${e.slug}`} className="card">
              <div className="card-body">
                <h2>{e.name}</h2>
                <p className="muted">
                  {[dates(e), e.photos ? `${e.photos.toLocaleString("pt-BR")} fotos` : null].filter(Boolean).join(" · ")}
                </p>
                {e.status === "indexing" && <span className="badge">Ainda recebendo fotos</span>}
              </div>
              <span className="btn btn-primary">Achar minhas fotos</span>
            </Link>
          </li>
        ))}
      </ul>
    </>
  );
}
