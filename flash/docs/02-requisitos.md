# 02 · Requisitos

Prioridade: **M** = Must (MVP) · **S** = Should (Fase 2–3) · **C** = Could (depois).

## 1. Épicos e histórias

### E1 — Conexão e ingestão (Drive)

| ID | História | Prio | Critérios de aceite |
|----|----------|------|---------------------|
| E1.1 | Como operador, crio um evento e conecto uma pasta do Drive compartilhando-a com o e-mail da conta de serviço do FLASH! | M | Dado o link da pasta, o sistema valida acesso, lista subpastas e mostra "N imagens encontradas" em ≤ 30 s |
| E1.2 | Como fotógrafo, subo fotos e elas são indexadas sem eu fazer nada | M | Foto nova fica pesquisável em ≤ 10 min (carga normal); status visível no painel |
| E1.3 | Como operador, vejo o progresso da indexação | M | Painel mostra descobertas / processadas / com erro / rostos detectados; erros listam motivo |
| E1.4 | Como sistema, não reprocesso fotos já lidas | M | Chave idempotente = `drive_file_id + md5Checksum`; renomear/mover não reindexa; substituir conteúdo reindexa |
| E1.5 | Como operador, uso o nome das subpastas como facetas (ex.: `Sábado/Vôlei/Quadra 2`) | S | Estrutura de pastas vira `dia`, `modalidade`, `local` configuráveis; filtro disponível na galeria |
| E1.6 | Como operador, reprocesso um evento com outro motor/limiar | S | Reindexação em background sem derrubar buscas (versão de índice) |
| E1.7 | Como operador, excluo fotos do índice | M | Foto marcada como "oculta" some de todas as buscas imediatamente |
| E1.8 | Suporte a outras fontes (Dropbox, S3/R2, upload direto) | C | Interface `SourceConnector` já prevista |

### E2 — Busca por selfie (site)

| ID | História | Prio | Critérios de aceite |
|----|----------|------|---------------------|
| E2.1 | Como participante, abro o site do cliente, escolho o evento | M | Lista só eventos ativos do tenant; link direto `/e/{slug}` e QR code |
| E2.2 | Tiro uma selfie com a câmera do celular | M | Guia na tela (rosto no círculo, boa luz); validação no aparelho: exatamente 1 rosto, nitidez e tamanho mínimos; mensagens claras |
| E2.3 | Posso enviar uma foto da galeria como alternativa | M | Aceita JPEG/PNG/HEIC ≤ 10 MB; se detectar ≠ 1 rosto, pede outra |
| E2.4 | Recebo as fotos ordenadas por confiança/qualidade | M | Primeiros resultados em ≤ 5 s; paginação; separação "Com certeza" × "Talvez sejam você" |
| E2.5 | Posso enviar 2–3 selfies para melhorar o resultado | S | Busca multi-consulta (união ponderada) |
| E2.6 | Vejo "pessoas parecidas" e escolho qual sou | S | Mostra até 3 clusters candidatos com miniaturas do rosto; escolher libera todas as fotos do cluster |
| E2.7 | Filtro por faceta (dia, modalidade) | S | Filtros combináveis |
| E2.8 | Baixo uma foto, várias ou todas (ZIP) | M | ZIP gerado em *streaming* (sem arquivo temporário), nome de arquivo legível |
| E2.9 | Compartilho uma foto nas redes | S | Botão de compartilhar nativo (Web Share API) com *preview* com marca d'água opcional |
| E2.10 | Marco "esta não sou eu" / "pedir remoção desta foto" | M | Registra feedback (alimenta calibração) e remoção em ≤ 24 h (automática se for o próprio rosto confirmado) |

### E3 — Bot do Instagram

| ID | História | Prio | Critérios de aceite |
|----|----------|------|---------------------|
| E3.1 | Como participante, mando "Quero minha foto" no Direct e o bot responde | M | Reconhece variações (sem acento, caixa, "quero minhas fotos", "foto"); responde em ≤ 3 s |
| E3.2 | Também por comentário em post específico | S | Comentário com palavra-chave dispara *private reply* (limite 750/h por conta, uma por comentário, em até 7 dias) |
| E3.3 | Bot mostra termos/consentimento de forma curta antes de pedir selfie | M | Aceite registrado (versão do texto, data/hora, ID do usuário) |
| E3.4 | Bot pergunta qual evento (botões) | M | Até 13 *quick replies* ou carrossel; se só há 1 evento ativo, pula a pergunta |
| E3.5 | Bot pede a selfie e valida | M | Imagem recebida → detecta rosto → se inválida, explica e pede outra (máx. 3 tentativas) |
| E3.6 | Bot busca e informa "achei N fotos" **antes** do gate | M | Mensagem com número e teaser (1 foto borrada/miniatura opcional) |
| E3.7 | *Follow gate*: só entrega se o usuário segue o perfil | M | Consulta `is_user_follow_business`; se não segue, pede e oferece botão "Já segui ✅"; cada toque rechecaa; limite de 5 tentativas e mensagem gentil de encerramento |
| E3.8 | Bot entrega as melhores fotos no Direct e o link da galeria | M | Até 10 imagens por mensagem, 2 mensagens; cada imagem ≤ 8 MB; link com *magic link* expirável |
| E3.9 | Bot trata fora do fluxo (texto livre, áudio, figurinha) | M | Responde com menu; nunca "trava" |
| E3.10 | Handoff para humano | S | Palavra "atendente" encaminha para caixa de entrada do cliente e silencia o bot por 24 h |
| E3.11 | Pesquisa de satisfação ao final | S | 👍/👎 e comentário opcional |
| E3.12 | Canal WhatsApp | C | Mesmo motor de fluxo, outro adaptador |

### E4 — Painel (operador e cliente)

| ID | História | Prio | Critérios de aceite |
|----|----------|------|---------------------|
| E4.1 | Login seguro (e-mail + senha/Magic link; 2FA depois) | M | Papéis: Dono (Bom&fim), Admin do cliente, Operador de evento, Leitura |
| E4.2 | Criar/editar evento, janela de datas, políticas de privacidade, tema | M | Evento tem estados: rascunho → indexando → aberto → encerrado → arquivado |
| E4.3 | Conectar Instagram do cliente (OAuth) | M | Fluxo guiado; mostra validade do token e alerta de expiração |
| E4.4 | Métricas do evento | M | Buscas, taxa de sucesso, fotos entregues, novos seguidores, downloads, horário de pico |
| E4.5 | Editor de fluxo do bot (textos, ordem, ligar/desligar gate) | S | Formulário simples, pré-visualização; sem JSON cru para o cliente |
| E4.6 | Moderação: ocultar foto, bloquear usuário, atender pedidos de remoção | M | Fila de pedidos com prazo |
| E4.7 | Exportar relatório do evento (PDF/CSV) | S | Pronto para o cliente prestar contas |
| E4.8 | Faturamento por uso | S | Medição por evento (fotos, buscas, mensagens) |

### E5 — Privacidade e conformidade

| ID | História | Prio | Critérios de aceite |
|----|----------|------|---------------------|
| E5.1 | Selfie nunca persiste | M | Imagem descartada após extrair o *embedding*; teste automatizado garante que nenhuma rota salva o *upload* |
| E5.2 | Retenção configurável | M | Padrão: *embeddings* de rostos apagados 90 dias após o encerramento do evento; job de purga com log |
| E5.3 | Direito de apagamento | M | Formulário/Bot "apagar meus dados" remove embeddings da pessoa e histórico de buscas; prazo ≤ 15 dias (meta: imediato) |
| E5.4 | Registro de consentimento | M | Imutável, versionado |
| E5.5 | Modo menores (código do evento, limite de buscas, sem busca livre) | M | Configurável por evento; padrão **ligado** quando o evento declara menores |
| E5.6 | Log de auditoria | M | Quem buscou o quê (sem imagem), quando, de onde; acessível ao DPO |

## 2. Requisitos não funcionais

| Categoria | Requisito | Meta |
|-----------|-----------|------|
| **Desempenho** | Busca por selfie (servidor) | p95 ≤ 1,5 s só a etapa de busca; ≤ 5 s ponta a ponta no site |
| | Vazão de indexação | ≥ 60 fotos/min por vCPU (2048 px); evento de 20 mil fotos em < 2 h com 4 vCPU |
| | Pico de buscas | 300 buscas/min sustentadas, 1.000 simultâneas no encerramento do evento sem degradar além de 2× |
| **Disponibilidade** | SLO | 99,5% mensal; **99,9% durante janela de evento** (o resto do mês pode ter manutenção) |
| **Escalabilidade** | Rostos por evento | até 2 milhões sem trocar de arquitetura |
| | Tenants | 100 no MVP de multi-cliente, sem mudar o banco |
| **Custo** | Infra fixa mensal | < R$ 300 com até 5 clientes ativos (alvo) |
| **Segurança** | Segredos | Tokens (Instagram, Drive) criptografados em repouso, rotacionáveis |
| | Isolamento | Row-Level Security por tenant; testes de vazamento entre tenants |
| **Privacidade** | Minimização | Ver E5; sem imagens de selfie, sem biometria desnecessária |
| **Observabilidade** | | Logs estruturados, métricas, traços das filas, alertas por Telegram/e-mail |
| **Manutenibilidade** | | Cobertura de testes ≥ 70% no núcleo; ADRs atualizados; CI verde obrigatório |
| **Acessibilidade** | | WCAG 2.1 AA no site; texto alternativo; contraste |
| **i18n** | | pt-BR primeiro; estrutura pronta para en/es |
| **Portabilidade** | | Sem dependência de provedor: Docker; objetos S3-compatíveis; troca de motor facial por configuração |
| **Compatibilidade** | | Safari iOS 16+, Chrome Android 10+; câmera via `getUserMedia` com *fallback* de upload |

## 3. Regras de negócio

- **RN1.** Toda foto pertence a um evento; todo evento a um tenant. Nenhum dado cruza tenants.
- **RN2.** Resultado "Com certeza" exige similaridade ≥ `τ_alto` do motor ativo; "Talvez" entre `τ_baixo` e `τ_alto`. Limiares ficam em configuração do evento, com valores iniciais calibrados no golden set.
- **RN3.** Rosto com qualidade abaixo do mínimo (tamanho < 40 px de lado, nitidez baixa, pose > 60°) é **indexado marcado como "baixa qualidade"** e só aparece em "Talvez".
- **RN4.** O *follow gate* é opcional por evento. Se ligado, nenhuma foto é enviada (nem link) antes da confirmação; o teaser só mostra **quantidade**.
- **RN5.** O link da galeria é um *magic link* assinado, vinculado ao resultado da busca, com validade configurável (padrão 30 dias) e revogável.
- **RN6.** Eventos com menores exigem: código do evento, limite de 10 buscas/usuário/dia, sem listagem de "pessoas", entrega só do resultado da própria busca.
- **RN7.** A selfie nunca é registrada, nem em log. Apenas o *embedding* vive em memória/sessão por no máximo 24 h.
- **RN8.** Pedido de remoção de um titular oculta a foto de todas as buscas imediatamente; a decisão final é humana em até 24 h.
- **RN9.** Fotos que o fotógrafo marcar como "pasta privada" (ex.: nome `_nao_publicar`) não são indexadas.
- **RN10.** O tenant só consome sua cota; excedente gera alerta, não interrupção durante o evento.
