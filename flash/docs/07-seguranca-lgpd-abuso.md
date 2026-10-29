# 07 · Segurança, LGPD e abuso

> **Aviso:** este documento é um mapa de riscos e de controles técnicos, não parecer jurídico. Leve-o a um advogado de proteção de dados **antes do piloto**. O ponto é crítico: o público-alvo inicial (estudantes-atletas) é majoritariamente menor de idade e o dado tratado é biométrico.

## 1. Por que é o maior risco do projeto

1. **Rosto e *embedding* são dado pessoal sensível** (biometria, LGPD art. 5º, II e art. 11). Não existe "legítimo interesse" como base legal para dado sensível; as bases são limitadas (consentimento específico e destacado, ou as hipóteses do art. 11, II).
2. **Crianças e adolescentes** (art. 14): tratamento no melhor interesse do menor; para crianças, consentimento específico de ao menos um dos pais/responsável.
3. **A ANPD está atenta ao tema.** Em 2026, a ANPD determinou a suspensão do uso de biometria/reconhecimento facial de estudantes da rede estadual do Paraná para controle de frequência (Nota Técnica nº 4/2026), apontando hipótese legal inadequada, falta de necessidade/proporcionalidade e existência de meios menos invasivos; reforçou que a base legal deve ser definida **antes** do início do tratamento. A agenda regulatória 2026–27 prioriza crianças no ambiente digital. O caso é de finalidade diferente (frequência escolar), mas mostra o rigor esperado. (Fontes: Felsberg Advogados; Tribuna do Paraná; Convergência Digital; MobileTime.)
4. **Risco de produto:** uma ferramenta que acha todas as fotos de um rosto pode ser usada para **localizar uma criança específica**. É risco reputacional e potencialmente criminal para o cliente e para você.

## 2. Papéis (modelo recomendado)

| Papel | Quem | Responsabilidades |
|-------|------|-------------------|
| **Controlador** | O cliente (ex.: CBDE) | Define a finalidade, obtém consentimento dos responsáveis na inscrição, responde ao titular, nomeia encarregado (DPO) |
| **Operador** | Bom&fim / FLASH! | Trata dados conforme instruções do cliente, aplica medidas de segurança, comunica incidentes |
| **Suboperadores** | Meta (Instagram), Google (Drive), Cloudflare, provedor de VPS, AWS (se Rekognition) | Listados no contrato; avaliar transferência internacional (art. 33) |

Formalizar com **Contrato de tratamento de dados (DPA)** entre FLASH! e cada cliente, com anexo de medidas de segurança e lista de suboperadores.

## 3. Bases legais e consentimento (para validar com o advogado)

| Tratamento | Possível base | Como operacionalizar |
|------------|---------------|----------------------|
| Indexar rostos das fotos do evento | Consentimento específico e destacado do titular (ou do responsável, se menor), coletado **na inscrição** do evento, com finalidade clara: "localizar suas fotos" | Cláusula/aceite separado no termo de inscrição: texto fornecido por você e revisado; o cliente guarda a prova |
| Processar a selfie para buscar | Consentimento no momento do uso (site/bot) | Aceite com versão do texto; registrado em `consent_log` |
| Menores | Consentimento de responsável + melhor interesse | Para <12 anos exigir, na prática, o responsável; para 12–17, recomendar ciência do responsável e opção de modo restrito. **Definir com o advogado a política de idade** |
| Segurança e prevenção a abuso | Obrigação/prevenção a fraude (verificar) | Registros mínimos, sem imagens |

**Pontos de atenção:**

- Pessoas que **aparecem nas fotos mas não foram inscritas** (público, árbitros, familiares): o consentimento do inscrito não cobre. Opções: restringir a indexação ao que o cliente comprovar cobrir; oferecer opt-out simples; avaliar *blur/omissão* de rostos fora da base; ou limitar o produto a eventos com credenciamento prévio.
- **Relatório de Impacto à Proteção de Dados (RIPD)** é fortemente recomendado (e pode ser exigido): fazer um modelo reutilizável para os clientes.
- **Encarregado (DPO)** do cliente e canal do titular na página do evento.

## 4. Privacidade por padrão (controles técnicos)

| Controle | Implementação |
|----------|---------------|
| **Selfie nunca persiste** | Lida em memória, vetor extraído, imagem descartada; testes automatizados garantem que nenhuma rota grava o *upload*; logs sem corpo de requisição |
| **Vetor da selfie com TTL** | Sessão do bot ≤ 24 h, criptografado; busca web: não guardado |
| **Retenção dos vetores do evento** | Padrão 90 dias após encerrar (configurável por contrato); depois purga; fotos continuam, vetores não |
| **Minimização** | Não coletar nome/telefone/e-mail para buscar; `subject_ref` = HMAC do IGSID/dispositivo |
| **Apagamento** | Fluxo "apagar meus dados" no bot e no site; remove sessão, buscas e, se identificado cluster próprio e confirmado, os vetores; prazo-meta imediato, máximo 15 dias |
| **Remoção de foto** | Qualquer pessoa pode pedir; foto fica oculta imediatamente; decisão humana em 24 h |
| **Criptografia** | TLS 1.2+; discos criptografados; tokens e vetores de sessão cifrados em nível de aplicação (AES-GCM, chave fora do banco) |
| **Isolamento** | RLS por tenant; testes que tentam ler dados de outro tenant devem falhar |
| **Acesso mínimo** | Papéis; ninguém da equipe navega rostos por curiosidade; acesso a golden set auditado |
| **Trilha de auditoria** | Quem consultou/exportou/apagou o quê |
| **Incidentes** | Plano de resposta com prazos de comunicação à ANPD e aos titulares |
| **Localização** | Preferir hospedagem no Brasil; Rekognition só com análise da transferência internacional |

## 5. Modelo de ameaças de abuso

| Ameaça | Cenário | Mitigações |
|--------|---------|-----------|
| **Rastrear uma criança** | Alguém sobe a foto de uma criança que não é sua | Modo menores: código do evento (distribuído a participantes), limite de buscas por usuário/dia, detecção de varredura (muitas faces diferentes do mesmo usuário), liveness-lite (câmera ao vivo no site), bloqueio e revisão manual |
| **Perseguição / stalking** | Terceiro busca uma ex-colega | Idem; entrega só de fotos "Com certeza"; opção de a pessoa se auto-bloquear (opt-out de índice) |
| **Raspagem em massa** | Bot varre a galeria e baixa tudo | Magic links expiram, ZIP com limites, Turnstile, rate limit por IP/dispositivo, URLs de preview assinadas e curtas |
| **Envenenamento de índice** | Fotógrafo sobe fotos fora de contexto | Papéis de upload; pastas privadas ignoradas; moderação |
| **Enumeração de eventos** | Adivinhar slugs | Slugs não sequenciais; eventos privados só com código |
| **Vazamento entre clientes** | Bug de RLS | Testes de isolamento no CI; revisão de queries sem `tenant_id` |
| **Token do Instagram roubado** | Acesso à conta do cliente | Cifra em repouso, escopo mínimo, rotação, revogação pelo painel |
| **Webhook falso** | Alguém forja eventos da Meta | Validação HMAC, rejeição sem assinatura |
| **Prompt/Comando malicioso no DM** | Texto tenta quebrar fluxo | O bot não usa LLM para decisões de segurança; entradas tratadas como dados |

**Princípio:** o produto deve fazer o uso **correto** fácil e o uso abusivo **caro**. Aceitar menos recall em troca de segurança em eventos com menores é decisão de produto, não de engenharia.

## 6. Segurança de aplicação (checklist OWASP)

- [ ] Validação de entrada, tamanho e tipo MIME de todos os uploads (`python-magic`/`libmagic`)
- [ ] Decodificação de imagem com limites (pixels máximos, *bombs*) e em processo com `rlimit`
- [ ] Remoção de EXIF/GPS das imagens que viram preview
- [ ] CSRF, CORS restrito, cabeçalhos de segurança (CSP, HSTS)
- [ ] Dependências fixadas, `pip-audit`/`npm audit`/Dependabot, imagem base mínima
- [ ] Segredos fora do repositório (SOPS/age, `.env` ignorado); varredura de segredos no CI
- [ ] SSRF: o bot baixa imagens por URL da Meta — aceitar apenas domínios da Meta, seguir limites e *timeouts*
- [ ] Logs sem dados pessoais; mascaramento de IGSID
- [ ] Backup criptografado e testado; plano de recuperação (RTO 4 h, RPO 24 h no MVP)
- [ ] Revisão de segurança antes do piloto (`/security-review` e teste manual)

## 7. Documentos que precisam existir (entregáveis jurídicos)

1. Política de Privacidade do FLASH! (operador) e modelo para o cliente (controlador).
2. Termos de Uso do serviço (participante).
3. Texto de consentimento para a inscrição do evento (menores/responsáveis) e versão curta para o bot.
4. DPA FLASH! ↔ cliente + lista de suboperadores.
5. RIPD modelo.
6. Política de retenção e descarte.
7. Procedimento de atendimento a titulares (prazos, responsáveis).
8. Plano de resposta a incidentes.
9. Registro das operações de tratamento (ROPA).

## 8. Posição de produto recomendada

- **Padrão = privacidade máxima:** o evento nasce com `has_minors = true`, código de evento obrigatório e retenção curta. O cliente precisa conscientemente afrouxar.
- **Transparência como argumento comercial:** "FLASH! nunca guarda a selfie; apaga os vetores em 90 dias; o participante pode sumir do evento com um toque".
- **Seguro/ressalvas contratuais:** limitação de responsabilidade, cláusulas de uso aceitável (proibido uso para vigilância), direito de suspender cliente abusivo.
