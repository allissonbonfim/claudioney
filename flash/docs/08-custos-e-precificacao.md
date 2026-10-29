# 08 · Custos e precificação

> Valores em **US$ verificados** quando indicado; o restante é **estimativa**. Câmbio de referência para conversões: R$ 5,50/US$ (ajuste). Reconfirme tabelas antes de assinar contratos.

## 1. Onde o dinheiro vai

| Etapa | Frequência | Custo dominante |
|-------|-----------|-----------------|
| Indexar fotos | 1× por foto | CPU (ou API por imagem) |
| Armazenar previews | contínuo | R2 (centavos) |
| Buscar por selfie | N× por evento | CPU insignificante + banco |
| Entregar (DM / site / ZIP) | N× | Largura de banda (CDN com egress zero) |
| Banco + VPS | fixo mensal | O maior custo fixo |
| Instagram API | por mensagem | Sem tarifa por mensagem na API (confirmar) |

## 2. Cenários de indexação (por evento)

### Opção A — Amazon Rekognition (gerenciado)

Preço (verificado na página da AWS): **US$ 0,001 por imagem** (Grupo 1: `IndexFaces`, `SearchFacesByImage`) nos primeiros 1 milhão de imagens/mês; **US$ 0,00001 por vetor de rosto/mês** de armazenamento; 1.000 imagens/mês grátis nos primeiros 12 meses.

| Evento | Imagens | Rostos (≈ 6/foto) | Indexar | Buscas (3.000) | Armazenar 3 meses | **Total** |
|--------|--------:|------------------:|--------:|---------------:|------------------:|----------:|
| Pequeno | 5.000 | 30.000 | US$ 5 | US$ 3 | US$ 0,9 | **~US$ 9** |
| Médio | 20.000 | 120.000 | US$ 20 | US$ 3 | US$ 3,6 | **~US$ 27** |
| Grande | 100.000 | 600.000 | US$ 100 | US$ 5 | US$ 18 | **~US$ 123** |

(Se a busca usar `SearchFacesByImage`, cada selfie conta como 1 imagem; buscas com múltiplas selfies multiplicam.) **Ressalva:** confirmar `IndexFaces` em região adequada e a questão LGPD de transferência internacional.

### Opção B — Motor próprio em CPU (OpenCV YuNet+SFace ou InsightFace licenciado)

Premissa (estimativa): ~0,3–0,6 s de CPU por foto de 2048 px (decodificação + detecção + embedding de ~6 rostos). SFace ≈ 9 ms por rosto e YuNet ≈ 1,5 ms em entrada pequena (benchmarks do cartão do modelo, CPU Intel); o resto é decodificação e redimensionamento.

| Evento | Fotos | CPU-segundos | Tempo em 4 vCPU | Custo extra |
|--------|------:|-------------:|----------------:|-------------|
| Pequeno | 5.000 | ~2.500 | ~10 min | R$ 0 (VPS fixa) |
| Médio | 20.000 | ~10.000 | ~40 min | R$ 0 |
| Grande | 100.000 | ~50.000 | ~3,5 h | R$ 0 ou VM extra por ~R$ 5–15 |

→ **Em volume, motor próprio é praticamente grátis na margem**; Rekognition ganha quando o volume é baixo e você não quer operar nada, e como motor "premium".

### Opção C — InsightFace licenciado

Mesma conta da B, com um custo fixo/ recorrente de licença **a cotar**. Só vale se a Spike S1 mostrar ganho de *recall* que pague a licença.

## 3. Custos fixos mensais (estimativa, até ~5 clientes)

| Item | Estimativa | Observação |
|------|-----------:|-----------|
| VPS 4 vCPU/8 GB no Brasil | R$ 80–250 | Comparar Oracle, AWS Lightsail/EC2 reservada, Magalu, VPS nacional |
| Cloudflare (DNS/CDN/Turnstile) | R$ 0 | Plano gratuito |
| R2 (armazenamento) | R$ 1–20 | ~US$ 0,015/GB-mês; 20 mil previews de ~350 KB ≈ 7 GB ≈ centavos; **egress zero** (valores de tabela a confirmar) |
| Backups (R2/B2) | R$ 5–20 | |
| Domínio(s) | R$ 3–10 | Domínios dos clientes são deles |
| Sentry / monitor | R$ 0 | Planos gratuitos no começo |
| E-mail transacional | R$ 0–30 | Provedor com camada gratuita |
| Jurídico (DPA, termos, RIPD) | **investimento inicial** R$ 3–10 mil | Pontual, essencial |
| Meta | R$ 0 | Sem tarifa de API; custo é tempo de verificação |
| **Total fixo** | **~R$ 100–350/mês** | |

## 4. Custo variável por evento (exemplo: 20 mil fotos, 3.000 buscas)

| Item | Motor próprio | Rekognition |
|------|--------------:|------------:|
| Indexação | ~R$ 0 | ~R$ 110 |
| Buscas | ~R$ 0 | ~R$ 17 |
| Vetores armazenados (3 meses) | ~R$ 0 (já no Postgres) | ~R$ 20 |
| Previews (R2, 3 meses) | ~R$ 1 | ~R$ 1 |
| Rede/CDN | ~R$ 0 | ~R$ 0 |
| Meta/Instagram | R$ 0 | R$ 0 |
| **Total variável** | **< R$ 5 + fração do fixo** | **~R$ 150** |
| Fixo rateado (5 eventos/mês) | ~R$ 40 | ~R$ 40 |
| **Custo total por evento** | **~R$ 45** | **~R$ 190** |

Mesmo no cenário mais caro, o custo do evento é uma fração mínima do que o cliente gasta com fotografia.

## 5. Precificação

**Princípios:** preço por **valor** (tempo economizado do cliente, engajamento/seguidores, percepção de profissionalismo), não por custo. O custo só define o piso.

### Estrutura sugerida (hipóteses a validar com 3–5 clientes)

| Plano | Para quem | Inclui | Preço de partida (ilustrativo) |
|-------|-----------|--------|-------------------------------:|
| **Evento Pontual** | Cliente eventual | 1 evento, até 5 mil fotos, site + bot, retenção 90 dias | R$ 1.200–2.500 |
| **Evento Plus** | Cliente médio | Até 20 mil fotos, domínio próprio, painel de métricas, relatório | R$ 2.500–5.000 |
| **Assinatura Anual** | Federações, redes de escolas | 6–12 eventos/ano, white-label total, prioridade | R$ 1.500–3.500/mês |
| **Enterprise** | Grandes eventos | Volume > 50 mil fotos, SLA, integrações, motor premium | sob consulta |
| **Add-ons** | | Foto por número de peito, WhatsApp, impressão/QR, revenda de fotos, curadoria | por item |

> Os valores acima são **ponto de partida para teste**, não recomendação financeira. Teste com preço âncora, vá ajustando por evidência (taxa de fechamento, objeções).

### Margem

Com custo de R$ 45–170 por evento e preço de R$ 1.200+, a margem bruta é de **85–95%**, mesmo contando jurídico e suporte. Atenção ao **custo escondido**: suporte em dia de evento, ajustes de fluxo e onboarding. Reserve horas na precificação.

## 6. Medição de uso e controle de custo

- `usage_meter` por tenant/evento/dia (fotos, rostos, buscas, DMs, bytes) já no MVP: base de faturamento e de alerta de custo.
- Alerta: evento com consumo > 150% do plano; custo de API > teto configurado; fila crescendo.
- Painel interno "custo por cliente" com margem calculada.
- Faturamento: PIX/boleto/cartão via gateway brasileiro (Asaas, Pagar.me, Mercado Pago); nota fiscal de serviço.

## 7. Como baixar ainda mais o custo (sem perder qualidade)

1. Reduzir a resolução de detecção quando as fotos forem de close; ligar *tiles* só onde o *recall* exige.
2. INT8 / ONNX Runtime com otimizações; processamento em lotes.
3. Pular quase duplicatas (rajadas): indexar a melhor de cada rajada e herdar para as irmãs por hash perceptual (reduz 20–40% em esporte, hipótese).
4. Workers efêmeros ligados só durante picos.
5. `halfvec` e retenção curta de vetores.
6. CDN com cache agressivo para miniaturas.
