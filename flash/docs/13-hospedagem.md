# 13 · Hospedagem: onde o FLASH! roda

Pesquisa de 23/10/2026. **Verificado** = li na página oficial do provedor. **Não confirmado** = veio de comparador/blog ou a página não carregou; confira antes de pagar.

## 1. Por que a hospedagem atual não serve

O plano HostGator compartilhado (cPanel) **não tem "Setup Python App"** (registrado em `cbde-youtube/dashboard/README-DEPLOY.md`). Ele serve páginas estáticas e PHP. O FLASH! precisa de Python (FastAPI), do OpenCV, de processos em segundo plano e de disco para as miniaturas. Subir só o site por FTP deixaria uma página sem backend.

O plano compartilhado continua útil para o que já faz (dashboard do YouTube) e pode apontar um subdomínio para o servidor novo (só um registro DNS).

## 2. O que o FLASH! precisa de um servidor

| Item | Mínimo (piloto) | Confortável (vendendo) | Por quê |
|------|-----------------|------------------------|---------|
| Tipo | VPS Linux com **root** | idem | instalar Python, serviços e HTTPS |
| vCPU | 2 | 4 | indexar fotos é CPU (estimativa: ~100–200 fotos/min/vCPU) |
| RAM | 4 GB | 8 GB | busca em memória (128 dimensões × 500 mil rostos ≈ 256 MB) + 4 workers decodificando fotos grandes |
| Disco | 50 GB NVMe | 100–200 GB NVMe | derivados ≈ 0,4 MB/foto → 20 mil fotos ≈ 8 GB; originais ficam no Drive |
| Local | Brasil | Brasil | latência e LGPD (transferência internacional, art. 33) |
| Tráfego | ≥ 1 TB/mês | idem | galeria e ZIP (originais passam pelo servidor) |
| SO | Ubuntu/Debian LTS | idem | `docker compose` ou `systemd` |

Não precisa de GPU. Não precisa de Kubernetes.

## 3. Opções encontradas

| Opção | Plano | Preço | Brasil? | Veredito |
|-------|-------|-------|---------|----------|
| **HostGator VPS (NVMe)** | linha atual com 6 tamanhos (2, 4, 8, 12, 16, 32) | promoção "a partir de R$ 20,99/mês" na página oficial; comparador cita R$ 69,99 promocional no "NVMe 8" (cheio R$ 173) — **não confirmado** | **Sim**: página diz "Servidores Oracle Cloud no Brasil"; guias citam acesso root (**não confirmado** na página) | **Recomendada**: você já é cliente, mesma fatura e painel, DNS no mesmo lugar. Conferir vCPU/RAM do tamanho 8 |
| **Hostinger VPS (KVM)** | KVM 2: 2 vCPU, 8 GB, 100 GB NVMe · KVM 4: 4 vCPU, 16 GB, 200 GB NVMe | KVM 2: R$ 42,99/mês promo, **renova R$ 77,99** · KVM 4: R$ 59,99/mês promo, **renova R$ 149,99** (**verificado**) | **Não confirmado** (página lista 10 data centers, sem mostrar quais) | Melhor custo-benefício no papel; só vale se **São Paulo aparecer no checkout** |
| **Hostzone (São Paulo)** | 4 núcleos/4 GB · 6 núcleos/8 GB | R$ 206 · R$ 320/mês (comparador, **não confirmado**) | Sim, Tier III | Caro para o porte |
| **Vultr (São Paulo)** | 4 vCPU/8 GB | ~US$ 72/mês (comparador, **não confirmado**) | Sim | Caro; bom como plano B com cobrança por hora |
| **Fly.io (gru = São Paulo)** | máquinas por uso: 4 vCPU compartilhados ≈ US$ 7,78 (1 GB) a US$ 22,78 (4 GB); volume US$ 0,15/GB-mês; saída na América do Sul US$ 0,04/GB (**verificado** nos docs; valores variam entre duas cópias da página) | ≈ US$ 25–40/mês no porte do FLASH! | **Sim** (São Paulo existe) | Boa se você não quer administrar servidor; custo de tráfego do ZIP pode crescer |
| **Render** | — | — | **Não** (Oregon, Ohio, Virginia, Frankfurt, Singapura) | Descartado: sem região no Brasil |
| **Hetzner** | a partir de € 5,99 | — | **Não** (Alemanha, Finlândia, Singapura, EUA) | Descartado para dados de menores (LGPD) |
| **Oracle Cloud "Always Free"** | ARM 4 vCPU/24 GB (docs) — duas fontes dizem que caiu para 2/12 em jun/2026, **não confirmado** | R$ 0 | Sim (São Paulo/Vinhedo) | Relatos de **falta de capacidade em São Paulo**; serve de brinde, não de base de negócio |
| **Magalu Cloud** | VMs em R$ | preço **não encontrado** | Sim (Grande SP e Fortaleza) | Vale pedir cotação |
| **Seu Mac + túnel gratuito (Cloudflare Tunnel)** | — | R$ 0 | Sim (seu Mac) | **Melhor para o piloto**: sem contratar nada, mas só no ar com o Mac ligado |

## 4. Recomendação

1. **Piloto (agora):** rodar no seu Mac, com o endereço público por Cloudflare Tunnel (gratuito). Valida tudo com fotos reais sem gastar. Exige que o Mac fique ligado durante o evento.
2. **Produção:** **VPS da HostGator**, tamanho com **≥ 4 vCPU e 8 GB** (ou, no mínimo, 2 vCPU e 4 GB para começar). Antes de pagar, confirme na página de contratação: vCPU, RAM, disco, "acesso root", Ubuntu disponível, preço de **renovação** e servidor no Brasil.
3. **Plano B:** Hostinger KVM 2/4 se o checkout permitir São Paulo; Fly.io em São Paulo se preferir não administrar servidor.
4. **Cuidado com promoções:** em todos os provedores o preço da renovação é bem maior que o do primeiro período (Hostinger KVM 4 vai de R$ 59,99 para R$ 149,99). Calcule o custo pelo preço de renovação.

Custo estimado em produção: **R$ 60–180/mês** de servidor, dentro do orçamento fixo previsto em [08](08-custos-e-precificacao.md).

## 5. Como fica o desenho

```text
fotos.seudominio.com.br  ──DNS (um registro A)──▶  VPS (Brasil)
                                                    ├─ Caddy (HTTPS automático)
                                                    ├─ FLASH! API + site (uvicorn)
                                                    ├─ worker (indexa fotos)
                                                    └─ SQLite → PostgreSQL quando crescer
Google Drive (2 TB)  ◀── conta de serviço ──  originais + pastas dos eventos
```

- O domínio/subdomínio pode continuar na HostGator: só se cria um registro `A` apontando para o IP do VPS. O dashboard do YouTube não é afetado.
- Backup noturno do banco para uma pasta `backups/` no Drive.
- Primeira implantação: `Dockerfile` e `infra/docker-compose.yml` já existem (não testados); a alternativa mais simples para um VPS único é `systemd` + Caddy, sem Docker.

## 6. Checklist de contratação (para você ou para mim, depois de contratado)

- [ ] Servidor no Brasil, Linux (Ubuntu LTS), acesso root por SSH
- [ ] ≥ 2 vCPU (ideal 4), ≥ 4 GB (ideal 8) de RAM, ≥ 50 GB (ideal 100+) NVMe
- [ ] IP fixo; portas 80 e 443 liberadas
- [ ] Preço de renovação anotado
- [ ] Subdomínio escolhido (ex.: `fotos.…`)
- [ ] Chave SSH criada só para este servidor (nada de senha no chat)

## 7. E o PC desktop de casa? (29/10/2026)

**Serve, sim.** Python, OpenCV e o FLASH! rodam direto no Windows ou no Linux, sem Docker. Para o piloto, para testes com fotos reais e para **indexar** os eventos, é a melhor opção (custo zero e, em geral, mais CPU que um VPS barato). Para o **dia do evento, com público acessando**, só com as condições abaixo.

| A favor | Contra |
|---------|--------|
| R$ 0; CPU e RAM geralmente sobram | **Upload residencial** é o gargalo: o ZIP passa pelo servidor |
| Indexa 20 mil fotos em poucos minutos (estimativa, com 8 núcleos) | Queda de energia/internet ou o Windows suspender/atualizar derruba o evento |
| Controle total dos dados | IP dinâmico e CGNAT: resolve com Cloudflare Tunnel (sem abrir portas no roteador) |
| | Dados biométricos de menores num PC doméstico: exige disco criptografado e backup |

**A conta do upload.** Um ZIP com 50 originais de 8 MB tem ~400 MB. Com 50 Mbps de upload, um download leva ~1 minuto; com 10 pessoas baixando juntas, ~10 minutos cada. Por isso, no PC de casa:
- o padrão da galeria deve ser o preview de 1600 px (~350 KB); o original fica sob demanda;
- limitar o ZIP (ex.: 30 fotos por vez) ou entregar o link do Drive;
- testar o upload real em speedtest.net no horário do evento.

**Condições para usar no dia do evento**
- [ ] Cabo de rede (não Wi-Fi), PC sem suspensão e com atualizações automáticas desligadas no dia
- [ ] Nobreak (ou aceitar o risco de queda)
- [ ] Acesso só por Cloudflare Tunnel; nenhuma porta aberta no roteador
- [ ] Disco criptografado (BitLocker no Windows), backup do banco no Drive
- [ ] Conta de usuário dedicada ao FLASH!, sem dados pessoais misturados
- [ ] Plano de contingência: o evento continua pelo Drive como hoje se o PC cair
- [ ] Conferir os termos do plano de internet residencial e da Cloudflare para esse uso

**Arranjo recomendado:** PC de casa para piloto e indexação; VPS no Brasil quando houver cliente pagante com evento aberto ao público.

## Fontes

- [HostGator Brasil – VPS](https://www.hostgator.com.br/vps) (preço inicial e Oracle Cloud no Brasil; planos detalhados não carregaram)
- [Hostinger – VPS](https://www.hostinger.com/br/servidor-vps) (tabela KVM 1–8, preços de promoção e renovação)
- [Render – regiões](https://render.com/docs/regions)
- [Fly.io – preços](https://fly.io/docs/about/pricing/) e [regiões](https://docs.fly.io/reference/regions)
- [Hetzner Cloud](https://www.hetzner.com/cloud/)
- [Oracle – Always Free](https://docs.oracle.com/en-us/iaas/Content/FreeTier/resourceref.htm)
- [Hostzone VPS](https://hostzone.com.br/en/vps-servers), [Cloud Mercato (Vultr SP)](https://pcr.cloud-mercato.com/providers/vultr/flavors/vhp-4c-8gb-amd-sc1/pricing) — comparadores, não confirmados
- [Magalu Cloud – contexto de regiões](https://www.baguete.com.br/noticias/magalu-cloud-cresceu-10x-desde-2025)
