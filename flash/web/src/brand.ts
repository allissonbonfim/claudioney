import type { Brand } from "./api";

export function applyBrand(brand: Brand, name: string) {
  const r = document.documentElement.style;
  if (brand.primary) r.setProperty("--primary", brand.primary);
  if (brand.accent) r.setProperty("--accent", brand.accent);
  document.title = `${name} · FLASH!`;
  document.querySelector('meta[name="theme-color"]')?.setAttribute("content", brand.primary ?? "#0b6b3a");
}
