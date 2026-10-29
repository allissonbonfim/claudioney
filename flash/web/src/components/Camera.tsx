import { useEffect, useRef, useState } from "react";

const MAX_SIDE = 1024;

function toBlob(source: CanvasImageSource, w: number, h: number): Promise<Blob> {
  const scale = Math.min(1, MAX_SIDE / Math.max(w, h));
  const c = document.createElement("canvas");
  c.width = Math.round(w * scale);
  c.height = Math.round(h * scale);
  c.getContext("2d")!.drawImage(source, 0, 0, c.width, c.height);
  return new Promise((resolve, reject) =>
    c.toBlob((b) => (b ? resolve(b) : reject(new Error("falha ao gerar imagem"))), "image/jpeg", 0.9),
  );
}

async function fileToBlob(file: File): Promise<Blob> {
  const bmp = await createImageBitmap(file, { imageOrientation: "from-image" });
  try { return await toBlob(bmp, bmp.width, bmp.height); } finally { bmp.close(); }
}

/** Câmera frontal com guia oval; cai para o seletor de arquivos se não houver permissão. */
export default function Camera({ onCapture, disabled }: { onCapture: (b: Blob) => void; disabled?: boolean }) {
  const video = useRef<HTMLVideoElement>(null);
  const stream = useRef<MediaStream | null>(null);
  const [state, setState] = useState<"idle" | "starting" | "live" | "denied">("idle");

  const stop = () => { stream.current?.getTracks().forEach((t) => t.stop()); stream.current = null; };
  useEffect(() => stop, []);

  async function start() {
    if (!navigator.mediaDevices?.getUserMedia) { setState("denied"); return; }
    setState("starting");
    try {
      stream.current = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "user", width: { ideal: 1280 }, height: { ideal: 1280 } }, audio: false,
      });
      setState("live");
      requestAnimationFrame(() => {
        if (video.current) { video.current.srcObject = stream.current; void video.current.play(); }
      });
    } catch { setState("denied"); }
  }

  async function snap() {
    const v = video.current;
    if (!v || !v.videoWidth) return;
    // recorte quadrado central: o rosto fica grande e a imagem pequena
    const side = Math.min(v.videoWidth, v.videoHeight);
    const c = document.createElement("canvas");
    c.width = c.height = side;
    c.getContext("2d")!.drawImage(v, (v.videoWidth - side) / 2, (v.videoHeight - side) / 2, side, side, 0, 0, side, side);
    const blob = await toBlob(c, side, side);
    stop(); setState("idle"); onCapture(blob);
  }

  async function pick(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    e.target.value = "";
    if (f) onCapture(await fileToBlob(f));
  }

  return (
    <div className="camera">
      {state === "live" ? (
        <>
          <div className="viewfinder">
            <video ref={video} playsInline muted aria-label="Prévia da câmera" />
            <div className="oval" aria-hidden="true" />
          </div>
          <p className="muted center">Centralize o rosto no círculo, com boa luz e sem óculos escuros.</p>
          <div className="row">
            <button className="btn btn-primary btn-lg" onClick={snap} disabled={disabled}>Tirar selfie</button>
            <button className="btn" onClick={() => { stop(); setState("idle"); }}>Cancelar</button>
          </div>
        </>
      ) : (
        <div className="row stack-sm">
          <button className="btn btn-primary btn-lg" onClick={start} disabled={disabled || state === "starting"}>
            {state === "starting" ? "Abrindo câmera…" : "Abrir câmera"}
          </button>
          <label className={`btn ${disabled ? "disabled" : ""}`}>
            Enviar foto da galeria
            <input type="file" accept="image/*" capture="user" hidden onChange={pick} disabled={disabled} />
          </label>
          {state === "denied" && (
            <p className="note">Não consegui acessar a câmera. Libere a permissão no navegador ou envie uma foto.</p>
          )}
        </div>
      )}
    </div>
  );
}
