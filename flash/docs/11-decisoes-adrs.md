# 11 · Registro de decisões (ADRs)

Formato: **Contexto → Decisão → Consequências → Alternativas**. Estado: *Proposta* (aguarda spike) ou *Aceita*. Mudou? Crie um ADR novo que "substitui" o anterior; não reescreva a história.

---

### ADR-001 · Monólito modular com workers
**Estado:** Aceita. **Contexto:** um mantenedor, custo baixo, evolução rápida. **Decisão:** um código-base com módulos (`ingest`, `faces`, `search`, `bot`, `delivery`, `tenancy`, `billing`) e processos distintos (api, worker-ingest, worker-bot). **Consequências:** deploy e depuração simples; fronteiras explícitas permitem extrair serviços depois. **Alternativas:** microsserviços (custo operacional alto sem benefício), *serverless* total (frio, limites de CPU/tempo para ML).

### ADR-002 · Python/FastAPI no back-end; Next.js no front-end
**Estado:** Aceita. **Contexto:** ecossistema de visão computacional é Python (ONNX Runtime, OpenCV, pyvips); UI white-label rica e SEO de galeria pedem React. **Decisão:** FastAPI + Pydantic; Next.js (App Router) + Tailwind. **Consequências:** duas linguagens; contrato OpenAPI gera tipos TypeScript. **Alternativas:** tudo em Node (bindings de ML piores), tudo em Python/HTMX (UI limitada para câmera/PWA).

### ADR-003 · PostgreSQL único: dados + pgvector + fila
**Estado:** Aceita (reavaliar a >1 M rostos/evento). **Decisão:** Postgres 16 com `pgvector`, fila via biblioteca sobre Postgres (`SKIP LOCKED`), sessões do bot em tabela com TTL. **Consequências:** um serviço para operar, backup único, transações atômicas entre estado e fila. **Alternativas:** Redis + Qdrant + RabbitMQ (mais peças, mais custo, mais falhas).

### ADR-004 · `FaceEngine` plugável; motor escolhido por benchmark
**Estado:** Proposta (Spike S1). **Contexto:** modelos de alta precisão populares têm **licença não comercial** (InsightFace `buffalo_l`); alternativas Apache 2.0 (OpenCV YuNet+SFace) e serviço gerenciado (Rekognition) existem. **Decisão:** interface única; `index_version` por evento; adaptadores para SFace, Rekognition e (se licenciado) InsightFace; decisão final pelo golden set. **Consequências:** custo de abstração pequeno; troca por configuração; reindexação necessária ao trocar. **Alternativas:** fixar um motor (risco de licença e lock-in).

### ADR-005 · Busca vetorial exata com filtro por evento; HNSW depois
**Estado:** Aceita. **Contexto:** eventos têm 10 mil–500 mil rostos; consultas filtradas por evento. **Decisão:** varredura exata (cosseno) com `event_id` indexado; criar HNSW apenas acima de ~500 mil rostos por evento. **Consequências:** *recall* 100%, sem afinação; latência a medir (S5). **Alternativas:** HNSW/IVF desde o início (complexidade e perda de recall com filtros), serviço de vetores.

### ADR-006 · Originais no Drive; previews no R2; sem cópia dos originais
**Estado:** Aceita. **Decisão:** fonte da verdade é o Drive do cliente; geramos 1600 px e 400 px no Cloudflare R2 (egress zero) servidos por CDN; original por *streaming* sob demanda (ou link do Drive se o cliente escolher). **Consequências:** custo de armazenamento ≈ 0; dependência da cota do Drive para downloads HD (S3). **Alternativas:** copiar tudo (caro), servir só do Drive (lento, exposição).

### ADR-007 · Conexão ao Drive via conta de serviço
**Estado:** Aceita (validar em S3). **Contexto:** OAuth com escopo `drive.readonly` é "restrito" e exige verificação/auditoria de segurança do Google. **Decisão:** cliente compartilha a pasta com o e-mail do FLASH! (leitor); sem OAuth do usuário. **Consequências:** onboarding de 1 passo; acesso limitado ao que foi compartilhado (bom para privacidade). **Alternativas:** OAuth por cliente (fricção e auditoria), Google Picker.

### ADR-008 · Selfie nunca persiste; só o vetor, com TTL
**Estado:** Aceita. **Decisão:** processar em memória, extrair *embedding*, descartar imagem; vetor em sessão (bot) por ≤ 24 h. **Consequências:** menor risco LGPD; impossível reprocessar a selfie com outro motor (pedir nova). **Alternativas:** guardar selfies (risco alto, sem ganho de produto).

### ADR-009 · Instagram API com Instagram Login; um app Meta para todos
**Estado:** Aceita (S4 confirma detalhes). **Decisão:** app único (Tech Provider) com Advanced Access às permissões de mensagens; cada cliente conecta via OAuth. **Consequências:** exige App Review + Business Verification (caminho crítico); onboarding simples do cliente. **Alternativas:** Facebook Login (exige Página), um app por cliente (insustentável), ferramentas de terceiros (dependência e mais um operador de dados).

### ADR-010 · Follow gate depois da busca, com botão de reverificação
**Estado:** Aceita. **Decisão:** buscar → mostrar quantidade → exigir seguir → checar `is_user_follow_business` a cada toque em "Já segui" → entregar. **Consequências:** conversão maior; zero tarefas agendadas; janela de 24 h renovada pelo toque. **Alternativas:** gate antes da selfie (menos compromisso), polling (impossível fora da janela, gera spam).

### ADR-011 · Entrega no Direct: melhores 20 + link da galeria
**Estado:** Aceita. **Decisão:** 2 mensagens × 10 imagens (≤ 1 MB cada) e *magic link*. **Consequências:** boa experiência, respeita limites e evita aparência de spam. **Alternativas:** enviar tudo (lento/ban), só link (perde o efeito "uau" no Direct).

### ADR-012 · Multi-tenant com esquema compartilhado + RLS
**Estado:** Aceita. **Decisão:** `tenant_id` em todas as tabelas, RLS, testes de isolamento. **Consequências:** barato e simples; risco de bug de política mitigado por testes. **Alternativas:** banco por cliente (custo/ops), esquema por cliente (migrações pesadas).

### ADR-013 · Fluxos, textos e limiares como configuração versionada
**Estado:** Aceita. **Decisão:** JSON validado por esquema; catálogo de mensagens; editor no painel. **Consequências:** customização sem código; testes de fluxo contra fixtures. **Alternativas:** código por cliente (fork, dívida).

### ADR-014 · Hospedagem em VPS no Brasil + Cloudflare
**Estado:** Proposta (S6). **Decisão:** Docker Compose em VPS brasileira; Cloudflare para DNS/CDN/R2/Turnstile. **Consequências:** custo baixo, LGPD mais simples; operação manual de patches/backup. **Alternativas:** Kubernetes/serviços gerenciados (caros demais agora), PaaS (Render/Fly: bom para início, mas ML e egress custam).

### ADR-015 · Privacidade por padrão para eventos com menores
**Estado:** Aceita. **Decisão:** `has_minors=true` por padrão; código do evento, limites de busca, retenção curta, sem listagem de pessoas; afrouxar exige ato consciente do cliente com registro. **Consequências:** menor *recall*/atrito em troca de segurança jurídica e ética. **Alternativas:** busca aberta (risco inaceitável).

### ADR-016 · Dados e jobs idempotentes
**Estado:** Aceita. **Decisão:** chave `(event_id, drive_file_id, md5)`; jobs repetíveis sem efeito colateral; reindexação por `index_version`. **Consequências:** robustez a falhas e reprocessos baratos.

### ADR-017 · Observabilidade desde o dia 1, sem custo
**Estado:** Aceita. **Decisão:** logs JSON, Sentry free, Uptime Kuma, métricas de negócio via `usage_meter`. **Consequências:** operação confiável sem time de SRE.

---

## Revisões de 22/10/2026 (início da construção)

### ADR-018 · Primeira entrega sem Instagram, mas "channel-ready"
**Estado:** Aceita. **Contexto:** o dono decidiu começar pelo site; o bot vem depois e a aprovação da Meta é lenta. **Decisão:** o domínio não conhece canais. Existe `SearchService` (selfie → resultado) e uma interface `Channel` (`web` hoje, `instagram` depois). Estado de conversa, consentimento e `subject_ref` já são modelados de forma neutra ao canal. **Consequências:** o bot vira um adaptador novo, sem mexer em busca, entrega ou dados. **Substitui parcialmente:** ordem de fases do roadmap (Instagram segue na Fase 2, sem bloquear a Fase 1).

### ADR-019 · Google Drive é o único armazenamento permanente
**Estado:** Aceita. **Contexto:** o dono tem espaço de sobra no Drive. **Decisão:** originais **e** qualquer arquivo permanente vivem no Drive. O servidor guarda apenas o **que é regenerável**: índice (banco) e derivados (miniatura 400 px, preview 1600 px) em um repositório de derivados com interface `DerivativeStore` (`local` hoje; `drive`/R2/S3 depois). **Consequências:** perder o servidor não perde fotos; reindexar a partir do Drive reconstrói tudo. Servir previews pelo nosso servidor (com cache em disco) evita depender de cotas do Drive em picos. **Substitui:** ADR-006 (R2 deixa de ser obrigatório; vira opção de escala).

### ADR-020 · Banco: SQLite no desenvolvimento, PostgreSQL em produção; busca vetorial atrás de interface
**Estado:** Aceita. **Contexto:** a máquina de desenvolvimento não tem Docker nem Postgres e o objetivo é começar rápido. **Decisão:** SQLAlchemy 2 com um único modelo de dados; `VectorIndex` com implementação `NumpyIndex` (matriz em memória por evento, busca exata, vetores `float16` no banco) e implementação `PgVectorIndex` quando a escala pedir. Fila de jobs em tabela própria, com reserva atômica (funciona em SQLite e Postgres). **Consequências:** zero instalação local; produção segue com Postgres. **Substitui:** ADR-003 na parte de "pgvector desde o MVP".

### ADR-021 · Front-end: SPA Vite + React + TypeScript (sem Next.js)
**Estado:** Aceita. **Contexto:** galeria é privada (sem SEO), o tema é carregado por tenant em tempo de execução e a hospedagem estática é a mais barata. **Decisão:** Vite + React + Tailwind, servido como arquivos estáticos pelo proxy (ou pelo próprio FastAPI no início). **Consequências:** menos peças, deploy trivial, PWA simples. **Substitui:** parte do ADR-002.

### ADR-023 · Hospedagem: piloto no Mac com túnel; produção em VPS no Brasil
**Estado:** Proposta (23/10/2026). **Contexto:** o plano HostGator compartilhado não roda Python. **Decisão:** piloto com Cloudflare Tunnel; produção em VPS com root no Brasil (HostGator VPS como primeira opção; Hostinger KVM e Fly.io/gru como alternativas). Detalhes e fontes em `13-hospedagem.md`. **Consequências:** custo estimado R$ 60–180/mês; plano exato e preço de renovação a confirmar na contratação.

### ADR-022 · Motor facial inicial: OpenCV YuNet + SFace (Apache 2.0)
**Estado:** Aceita para o desenvolvimento; confirmação final pelo benchmark S1. **Decisão:** `cv2.FaceDetectorYN` + `cv2.FaceRecognizerSF`, sem dependências extras; modelos baixados por script com SHA-256 registrado. **Consequências:** licença limpa e instalação trivial; precisão em esporte a medir; vetor de 128 dimensões (cabe em RAM com folga).

---

## Decisões em aberto (a fechar nos spikes)

| Tema | Spike | Dono |
|------|-------|------|
| Motor facial padrão | S1 | Allisson |
| Original vs. miniatura grande do Drive | S3 | Allisson |
| Piloto sem App Review | S4 | Allisson |
| Provedor da VPS | S6 | Allisson |
| Política de idade (<12, 12–17) | Jurídico | Advogado |
| Preço dos planos | Pesquisa com clientes | Allisson |
| Nome definitivo/marca | INPI | Allisson |
