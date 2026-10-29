# 10 · Qualidade e operação

## 1. Pirâmide de testes

| Nível | O que cobre | Ferramentas | Quando roda |
|-------|-------------|-------------|-------------|
| **Unidade** | Regras (limiares, máquina de estados, parser de palavra-chave, ordenação), funções puras | `pytest`, `vitest` | A cada commit |
| **Contrato** | Webhooks da Meta com *fixtures* reais anonimizadas; respostas da Graph API; Drive API (gravadas) | `pytest` + `respx`/`vcr` | A cada commit |
| **Integração** | API + Postgres + fila + R2 local (MinIO) em contêineres | `pytest` + `testcontainers` | A cada PR |
| **Isolamento de tenant** | Consultas tentando ler dados de outro tenant devem falhar (RLS) | Suite dedicada | Cada PR; bloqueia merge |
| **Privacidade** | Nenhuma rota/log/disco guarda a selfie; purga de retenção funciona | Testes que inspecionam FS e logs | Cada PR |
| **Qualidade do motor** | Golden set: precisão, recall, latência, custo | `bench/` | Cada troca de modelo/limiar; semanal |
| **E2E** | Site: selfie → galeria → ZIP; bot simulado | Playwright; simulador de webhook | Antes de cada release |
| **Carga** | 300 buscas/min e pico de 1.000 simultâneas; ingestão de 20 mil fotos | k6 / Locust | Antes de cada evento grande |
| **Caos/falha** | Meta fora, Drive 429, R2 lento, worker morto, banco lento | Scripts de falha | Trimestral e pré-evento |
| **Segurança** | SAST/dep audit, segredos, OWASP ZAP no staging | `bandit`, `pip-audit`, `trivy`, ZAP | CI + antes do piloto |
| **Acessibilidade/UX** | WCAG, câmera em iOS/Android reais | axe, teste manual em 5 aparelhos | Antes de releases do site |

**Regressão de reconhecimento** é o teste mais importante: um pull request que altere pipeline, modelo ou limiar roda o golden set e **falha se a precisão cair > 0,5 p.p. ou o recall > 1 p.p.**

## 2. Qualidade de código e processo

- **Monorepo:** `apps/api`, `apps/web`, `packages/flash_core` (domínio), `bench/`, `docs/`, `infra/`.
- **Python:** `ruff` (lint+format), `mypy --strict` no domínio, `pytest`. **TypeScript:** `eslint`, `tsc --noEmit`.
- **Git:** *trunk-based* com branches curtos; *Conventional Commits* (você já usa: `feat:`, `fix:`, `docs:`); PRs pequenos; `/code-review` antes de mesclar; *squash merge*.
- **CI (GitHub Actions):** lint → testes → imagem Docker → varredura (`trivy`) → publicar `ghcr.io` → deploy em staging; produção por *tag* e aprovação manual.
- **Versionamento:** SemVer da aplicação; versão do esquema de configuração separada; `index_version` por evento.
- **Migrações:** Alembic, revisadas, reversíveis quando possível, padrão *expand/contract*.
- **Segredos:** `.env` fora do Git; SOPS+age para produção; `gitleaks` no CI.
- **Documentação viva:** README por pacote, ADRs, OpenAPI gerado, *runbooks* neste diretório.

## 3. Observabilidade

| Pilar | O que registrar | Ferramenta |
|-------|-----------------|-----------|
| **Logs** | JSON estruturado, `tenant_id`, `event_id`, `job_id`, IDs mascarados; **nunca** corpo com imagem | stdout → Loki/arquivo rotacionado |
| **Métricas** | Fotos/min, fila, erros por tipo, latência da busca (p50/p95/p99), mensagens enviadas, falhas Meta, cota Drive, CPU/memória | Prometheus + Grafana |
| **Traços** | Busca e job de ingestão | OpenTelemetry (opcional) |
| **Erros** | Exceções com contexto | Sentry |
| **Negócio** | Funil do bot, conversão do gate, buscas/evento, custo/evento | Painel interno + `usage_meter` |
| **Disponibilidade** | Site, API, webhook, fila parada | Uptime Kuma + alerta Telegram |

**SLOs e alertas:** latência de busca p95 > 3 s por 5 min; erro 5xx > 1%; fila de ingestão > 30 min de atraso; falha de envio de DM > 5%; token do Instagram expira em < 10 dias; disco > 80%; backup falhou.

## 4. Runbook de dia de evento

**D-14 a D-7**
- [ ] Contrato, DPA e texto de consentimento assinados; cliente confirmou inscrições com aceite dos responsáveis.
- [ ] Evento criado; pasta do Drive compartilhada; testar com 50 fotos.
- [ ] Conta do Instagram conectada; token válido; gate configurado; palavras-chave e ice breaker publicados.
- [ ] Domínio/QR code prontos; arte do cartaz ("Escaneie e ache suas fotos").
- [ ] Teste de carga e verificação de backup.

**D-1**
- [ ] Congelar deploys. Verificar monitores. Confirmar plantão e canal de incidentes.
- [ ] Subir lote-teste de fotos e executar busca completa pelo site e pelo Instagram.
- [ ] Checar limite de armazenamento do Drive do cliente e do VPS.

**Dia do evento**
- [ ] Fotógrafos sobem em lotes (a cada ~15 min); acompanhar progresso e erros no painel.
- [ ] Postar o QR code/palavra-chave nos telões e Stories quando o índice cobrir ≥ 80% das fotos do dia.
- [ ] Monitorar funil e latência; responder a pedidos de remoção em até 24 h (idealmente na hora).
- [ ] Ligar workers extras se a fila passar de 20 min.

**D+1 a D+7**
- [ ] Reprocessar erros; rodar relatório; coletar feedback.
- [ ] Encerrar o evento (muda para `closed`); agendar retenção (padrão +90 dias).

**D+90**
- [ ] Purga automática dos vetores; relatório de descarte ao cliente; arquivar evento.

## 5. Modos de falha e resposta

| Falha | Sintoma | Resposta |
|-------|---------|----------|
| Drive 429/permissão revogada | Fila de erros, `403/429` | Backoff; pausar download; avisar cliente a recompartilhar pasta |
| Worker lento | Fila cresce | Escalar workers; reduzir resolução de detecção; pular rajadas |
| Meta fora / rate limit | DMs falham | Fila com *retry*, mensagem de contingência no site, não perder estado |
| Banco lento | Latência alta | Checar índices, `VACUUM`, réplica de leitura; ativar cache |
| Pico de buscas | Latência acima do SLO | Cache de resultados idênticos, aumentar réplicas da API, limitar buscas/IP |
| Token do Instagram vencido | Bot silencioso | Alerta 10 dias antes, renovação automática; fallback para site |
| Disco cheio | Erros de escrita | Limpar derivados antigos, aumentar volume |
| Vazamento suspeito | Alerta de auditoria | Plano de incidentes: conter, avaliar, comunicar (ANPD/titulares conforme o caso) |

**Modo contingência (sempre pronto):** o cliente continua com o fluxo de hoje (Drive compartilhado). O FLASH! nunca pode ser pior que o status quo.

## 6. Backup e recuperação

- **Dados críticos:** Postgres (esquema, eventos, consentimentos, auditoria). Originais ficam no Drive do cliente; previews são regeneráveis.
- **Rotina:** *dump* lógico diário + WAL contínuo para R2 criptografado; retenção 30 dias; **restauração testada todo mês**.
- **RTO/RPO MVP:** 4 h / 24 h; meta na Fase 3: 1 h / 15 min.
- **Reindexação** como mecanismo de recuperação: se o índice se perder, é regenerável a partir do Drive.

## 7. Suporte e onboarding de cliente

1. **Checklist de onboarding (≤ 10 min):** criar tenant → tema → conectar Instagram → criar evento → compartilhar pasta → teste com 3 fotos → publicar QR.
2. **Canal de suporte:** WhatsApp do plantão em eventos; e-mail no dia a dia; base de conhecimento curta com vídeos.
3. **SLAs (proposta):** resposta em 15 min em janela de evento; 1 dia útil fora dela.
4. **Pós-evento:** relatório com métricas (buscas, taxa de sucesso, novos seguidores, fotos baixadas) para o cliente mostrar resultado.
