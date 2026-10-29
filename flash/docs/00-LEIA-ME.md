# FLASH! — Manual de Produto e Engenharia

> **Versão:** 0.1 (rascunho de fundação) · **Data:** 22/10/2026 · **Dono:** Allisson Bonfim (Bom&fim Fullscope)
> **Cliente-piloto:** CBDE · **Status:** pré-projeto — nada foi codificado ainda

FLASH! é uma plataforma que transforma **milhares de fotos de evento em Google Drive** em **entrega individual e instantânea**: o participante manda uma selfie (no site ou no Direct do Instagram) e recebe todas as fotos em que aparece.

Este manual é o conjunto de documentos que precisa existir **antes** da primeira linha de código: visão, requisitos, arquitetura, decisões, riscos jurídicos, custos, plano e forma de testar. Foi escrito para você (dono do produto, que vai construir com apoio do Claude Code) e para qualquer dev que entre depois.

## Como ler

| # | Documento | Responde a |
|---|-----------|-----------|
| 01 | [Visão do produto](01-visao-produto.md) | Para quem é, por que ganha, o que é e o que **não** é |
| 02 | [Requisitos](02-requisitos.md) | O que o sistema faz (histórias + critérios de aceite) e com que qualidade |
| 03 | [Arquitetura](03-arquitetura.md) | Como as peças se encaixam, fluxos e como mantê-lo barato |
| 04 | [Reconhecimento facial](04-reconhecimento-facial.md) | Qual motor usar, licenças, pipeline, precisão, como medir |
| 05 | [Bot do Instagram](05-instagram-bot.md) | Fluxo de conversa, limites da Meta, *follow gate*, entrega |
| 06 | [Dados e API](06-dados-e-api.md) | Modelo de dados, endpoints, multi-cliente |
| 07 | [Segurança, LGPD e abuso](07-seguranca-lgpd-abuso.md) | O maior risco do projeto: biometria de menores |
| 08 | [Custos e precificação](08-custos-e-precificacao.md) | Quanto custa operar, quanto cobrar |
| 09 | [Roadmap e backlog](09-roadmap-e-backlog.md) | Spikes, fases, critérios de Go/No-Go |
| 10 | [Qualidade e operação](10-qualidade-e-operacao.md) | Testes, CI/CD, observabilidade, roteiro de dia de evento |
| 11 | [Decisões (ADRs)](11-decisoes-adrs.md) | Cada decisão técnica, alternativas e por quê |
| 12 | [Construindo com Claude Code](12-construindo-com-claude-code.md) | Método de trabalho, `CLAUDE.md` do projeto, prompts-guia |
| 13 | [Hospedagem](13-hospedagem.md) | Onde o FLASH! roda: planos pesquisados, preços e recomendação |

## Resumo executivo (1 minuto)

**Ideia original (sua):** subir fotos no Drive → FLASH! indexa rostos → atleta acha suas fotos por selfie no site ou no Instagram (palavra-chave "Quero minha foto" → escolhe evento → manda selfie → *follow check* em loop → recebe as fotos).

**O que a análise confirma:**

- A ideia é tecnicamente viável, e o **custo marginal é baixíssimo**: indexar 20 mil fotos custa na ordem de **US$ 20 em API gerenciada** ou **~40 min de CPU** (4 vCPU) em servidor próprio; cada busca por selfie custa frações de centavo. Veja [08](08-custos-e-precificacao.md).
- O *follow check* é possível pela API oficial (campo `is_user_follow_business` do perfil de quem conversa com a conta).
- Concorrentes existem (Fotop, OPIC, Kamero, Supa Waldo…), mas nenhum que eu tenha encontrado combina **Drive nativo + entrega por Direct do Instagram com *follow gate* + white-label barato**. É esse o espaço do FLASH!. (Pesquisa superficial; faça uma análise competitiva de verdade antes de precificar.)

**Onde a ideia precisa de aperfeiçoamento (o miolo deste manual):**

| # | Aperfeiçoamento | Por quê |
|---|-----------------|---------|
| 1 | **Teaser antes do *follow gate***: buscar primeiro e dizer "achei 37 fotos suas! Siga @cbde para liberar" | A busca custa quase zero e o número é o melhor argumento para a pessoa seguir |
| 2 | **Guardar só o *embedding* da selfie**, nunca a imagem; descartar em minutos | Minimiza dado biométrico, resolve o loop de espera do *follow gate* e reduz risco LGPD |
| 3 | **DM entrega as melhores 10–20 fotos + link da galeria completa** | A API aceita até 10 imagens por mensagem e 8 MB por imagem; entregar 200 fotos por DM é lento e parece spam |
| 4 | **Agrupar rostos em "pessoas" (clusters) e aceitar 2–3 selfies** | Atleta de capacete, óculos, de perfil e em movimento é onde o reconhecimento falha; clusters recuperam essas fotos |
| 5 | **Modo "evento com menores"**: código do evento + limite de buscas | Sem isso FLASH! vira ferramenta para localizar uma criança específica |
| 6 | **Motor facial plugável (`FaceEngine`)** | Os modelos mais usados (InsightFace `buffalo_l`) são **proibidos para uso comercial sem licença**; a decisão precisa ser reversível |
| 7 | **Drive via conta de serviço** (cliente compartilha a pasta com o FLASH!) | Evita OAuth com escopo "restrito" do Google, que exige auditoria de segurança |
| 8 | **Originais ficam no Drive; só *previews* no R2/CDN** | Armazenamento e tráfego quase zero; o cliente continua dono do acervo |
| 9 | **Tudo no Postgres** (dados + vetores + fila) | Um serviço a menos para pagar, vigiar e restaurar |
| 10 | **Fluxos de conversa, textos e limiares como configuração por cliente** | É isso que torna o produto vendável a vários clientes sem fork de código |
| 11 | **Facetas por pasta** (modalidade, dia, quadra) como filtros | Fotógrafo já organiza pastas; vira busca "só meu jogo de vôlei de sábado" |
| 12 | **Spikes antes de código** + pedir a revisão da Meta no dia 0 | A aprovação da Meta leva semanas e é o caminho crítico do bot |

## As 5 decisões que mais pesam (detalhes em [11](11-decisoes-adrs.md))

1. **Monólito modular + workers**, não microsserviços. Um dev, um `docker compose`.
2. **Python/FastAPI** (IA e API) + **Next.js** (site/galeria white-label) + **Postgres com pgvector**.
3. **Motor facial escolhido por benchmark** com fotos reais da CBDE (Spike S1): candidatos InsightFace licenciado, OpenCV YuNet+SFace (Apache 2.0) e Amazon Rekognition.
4. **Instagram pela "Instagram API com Instagram Login"**, um único app Meta (Tech Provider) atendendo todos os clientes.
5. **Cliente = controlador, FLASH! = operador** (LGPD), com consentimento do responsável embutido na inscrição do evento.

## O que fazer primeiro (próximas 2 semanas)

1. **Dia 0:** abrir o app Meta, iniciar **Business Verification** e preparar o *App Review* (vai levar semanas — [05](05-instagram-bot.md)).
2. **Dia 0:** consultar um advogado de proteção de dados sobre o texto de consentimento e o papel de operador ([07](07-seguranca-lgpd-abuso.md)); registrar/pesquisar o nome "FLASH!" no INPI (nome genérico, há risco de conflito).
3. **Semana 1:** montar o **conjunto-ouro** (golden set): ~30 atletas rotulados em ~1.500 fotos reais de um evento CBDE — é o ativo mais valioso do projeto, porque decide motor, limiares e qualidade ([04](04-reconhecimento-facial.md)).
4. **Semana 1–2:** rodar os **spikes S1–S6** ([09](09-roadmap-e-backlog.md)). Só depois do Go/No-Go começa a Fase 1.

## Convenções

- **Verificado** = conferi em fonte oficial em out/2026. **Estimativa** = cálculo meu, a validar. **Hipótese** = precisa de spike.
- Preços em US$ são de tabela pública; em R$ são estimativas sem câmbio fixo. Reconfirme antes de assumir compromisso.
- Nada aqui é parecer jurídico. A parte de LGPD é um mapa de riscos para levar ao advogado.
