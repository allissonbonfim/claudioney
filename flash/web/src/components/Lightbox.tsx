import { useEffect } from "react";
import type { GalleryItem } from "../api";

type Props = {
  items: GalleryItem[]; index: number; onIndex: (i: number) => void; onClose: () => void;
  onFeedback: (item: GalleryItem, kind: "not_me" | "remove") => void;
};

export default function Lightbox({ items, index, onIndex, onClose, onFeedback }: Props) {
  const item = items[index];

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      if (e.key === "ArrowRight" && index < items.length - 1) onIndex(index + 1);
      if (e.key === "ArrowLeft" && index > 0) onIndex(index - 1);
    };
    window.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => { window.removeEventListener("keydown", onKey); document.body.style.overflow = ""; };
  }, [index, items.length, onClose, onIndex]);

  if (!item) return null;
  return (
    <div className="lightbox" role="dialog" aria-modal="true" aria-label="Foto ampliada">
      <button className="lb-close btn" onClick={onClose} aria-label="Fechar">×</button>
      <button className="lb-nav lb-prev" onClick={() => onIndex(index - 1)} disabled={index === 0} aria-label="Anterior">‹</button>
      <img src={item.preview} alt={item.name} />
      <button className="lb-nav lb-next" onClick={() => onIndex(index + 1)} disabled={index === items.length - 1} aria-label="Próxima">›</button>
      <div className="lb-bar">
        <span className="muted">{index + 1} / {items.length}</span>
        <a className="btn btn-primary" href={item.original} download={item.name}>Baixar original</a>
        <button className="btn" onClick={() => onFeedback(item, "not_me")}>Não sou eu</button>
        <button className="btn btn-danger" onClick={() => onFeedback(item, "remove")}>Pedir remoção</button>
      </div>
    </div>
  );
}
