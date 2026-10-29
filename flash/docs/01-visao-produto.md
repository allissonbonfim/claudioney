# 01 · Visão do produto

## 1. Problema

Em eventos como os da CBDE, a equipe de fotografia produz **milhares de imagens**. Hoje:

- Só um *select* pequeno vai para as redes, rápido; a "grande massa" demora a subir.
- Quando sobe, está num Drive: o estudante-atleta precisa **garimpar** centenas de fotos para achar as dele.
- Resultado: baixa percepção de valor do trabalho fotográfico, fotos que nunca são vistas, perda de engajamento e de oportunidade de divulgação orgânica.

O problema se repete em qualquer evento com muito público fotografado: corridas, formaturas, torneios, festivais, convenções, casamentos, escolas.

## 2. Proposta de valor

> **"Tirou a selfie, achou todas as suas fotos."**  Em segundos, sem garimpar, sem baixar pasta de 40 GB.

| Para quem | Valor |
|-----------|-------|
| **Participante** (atleta, aluno, convidado) | Acha e baixa as próprias fotos em segundos, pelo canal que já usa (Instagram ou site) |
| **Cliente-organizador** (CBDE, federação, escola, produtora) | Cada foto vira conteúdo compartilhado pelo participante; ganha seguidores; zero trabalho manual de "me manda minhas fotos" |
| **Fotógrafo / equipe** | Sobe tudo no Drive como sempre; não organiza nada por pessoa |
| **Você (Bom&fim)** | Produto recorrente e revendável, custo marginal por evento próximo de zero |

### Diferenciais pretendidos (a validar contra concorrentes)

1. **Instagram-first:** a entrega acontece onde o público já está (Direct), com **follow gate** que transforma cada entrega em novo seguidor para o cliente.
2. **Drive-native:** o fluxo do fotógrafo não muda. Nada de novo painel de upload.
3. **Barato de operar:** indexação em CPU comum ou API a ~US$ 1 por mil imagens; fotos pesadas ficam no Drive.
4. **White-label real:** domínio, cores, textos, fluxo do bot e regras por cliente, sem programar.
5. **Privacidade como recurso de venda:** selfie nunca armazenada, retenção configurável, apagamento sob demanda, modo para menores.

## 3. Personas

| Persona | Contexto | Necessidade-chave |
|---------|----------|-------------------|
| **Bia, 16 anos, atleta** | Celular, Instagram o dia todo, pouca paciência | Pedir foto com 3 toques; receber no Direct |
| **Sr. Carlos, pai** | Quer fotos do filho, menos íntimo com tecnologia | Link simples, download em lote |
| **Dani, coordenadora de comunicação (cliente)** | Precisa mostrar resultado ao presidente | Painel: quantas buscas, novos seguidores, fotos mais baixadas |
| **Léo, fotógrafo** | Sobe 6.000 fotos à noite | Saber que "o sistema já leu minhas fotos" e quantas faltam |
| **Allisson, operador da Bom&fim** | Gerencia vários clientes e eventos | Criar evento em 5 min; ver custo e uso por cliente |
| **Titular de dados / responsável legal** | Aparece nas fotos | Poder pedir remoção e entender o que acontece com seu rosto |

## 4. Escopo

### Dentro (MVP + evolução prevista)

- Conexão com Google Drive (pasta do evento) e indexação automática, contínua durante o evento.
- Busca por selfie via **site/PWA** e via **Direct do Instagram**.
- Entrega: galeria com *previews*, download individual, ZIP de todas, entrega das melhores no Direct.
- *Follow gate* configurável.
- Painel do operador/cliente (eventos, status de indexação, métricas, moderação, remoção).
- Multi-cliente (tenants) e white-label.
- Controles de privacidade e anti-abuso.

### Fora (por ora, explicitamente)

- Venda de fotos / checkout (candidato à Fase 5, via PIX).
- Edição ou tratamento de imagens.
- Reconhecimento de pessoas **sem** selfie (ex.: "listar todos que aparecem").
- Uso para vigilância, controle de acesso, identificação de terceiros fora do evento.
- App nativo (PWA cobre).
- Moderação automática de conteúdo impróprio (tratar manualmente no MVP).

## 5. Métricas de sucesso

**Produto (North Star: *fotos entregues por atleta*)**

| Métrica | Meta MVP | Como medir |
|---------|----------|-----------|
| Taxa de sucesso da busca (≥ 1 foto encontrada) | ≥ 90% dos participantes reais | `search.results_count > 0` |
| Precisão das fotos entregues "com certeza" | ≥ 98% | Auditoria amostral + golden set |
| Recall (fotos do atleta realmente encontradas, rosto ≥ 60 px) | ≥ 90% | Golden set |
| Tempo da selfie ao primeiro resultado | ≤ 5 s (site) · ≤ 15 s (Direct) | Telemetria |
| Conversão do *follow gate* | ≥ 60% dos que chegam ao gate seguem | Funil do bot |
| Atraso até a foto ficar pesquisável | ≤ 10 min da subida no Drive (ritmo normal) | `indexed_at − drive_created_at` |

**Negócio**

| Métrica | Meta |
|---------|------|
| Custo variável por evento de 20 mil fotos | < R$ 150 (ideal < R$ 50) |
| Tempo de configuração de um novo evento | ≤ 10 min |
| Margem bruta por evento vendido | ≥ 85% |
| Clientes pagantes no 12º mês | 5–10 (hipótese, validar) |

## 6. Modelo de negócio (hipóteses)

| Modelo | Descrição | Quando |
|--------|-----------|--------|
| **Por evento** | Pacote por faixa de fotos (ex.: até 5k / 20k / 50k) com taxa de implantação | MVP, mais simples de vender |
| **Assinatura** | Mensalidade com N eventos/mês incluídos + excedente | Clientes recorrentes (CBDE, federações) |
| **White-label premium** | Domínio próprio + Instagram próprio + SLA | Upsell |
| **Revenda de fotos** | Comissão sobre venda de fotos individuais | Fase 5 |

Preços e custos em [08](08-custos-e-precificacao.md).

## 7. Concorrência (levantamento inicial, a aprofundar)

Encontrei plataformas que fazem "selfie → suas fotos": **OPIC, Supa Waldo, Kamero, Gatherpro, Facialprint**, e, no Brasil esportivo, a **Fotop**, que usa reconhecimento facial desde 2016 e entrega fotos também via WhatsApp (fonte: matéria do Máquina do Esporte, via busca). A maioria exige que o fotógrafo suba as fotos na plataforma deles e cobra por foto ou assinatura.

**Tarefa:** montar uma planilha com 8–10 concorrentes (preço, canal de entrega, white-label, política de privacidade, Drive?, Instagram?) antes de fixar preço. Prazo: Semana 2.

## 8. Premissas e dependências

- O cliente tem (ou cria) conta **Instagram Profissional** (Business/Creator) — requisito para a API de mensagens.
- O cliente compartilha a pasta do evento no Drive com o FLASH!.
- O cliente obtém consentimento dos responsáveis na inscrição (modelo fornecido por você, revisado por advogado).
- A Meta aprova o app para uso em produção (caminho crítico).

## 9. Riscos de alto nível

Registro completo em [09](09-roadmap-e-backlog.md#riscos). Os quatro que podem matar o projeto:

1. **Jurídico/LGPD:** biometria de menores. → [07](07-seguranca-lgpd-abuso.md)
2. **Aprovação da Meta** atrasar ou ser negada. → plano B: ManyChat/Chatwoot como ponte; WhatsApp.
3. **Precisão ruim em esporte** (capacete, movimento, rostos pequenos). → golden set e clusters.
4. **Licença do modelo facial.** → `FaceEngine` plugável e benchmark.
