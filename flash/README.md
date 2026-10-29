# FLASH!

Busca de fotos de eventos por selfie. Fotógrafos sobem no Google Drive; o participante manda uma selfie no site e recebe as fotos em que aparece. O bot do Instagram vem depois (o código já é "channel-ready").

Manual completo em [`docs/`](docs/00-LEIA-ME.md).

## Estado (22/10/2026)

| Pronto | Falta |
|--------|-------|
| Ingestão (pasta local e Google Drive), derivados, fila | Teste com **fotos reais** (precisa do golden set) |
| Motor YuNet + SFace (OpenCV, Apache 2.0) | Calibrar limiares e qualidade (`docs/04`) |
| Busca exata em memória, limiares, anti-abuso, modo menores | Teste do Drive com a conta de serviço real |
| Site: selfie, galeria, ZIP, pedido de remoção | Painel: editor de textos/tema, relatório |
| Painel admin básico | Alembic, PostgreSQL validado, deploy |
| 23 testes automatizados (motor falso) | Instagram (Fase 2) |

## Rodar localmente

```bash
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/python scripts/fetch_models.py        # baixa YuNet + SFace (~39 MB)
(cd web && npm install && npm run build)

.venv/bin/flash seed --slug cbde --name "CBDE"
.venv/bin/flash event jebs-2026 --name "JEBs 2026" --source local --ref ~/Fotos/jebs
.venv/bin/flash scan jebs-2026
.venv/bin/flash worker --once                   # indexa tudo e sai
.venv/bin/flash serve                           # http://127.0.0.1:8000  (painel em /admin)
```

Variáveis: copie `.env.example` para `.env`. Em desenvolvimento o token do painel é `dev-admin`.

Demonstração sem fotos reais (motor falso, quadrados coloridos): `scripts/make_demo.py`.

## Google Drive

1. Crie uma conta de serviço no Google Cloud, ative a **Drive API** e baixe o JSON.
2. `FLASH_GOOGLE_CREDENTIALS_FILE=/caminho/conta.json`
3. Compartilhe a pasta do evento com o e-mail da conta de serviço (**Leitor**).
4. `flash event jebs-2026 --source drive --ref <ID da pasta>` e `flash scan jebs-2026`.

Subpastas viram facetas (`Sábado/Vôlei`); pastas que começam com `_nao_publicar` ou `_privado` nunca são indexadas.

## Testes

```bash
.venv/bin/python -m pytest -q          # motor falso: não precisa de fotos reais
.venv/bin/ruff check src tests scripts
cd web && npx tsc --noEmit
```

## Estrutura

```text
src/flash/
  faces/      FaceEngine (sface, fake) + validação de selfie
  sources/    Drive e pasta local (SourceConnector)
  storage/    derivados regeneráveis (DerivativeStore)
  ingest/     fila em tabela, scan, pipeline, worker
  index/      busca vetorial exata (NumpyIndex)
  search/     SearchService — independe do canal
  channels/   contrato dos canais (web hoje; Instagram depois)
  api/        rotas públicas e administrativas (FastAPI)
web/          site (Vite + React + TypeScript)
docs/         manual do produto e ADRs
```

## Inegociáveis

- A selfie nunca é gravada (disco, log, banco). Há teste para isso.
- Toda tabela de negócio tem `tenant_id`.
- Motor facial só pela interface `FaceEngine`; não usar modelos de licença não comercial em produção.
