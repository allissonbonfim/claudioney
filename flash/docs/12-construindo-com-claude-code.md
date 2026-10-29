# 12 · Construindo o FLASH! com o Claude Code

Como transformar este manual em software sem se perder. O princípio: **a documentação é o contrato; a IA executa fatias pequenas e verificáveis; os testes dizem se funcionou.**

## 1. Regras de trabalho

1. **Uma fatia por vez, ponta a ponta.** Cada pedido entrega algo que roda e é testado (ex.: "dado uma pasta com 10 fotos, indexa e retorna os rostos"), nunca "construa o sistema inteiro".
2. **Teste primeiro nas partes que erram em silêncio:** limiares, máquina de estados, isolamento de tenant, não-persistência da selfie.
3. **O golden set manda.** Nenhuma mudança de modelo ou limiar entra sem rodar `bench/`.
4. **Decisão nova = ADR novo.** Peça ao Claude para propor o ADR antes de mudar a arquitetura.
5. **Revisão antes de mesclar:** `/code-review` em cada PR e `/security-review` antes do piloto.
6. **Segredos nunca em conversa nem em Git.** Tokens da Meta, chaves da AWS e do Cloudflare vão em `.env`/SOPS; o Claude usa variáveis de ambiente.
7. **Commits pequenos e convencionais**, como você já faz (`feat(ingest): …`).

## 2. Estrutura inicial do repositório

```text
flash/
├─ README.md                  # como rodar (fonte da verdade do dia a dia)
├─ docs/                      # este manual
├─ src/flash/                 # pacote Python: faces, sources, storage, ingest, index, search, channels, api
├─ web/                       # site (Vite + React + TypeScript)
├─ tests/                     # pytest (motor falso)
├─ scripts/                   # fetch_models.py, make_demo.py
├─ infra/                     # docker-compose (não testado), Dockerfile na raiz
└─ bench/                     # (a criar) golden set e relatórios do Spike S1
```

> Estrutura real em 22/10/2026 (ajustada em relação ao plano inicial: pacote único `src/flash`, SPA em vez de Next.js — ver ADR-018 a 022).
>
> O workspace atual é um repositório com vários projetos. Recomendo que o FLASH! tenha **repositório próprio** (`git init` dentro de `flash/`) para CI, issues e histórico limpos.

## 3. `CLAUDE.md` sugerido para o projeto

```markdown
# FLASH! — instruções para o Claude

Produto: busca de fotos de eventos por selfie (site + Direct do Instagram). Leia `docs/00-LEIA-ME.md` e o documento do tema antes de mexer.

## Inegociáveis
- A selfie NUNCA é gravada (disco, log, banco, fila). Só o vetor, em memória/sessão com TTL.
- Toda tabela de negócio tem tenant_id + RLS. Query sem tenant_id é bug.
- Motor facial só via interface FaceEngine. Nunca importe insightface/onnx direto fora de packages/flash_core/faces.
- Não use modelos com licença não comercial em código de produção.
- Webhook da Meta: validar assinatura, deduplicar por mid, responder 200 e enfileirar.
- Eventos com menores: modo restrito por padrão.

## Convenções
- Python 3.12, ruff, mypy --strict no domínio, pytest. TypeScript estrito.
- Commits convencionais em pt-BR (feat:, fix:, docs:, test:, chore:).
- Migrações com Alembic, expand/contract.
- Config por tenant/evento em JSON validado por esquema.

## Antes de concluir uma tarefa
1. Rodar lint, tipos e testes.
2. Se tocou reconhecimento: rodar bench e anexar o resultado.
3. Atualizar docs/ADR se mudou decisão.
4. Não deixar segredos no repositório.
```

## 4. Sequência de prompts-guia (Fase 0 e 1)

Use como roteiro; ajuste ao que já existir.

**Spike S1 — benchmark do motor**
> "Crie `bench/` com um script que lê `golden/labels.csv` (foto, pessoa) e `golden/selfies/`, roda o `FaceEngine` escolhido, e gera um relatório de Precisão×Recall por limiar e custo por 1.000 fotos. Implemente adaptadores para OpenCV YuNet+SFace e AWS Rekognition. Não grave dados pessoais em logs."

**Esqueleto**
> "Monte o monorepo conforme `docs/12`: `docker compose` com Postgres+pgvector, API FastAPI com `/health`, worker, CI no GitHub Actions com ruff, mypy e pytest. Inclua migração inicial com as tabelas de `docs/06` e teste de RLS que prove isolamento entre dois tenants."

**Ingestão do Drive**
> "Implemente o conector do Drive com conta de serviço: listar pasta recursivamente, seguir `changes`, ignorar pastas `_nao_publicar`, baixar com backoff e respeitar concorrência máxima. Idempotência por `(event_id, drive_file_id, md5)`. Teste com respostas gravadas."

**Pipeline**
> "Implemente o job de indexação: decodificar, orientar por EXIF, gerar 2048/1600/400 px com pyvips, enviar previews ao R2 (MinIO no teste), detectar e embedar rostos via `FaceEngine`, gravar `face` com qualidade. Teste que reexecutar o job não duplica rostos."

**Busca**
> "Implemente `POST /v1/public/events/{slug}/search` conforme `docs/06`. Valide a selfie (1 rosto, qualidade), extraia o vetor, descarte a imagem, busque exato filtrando por evento, aplique `τ_alto`/`τ_baixo` do evento, agrupe por foto e devolva 'certain'/'maybe'. Inclua teste que prove que nenhum byte da selfie é gravado."

**Bot**
> "Implemente o webhook da Meta (verificação, HMAC, deduplicação por mid) e a máquina de estados de `docs/05`. Use o JSON de fluxo de exemplo. Cubra com testes de fixtures: palavra-chave, consentimento, evento, selfie inválida, gate com `is_user_follow_business` falso→verdadeiro, entrega 10+10."

**Segurança**
> "Faça um `/security-review` do branch; verifique upload de imagem, SSRF no download de mídia da Meta, vazamento entre tenants, logs com dados pessoais."

## 5. Como pedir bem (padrão de bom pedido)

- **Contexto:** qual documento/ADR vale.
- **Resultado:** o que deve existir e rodar.
- **Critérios de aceite:** copie de `docs/02`.
- **Fora de escopo:** o que não mexer.
- **Verificação:** quais testes/benchmarks devem passar.

## 6. Agentes e skills úteis neste projeto

| Necessidade | Ferramenta |
|-------------|-----------|
| Revisar código | `/code-review`, `/simplify` |
| Segurança | `/security-review` |
| Rodar e ver o app | skill `run` + navegador do app para o site |
| Roteiro de vídeo/campanha de lançamento | skill `barizon-do-marketing` |
| Documentos comerciais (proposta, contrato) | skill `documentos-bomfim` |
| Pesquisa de concorrentes no Instagram | skill `rm-concorrentes` |

## 7. Disciplina de custos (para você, dono)

- Revisar `usage_meter` toda semana nos primeiros 3 meses.
- Teto de gasto na AWS (se usar Rekognition) e alertas de orçamento.
- Cada novo serviço pago exige um ADR curto com "o que deixamos de fazer sem ele".
