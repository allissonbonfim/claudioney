# FLASH! — instruções para o Claude

Produto: busca de fotos de eventos por selfie. Fotógrafos sobem as fotos no Google Drive; o FLASH! indexa os rostos; o participante manda uma selfie no site e recebe todas as fotos em que aparece. O bot do Instagram (Direct + "follow gate") é a Fase 2 — o código já é "channel-ready".

- **Dono:** Allisson Bonfim (Bom&fim Fullscope, agência de comunicação). Fale sempre em **português do Brasil**.
- **Cliente-piloto:** CBDE (eventos escolares esportivos, como os JEBs). A maioria dos participantes é **menor de idade**.
- **Objetivo comercial:** vender para outros clientes (multi-cliente, white-label, baixo custo de operação).

Antes de mexer em algo, leia `CONTINUAR-AQUI.md` (estado e próximos passos) e o documento do tema em `docs/` (índice em `docs/00-LEIA-ME.md`).

## Inegociáveis
- A selfie **nunca** é gravada (disco, log, banco, fila). Só o vetor, em memória. Há teste para isso (`tests/test_search_api.py::test_selfie_is_never_persisted`).
- Toda tabela de negócio tem `tenant_id`. Query sem filtro de cliente é bug (há teste de isolamento).
- Motor facial só pela interface `FaceEngine` (`src/flash/faces/`). Nunca importar OpenCV/ONNX fora de `flash.faces` / `flash.imaging`.
- **Não usar InsightFace `buffalo_l`** (licença só para pesquisa não comercial) em código de produção. Motor atual: OpenCV YuNet + SFace (Apache 2.0).
- Eventos com menores: modo restrito por padrão (código de acesso, limite de buscas).
- Armazenamento permanente = **Google Drive** do cliente. No servidor só o que é regenerável (índice e miniaturas).
- Segredos (senhas, tokens, JSON da conta de serviço) nunca no código nem no chat. Ficam no `.env` (fora do Git).

## Convenções
- Python 3.12+, FastAPI, SQLAlchemy 2, `ruff` (lint + format), `pytest`. Front: Vite + React + TypeScript (`web/`).
- SQLite em desenvolvimento; PostgreSQL em produção (ainda não validado).
- Commits convencionais em pt-BR (`feat:`, `fix:`, `docs:`, `test:`, `chore:`).
- Decisão de arquitetura nova = novo ADR em `docs/11-decisoes-adrs.md`.
- Valores incertos: diga "estimativa" ou "não confirmado". Não invente preço, prazo ou regra da Meta/Google.

## Antes de concluir uma tarefa
1. `python -m pytest -q` e `ruff check src tests scripts` passando; no front, `npx tsc --noEmit`.
2. Se mexeu no reconhecimento: medir com fotos reais / golden set e anotar o resultado.
3. Atualizar `CONTINUAR-AQUI.md` (estado) e os docs/ADRs afetados.
