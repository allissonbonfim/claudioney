# 09 · Roadmap, backlog e riscos

## 1. Estratégia de entrega

1. **Reduzir incerteza antes de construir** (fase 0 com spikes).
2. **Fatias finas e ponta a ponta** (do Drive à foto na tela) desde a primeira fase.
3. **Piloto real** em um evento CBDE com observação de ponta a ponta.
4. **Só então generalizar** (multi-cliente, painel completo, cobrança).

Prazos em semanas de trabalho de uma pessoa com apoio de IA (ritmo parcial); ajuste ao seu tempo disponível.

```mermaid
gantt
  dateFormat  YYYY-MM-DD
  axisFormat  S%W
  section Fase 0 · Descoberta
  Spikes S1–S6, golden set       :f0, 2026-10-26, 14d
  Meta: verificação e submissão  :crit, meta, 2026-10-26, 45d
  Jurídico: DPA, termos, consent :jur, 2026-10-26, 21d
  section Fase 1 · Núcleo web
  Ingestão Drive + índice        :f1a, after f0, 14d
  Busca web + galeria + ZIP      :f1b, after f1a, 14d
  section Fase 2 · Instagram
  Bot + gate + entrega           :f2, after f1b, 14d
  section Piloto
  Evento CBDE (observado)        :milestone, pil, after f2, 1d
  section Fase 3 · Produto
  Multi-cliente, painel, billing :f3, after f2, 28d
```

## 2. Fase 0 — Descoberta (2 semanas) — **critério Go/No-Go**

| Spike | Pergunta | Entrega | Critério de sucesso |
|-------|----------|---------|---------------------|
| **S1 · Motor facial** | Qual motor atinge as metas em fotos de esporte? | Relatório do golden set: SFace × Rekognition × (InsightFace p/ comparação interna) | Algum motor com precisão ≥ 98% e recall ≥ 90% a custo aceitável; se não, definir plano (licença, ladrilhos, multi-selfie) |
| **S2 · Pipeline de CPU** | Quantas fotos/min por vCPU? Quanto custa a decodificação? | Medição com `pyvips` + ONNX | ≥ 60 fotos/min/vCPU a 2048 px |
| **S3 · Drive** | Conta de serviço + pasta compartilhada: `changes`, cotas, download em massa, miniatura grande (`thumbnailLink`) vs. original | Script e nota técnica | 5 mil fotos baixam sem erro de cota; decidir original × miniatura |
| **S4 · Instagram** | Webhook, perfil, `is_user_follow_business`, envio de 10 imagens, limites reais, **piloto sem App Review?** | Bot "eco" funcional com 2 contas de teste | Campo de seguidor funciona; 10 imagens/mensagem entregues; decisão sobre piloto em modo de desenvolvimento |
| **S5 · Busca vetorial** | Latência da busca exata com 200 mil–1 milhão de rostos no pgvector | Benchmark | p95 ≤ 100 ms (200 mil) em VPS alvo |
| **S6 · Infra** | Qual VPS brasileira por custo/desempenho? Backup/restore? | Comparativo + teste de restauração | Escolha justificada, restauração < 30 min |

**Go/No-Go (fim da semana 2):** prosseguir se (a) S1 atinge metas ou há caminho claro; (b) S4 confirma o gate; (c) parecer jurídico preliminar não bloqueia; (d) Meta iniciou verificação. Caso contrário, reabrir escopo (ex.: só site no piloto).

## 3. Fase 1 — Núcleo web (4 semanas)

> **Andamento (22/10/2026):** a primeira versão do núcleo já roda localmente (ingestão de pasta local e Drive, motor YuNet+SFace, busca, site com selfie/galeria/ZIP, painel básico, 23 testes). **Ainda não foi validada com fotos reais nem com o Drive real**; isso depende do golden set e das credenciais (ver `README.md` do projeto). Instagram segue na Fase 2, sem bloquear esta.

**Objetivo:** fotógrafo sobe no Drive → participante acha no site. **Sem Instagram, sem multi-cliente.**

Entregas: repositório e CI, esquema do banco, `FaceEngine` com 1–2 motores, ingestão contínua, derivados no R2, busca, galeria, download/ZIP, painel mínimo (criar evento, progresso, ocultar foto), modo menores (código do evento), pedidos de remoção básicos, `usage_meter`.

**Definição de pronto da fase:** evento de 5.000 fotos indexado em < 30 min; 20 pessoas reais testam e a precisão medida cumpre a meta; zero armazenamento de selfie comprovado por teste.

## 4. Fase 2 — Instagram (2–3 semanas)

Entregas: OAuth e conexão da conta, webhook seguro, máquina de estados, consentimento, escolha de evento, selfie, teaser, **follow gate** com botão, entrega de 20 fotos + link, ice breaker, handoff, métricas do funil.

**Definição de pronto:** 30 testadores executam o fluxo completo; 0 mensagens duplicadas; recuperação de falhas; conversão do gate medida.

## 5. Piloto (1 evento CBDE)

- Escolher evento de risco moderado; **equipe de plantão**; plano de contingência (entregar no Drive como hoje se algo falhar).
- Medir: buscas, sucesso, tempo, novos seguidores, satisfação, custo real, incidentes.
- Retrospectiva e *backlog* de correções antes de vender para outros.

## 6. Fase 3 — Produto vendável (4 semanas)

Multi-tenant completo (RLS, temas, domínio próprio), painel do cliente com métricas e relatório, editor de fluxo do bot, faturamento por uso, documentação, onboarding de cliente em ≤ 10 min, backups automatizados, painel de custos.

## 7. Fase 4+ — Evolução

| Item | Valor |
|------|-------|
| Clusters + "Qual destes é você?" | Recall |
| Facetas por pasta e filtros | Experiência |
| Número de peito (OCR) / time | Esporte e corridas |
| WhatsApp | Alcance no Brasil |
| Embedding no navegador (privacidade) | Diferencial LGPD |
| Venda de fotos (PIX) | Nova receita |
| Marketplace de temas/fluxos | Escala comercial |
| Reidentificação para "momentos" (highlights) | Conteúdo para redes |

## 8. Backlog inicial priorizado (épicos → primeiras histórias)

| Ordem | História | Fase |
|------:|----------|------|
| 1 | Esqueleto do monorepo + CI + `docker compose` | 1 |
| 2 | Modelo de dados e migrações (tenant, event, photo, face) | 1 |
| 3 | `FaceEngine` + adaptador SFace + testes com golden set | 1 |
| 4 | Conector Drive (conta de serviço, `changes`) | 1 |
| 5 | Worker: download → derivados → detectar → gravar | 1 |
| 6 | API de busca + pós-processamento + limiares | 1 |
| 7 | Site: seleção de evento, câmera, galeria, download | 1 |
| 8 | ZIP em streaming + magic link | 1 |
| 9 | Painel mínimo e progresso | 1 |
| 10 | Modo menores (código, limites) | 1 |
| 11 | Webhook Meta + assinatura + deduplicação | 2 |
| 12 | Máquina de estados do bot | 2 |
| 13 | Gate com `is_user_follow_business` | 2 |
| 14 | Entrega 10+10 imagens + link | 2 |
| 15 | Métricas do funil | 2 |

## 9. Registro de riscos {#riscos}

Probabilidade (P) e Impacto (I): A/M/B.

| # | Risco | P | I | Resposta |
|---|-------|---|---|----------|
| R1 | Questionamento jurídico (biometria de menores; terceiros nas fotos) | M | A | Advogado no dia 0; consentimento na inscrição; modo menores; retenção curta; RIPD; contrato de operador |
| R2 | Meta atrasa/nega App Review | M | A | Iniciar no dia 0; piloto em modo de desenvolvimento; ponte ManyChat; WhatsApp como alternativa |
| R3 | Precisão insuficiente em esporte (capacete, movimento) | M | A | Golden set; clusters; multi-selfie; tiles; motor premium |
| R4 | Licença do modelo (InsightFace) | A (se usado) | A | `FaceEngine` plugável; SFace/Rekognition; licença comercial se necessário |
| R5 | Abuso: localizar criança específica | M | A | Código do evento, limites, detecção de varredura, auditoria, bloqueio |
| R6 | Cota/bloqueio do Google Drive | M | M | Conta de serviço, backoff, `changes` em vez de varredura, limite de concorrência; plano B: upload direto |
| R7 | Pico de buscas no encerramento do evento | M | M | Busca exata leve, réplica de leitura, cache, teste de carga |
| R8 | Dependência de um dev/uma pessoa (você) | A | M | Docs (este manual), automação, CI, backups, ADRs |
| R9 | Mudança de política da Meta | M | M | Abstração de canal; WhatsApp; site como canal principal |
| R10 | Custo de API (Rekognition) sair do controle | B | M | Quotas por tenant, alerta, preferir motor próprio em volume |
| R11 | Nome "FLASH!" conflita com marca existente | A | M | Busca no INPI; nome alternativo/slogan; domínio |
| R12 | Fotógrafos sobem fotos fora de contexto/ilícitas | B | A | Moderação, papéis, denúncia, cláusula contratual |
| R13 | Perda de dados / falha de backup | B | A | Backup testado; fotos originais no Drive (fonte da verdade) |
| R14 | Cliente descontente por falha em dia de evento | M | A | Piloto, plantão, modo contingência, SLA de janela |

## 10. Definições de processo

**Definition of Ready (história):** objetivo claro, critérios de aceite testáveis, dependências conhecidas, tamanho ≤ 2 dias.
**Definition of Done:** código revisado (inclusive por `/code-review`), testes automatizados, documentação/ADR atualizados, métricas/logs, sem segredos no repositório, implantado em staging e validado.
**Cadência:** ciclos de 1 semana; demonstração ao fim; retrospectiva a cada piloto; revisão mensal de custos e riscos.
**Governança:** decisões relevantes viram ADR ([11](11-decisoes-adrs.md)); mudança de escopo atualiza [02](02-requisitos.md).
