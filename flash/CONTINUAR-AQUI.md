# Continuar aqui — FLASH!

Passagem de bastão do Mac para o PC de casa, 29/10/2026. Este arquivo resume tudo o que foi conversado e decidido até agora. Leia junto com `CLAUDE.md`.

---

## 1. Como começar no PC (15 minutos)

### Pré-requisitos
- **Python 3.12 ou mais novo** (Windows: python.org, marque "Add Python to PATH").
- **Node.js 22 ou mais novo** (nodejs.org, versão LTS).
- Internet para baixar dependências e os modelos (~39 MB).

### Windows (PowerShell, dentro da pasta `flash`)
```powershell
python -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\pip install -e ".[dev]"
.venv\Scripts\python scripts\fetch_models.py
cd web; npm install; npm run build; cd ..
copy .env.example .env
.venv\Scripts\python -m pytest -q
```

### Linux / macOS
```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/python scripts/fetch_models.py
(cd web && npm install && npm run build)
cp .env.example .env
.venv/bin/python -m pytest -q
```

Os testes devem terminar com **23 passed**. Depois:

```powershell
.venv\Scripts\flash seed --slug cbde --name "CBDE"
.venv\Scripts\flash event teste --name "Teste com fotos reais" --source local --ref "C:\caminho\da\pasta\de\fotos"
.venv\Scripts\flash scan teste
.venv\Scripts\flash worker --once
.venv\Scripts\flash serve
```
Abra http://127.0.0.1:8000 (participante) e http://127.0.0.1:8000/admin (painel; token `dev-admin` em desenvolvimento).

Demonstração sem fotos reais (motor falso, quadrados coloridos no lugar de rostos): no `.env`, `FLASH_ENGINE=fake`, `FLASH_DATA_DIR=data/demo`, `FLASH_DATABASE_URL=sqlite:///data/demo/flash.db`, depois `python scripts/make_demo.py`.

### Primeiro pedido sugerido para o Claude no PC
> "Leia CLAUDE.md e CONTINUAR-AQUI.md. Prepare o ambiente (venv, dependências, modelos, build do site), rode os testes e depois indexe a pasta de fotos reais que eu indicar para medirmos o reconhecimento."

---

## 2. A ideia (resumo)

Nos eventos da CBDE saem milhares de fotos. Só um *select* vai para as redes; o resto demora e, no Drive, o estudante-atleta não acha as fotos dele. O FLASH!:
1. lê a pasta do evento no Google Drive e indexa os rostos;
2. o participante abre o site, escolhe o evento, tira uma selfie e recebe as fotos em que aparece (galeria, download, ZIP);
3. **Fase 2:** o mesmo pelo Direct do Instagram ("Quero minha foto" → evento → selfie → checa se segue o perfil → entrega).

Decisões de produto já tomadas (detalhes em `docs/`):
- Buscar **antes** do *follow gate* e mostrar "achei N fotos" como incentivo (Fase 2).
- No Direct: 20 melhores fotos + link da galeria (a API aceita 10 imagens por mensagem, 8 MB cada).
- Modo para eventos com menores: código do evento, limite de buscas por dia, selfie nunca armazenada.

---

## 3. Decisões do Allisson nesta conversa

| Data | Decisão |
|------|---------|
| 22/10 | Começar **só pelo site**, sem Instagram, mas com modelo escalável que receba o Instagram depois. |
| 22/10 | Armazenamento no **Google Drive** (tem 2 TB livres). |
| 22/10 | Direito de imagem já é coberto pelo advogado da CBDE; a busca é só da própria pessoa, por isso a selfie. *(Observação do Claude: a selfie é dado biométrico — vale o advogado revisar o texto curto de aceite que o site já mostra.)* |
| 22/10 | Vai disponibilizar uma **pasta no Drive** para eu distribuir o que for preciso — **link ainda não enviado**. |
| 23/10 | Pediu um plano/serviço que rode Python (o HostGator compartilhado não roda). |
| 29/10 | Avaliar rodar no **PC desktop de casa** → resposta: sim para piloto e indexação; VPS quando houver evento público pago. |

---

## 4. O que existe (estado em 29/10/2026)

**Pronto e testado (23 testes, com motor falso):**
- Ingestão: pasta local e Google Drive (conta de serviço), subpastas viram filtros (`Sábado/Vôlei`), pastas `_nao_publicar`/`_privado` ignoradas, reindexação sem duplicar, arquivo substituído detectado, foto corrompida não derruba o resto, orientação EXIF.
- Motor facial OpenCV YuNet + SFace (licença Apache 2.0) atrás da interface `FaceEngine`.
- Busca exata em memória por evento, faixas "Com você" / "Talvez seja você", limite diário, código do evento contra força bruta.
- Site (Vite + React): eventos, selfie pela câmera ou galeria (até 3), aceite, galeria em mosaico, foto ampliada, baixar original, ZIP de todas ou das selecionadas, "Não sou eu", "Pedir remoção" (oculta na hora).
- Painel `/admin`: criar evento, progresso da indexação, abrir/encerrar, métricas, ocultar fotos.
- Multi-cliente (`tenant_id` em tudo), trava que impede subir em produção com segredos de desenvolvimento.
- Verificado no navegador do Mac: busca, galeria no celular, foto ampliada, download e ZIP, painel.

**Ainda NÃO validado:**
- Reconhecimento com **fotos reais** (a precisão do SFace em esporte é desconhecida) — **próximo passo nº 1**.
- Google Drive com a conta de serviço real (só testado com respostas simuladas).
- PostgreSQL, `Dockerfile` e `infra/docker-compose.yml` (escritos, nunca executados).
- Migrações (Alembic) — hoje as tabelas são criadas direto (`create_all`).

---

## 5. Hospedagem (resumo de `docs/13-hospedagem.md`)

- HostGator compartilhado (`bomefim.com.br`): **não roda Python**. Tentativa de FTP em 22/10 falhou (o nome `ftp.bomefim.com.br` não resolveu a partir do Mac). Nada foi enviado.
- **Piloto:** PC de casa + Cloudflare Tunnel (gratuito, sem abrir portas no roteador).
- **Produção:** VPS no Brasil com root — 1ª opção HostGator VPS (Oracle Cloud no Brasil; planos exatos não confirmados), alternativas Hostinger KVM (confirmar São Paulo no checkout) e Fly.io (região São Paulo). Render e Hetzner descartados (sem Brasil).
- No PC de casa o gargalo é o **upload** da internet (ZIPs grandes). Checklist do dia do evento em `docs/13-hospedagem.md`, seção 7.

---

## 6. Próximos passos (em ordem)

1. **Instalar no PC** (seção 1) e rodar os testes.
2. **Testar com ~50–200 fotos reais** de um evento da CBDE (pasta local) e fazer selfies de 3–5 pessoas que aparecem nelas. Anotar: acertos, fotos perdidas, fotos erradas, tempo de indexação. Ajustar os limiares (`certain`/`maybe` em `event.config.thresholds`; padrão SFace 0,50/0,38 — **chute inicial, não calibrado**).
3. **Golden set** (Spike S1, `docs/04`): 30–50 pessoas rotuladas em ~1.500 fotos → decidir se SFace basta ou se precisa de outro motor.
4. **Conectar o Drive real:** criar conta de serviço no Google Cloud, ativar a Drive API, baixar o JSON, compartilhar a pasta do evento com o e-mail da conta (Leitor), `FLASH_GOOGLE_CREDENTIALS_FILE=...` no `.env`.
5. **Publicar o piloto** com Cloudflare Tunnel apontando um subdomínio.
6. Definir hospedagem de produção (VPS) e PostgreSQL + Alembic.
7. **Fase 2 – Instagram:** abrir o app na Meta e iniciar a Business Verification cedo (aprovação leva semanas).

Pendências que só o Allisson resolve: fotos reais para teste, JSON da conta de serviço, link da pasta do Drive, texto de aceite revisado pelo advogado, pesquisa do nome "FLASH!" no INPI, contas da Meta.

---

## 7. O que NÃO veio no pacote (e como recriar)

| Item | Por quê | Como recriar |
|------|---------|--------------|
| `.venv/`, `web/node_modules/` | específicos do sistema | seção 1 |
| `models/*.onnx` | baixados da internet | `scripts/fetch_models.py` (confere SHA-256 em `models/SHA256SUMS`) |
| `data/` (banco e miniaturas de demonstração) | regeneráveis, sintéticos | `scripts/make_demo.py` |
| `.env` | segredos | copie de `.env.example` |
| Memória do Claude do Mac | fica em `~/.claude` do Mac | o essencial está neste arquivo e no `CLAUDE.md` |

Credenciais de FTP da HostGator (usadas por outro projeto, o dashboard do YouTube) **não** foram incluídas.

---

## 8. Mapa rápido do código

```text
src/flash/
  config.py        configurações (.env com prefixo FLASH_)
  db.py            modelos: Tenant, Event, Photo, Face, Job, Search, SearchResult, ConsentLog, Feedback
  imaging.py       decodificação segura, derivados, hash perceptual
  faces/           FaceEngine (sface, fake) + validação da selfie
  sources/         SourceConnector: local e Google Drive
  storage/         miniaturas e prévias regeneráveis
  ingest/          fila em tabela, scan, pipeline, worker
  index/vector.py  busca vetorial exata em memória (NumpyIndex)
  search/service.py  selfie → fotos (independe do canal)
  channels/base.py contrato dos canais (web hoje; Instagram depois)
  api/             rotas públicas (/v1/public) e admin (/v1/admin)
  cli.py           comando `flash` (seed, event, scan, worker, progress, serve)
web/src/           site: Home, Event (selfie), Gallery, Admin
tests/             pytest com motor falso
docs/              manual completo (00 a 13) e ADRs
```
