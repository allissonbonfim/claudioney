import { useEffect, useState } from "react";
import { Link, Route, Routes } from "react-router-dom";
import { api, type Tenant } from "./api";
import { applyBrand } from "./brand";
import Admin from "./pages/Admin";
import EventPage from "./pages/Event";
import Gallery from "./pages/Gallery";
import Home from "./pages/Home";

export function Bolt({ size = 22 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" aria-hidden="true">
      <path d="M36 8 16 36h13l-4 20 23-31H34z" fill="currentColor" />
    </svg>
  );
}

export default function App() {
  const [tenant, setTenant] = useState<Tenant | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    api.tenant().then((t) => { setTenant(t); applyBrand(t.brand, t.name); }).catch(() => setFailed(true));
  }, []);

  return (
    <div className="app">
      <header className="topbar">
        <Link to="/" className="brand" aria-label="Início">
          <span className="brand-mark"><Bolt /></span>
          <span className="brand-name">{tenant?.name ?? "FLASH!"}</span>
        </Link>
        <span className="powered">FLASH!</span>
      </header>
      <main className="main">
        <Routes>
          <Route path="/" element={<Home tenant={tenant} failed={failed} />} />
          <Route path="/e/:slug" element={<EventPage tenant={tenant} />} />
          <Route path="/g/:token" element={<Gallery />} />
          <Route path="/admin/*" element={<Admin />} />
          <Route path="*" element={<p className="empty">Página não encontrada.</p>} />
        </Routes>
      </main>
      <footer className="foot">
        <span>Sua selfie é usada só para buscar e <strong>nunca é guardada</strong>.</span>
        {tenant?.terms_url && <a href={tenant.terms_url} target="_blank" rel="noreferrer">Termos e privacidade</a>}
      </footer>
    </div>
  );
}
