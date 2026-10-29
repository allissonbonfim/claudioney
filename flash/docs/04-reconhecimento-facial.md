# 04 · Reconhecimento facial

Esta é a parte que decide a qualidade percebida do produto **e** o risco jurídico/comercial. Tratada como módulo substituível.

## 1. Interface `FaceEngine`

```python
class FaceEngine(Protocol):
    name: str            # "insightface", "sface", "rekognition"
    version: str         # entra no índice: vetores de motores diferentes NÃO se misturam
    dim: int

    def detect_and_embed(self, image: np.ndarray) -> list[Face]: ...
    def embed_selfie(self, image: np.ndarray) -> SelfieResult: ...  # exige 1 rosto

class Face:
    bbox: tuple[int, int, int, int]
    landmarks: list[tuple[float, float]]   # 5 pontos
    det_score: float
    quality: float                         # 0–1: tamanho, nitidez, pose, oclusão
    embedding: np.ndarray                  # normalizado (L2 = 1)
```

Regras:

- Cada evento fixa **um** motor e uma `index_version`. Trocar de motor = reindexar o evento (E1.6).
- Para motores em nuvem (Rekognition), o "vetor" fica no serviço; a camada `Face` guarda `external_face_id`, e a busca é delegada. A interface esconde a diferença.
- Todo candidato é avaliado contra o **mesmo golden set** (seção 5) antes de entrar em produção.

## 2. Candidatos a motor

| Opção | Licença | Qualidade esperada | Custo | Risco |
|-------|---------|--------------------|-------|-------|
| **InsightFace** (SCRFD + ArcFace, pacote `buffalo_l`) | Código MIT, **modelos só para pesquisa não comercial**; uso comercial exige licença (contato `recognition-oss-pack@insightface.ai`) — *verificado no README do projeto* | Muito boa; padrão de mercado em código aberto | Licença: **orçamento a pedir**; CPU próprio | Usar sem licença em produto vendido é violação |
| **OpenCV Zoo: YuNet (detecção) + SFace (reconhecimento)** | **Apache 2.0** (*verificado*) | Boa em rostos frontais (~99,4% no teste do cartão do modelo); mais fraca em perfil, oclusão, baixa resolução | Quase zero; muito rápido (SFace ~9 ms/rosto em CPU Intel; YuNet ~1,5 ms em entrada pequena) | Precisão em esporte desconhecida → **medir** |
| **Amazon Rekognition** (`IndexFaces` + `SearchFacesByImage`) | Serviço pago | Boa e estável, sem operar GPU/CPU | US$ 0,001 por imagem nos 1º milhão + US$ 0,00001 por rosto/mês (*verificado na página de preços*) | Disponibilidade de `IndexFaces` em `sa-east-1` **não confirmada** (docs indicam subconjunto de operações em São Paulo); dados biométricos fora do país → LGPD art. 33; custo cresce linear |
| **Outros** (DeepFace, CompreFace, AdaFace, modelos de provedores) | Variadas; treinados em bases (MS1M/WebFace) de licença restrita | Variável | Variável | Dívida de licença de **dados de treino**; auditar caso a caso |

**Recomendação provisória (a confirmar no Spike S1):**

1. **Piloto CBDE:** OpenCV YuNet+SFace como padrão (licença limpa, custo zero) **e** Rekognition como motor de contraste.
2. Se SFace não atingir as metas em esporte → pedir cotação de licença do InsightFace (o preço diluído em 10 clientes pode compensar) **ou** usar Rekognition como motor "premium" cobrado por uso.
3. **Nunca** colocar `buffalo_l` em produção, inclusive no piloto, sem licença: piloto para cliente é uso comercial.

> **Nota sobre licença de dados.** Quase todos os modelos de reconhecimento foram treinados em conjuntos acadêmicos de licença restrita. Mesmo com pesos sob Apache, vale uma conversa com o advogado e a leitura do cartão do modelo. Isso é risco de longo prazo; por isso a troca de motor tem que ser barata.

## 3. Pipeline de indexação (por foto)

1. **Decodificar** (JPEG/HEIC/PNG), aplicar orientação EXIF, converter para sRGB.
2. **Redimensionar** para 2048 px no lado maior (cópia de trabalho).
3. **Detectar** rostos (+ 5 landmarks). Descartar `det_score` < 0,6 (configurável).
4. **Qualidade** por rosto: lado da caixa em px (≥ 40 mínimo, ≥ 80 ideal), variância do Laplaciano (nitidez), ângulo de cabeça estimado pelos landmarks (≤ 60°), razão de oclusão (heurística). Gera `quality ∈ [0,1]`.
5. **Alinhar** (transformação por similaridade a 112×112) e **embedar**; normalizar L2.
6. **Gravar**: `faces(photo_id, bbox, quality, embedding, engine, index_version)`.
7. **Clusterizar** (seção 4).
8. **Opcional por evento:** OCR do número de peito (plugin, Fase 4).

**Rostos pequenos/multidão:** detecção em ladrilhos (tiles 1024 px com 25% de sobreposição, supressão de duplicatas por IoU) como opção por evento. Aumenta ~4× o custo; ativar só onde o *recall* medido pedir.

## 4. Clusters ("pessoas") — o salto de recall

Ideia: em vez de comparar a selfie com cada rosto isoladamente, agrupar os rostos do evento por identidade provável, de modo que um acerto forte "puxe" as outras aparições da mesma pessoa (de perfil, de capacete, de longe).

- **Atribuição incremental:** ao indexar um rosto de qualidade ≥ Q, comparar com o centróide dos clusters existentes do evento; se `sim ≥ τ_atribuir` (conservador, acima do `τ_alto`), entra no cluster mais próximo; senão cria cluster. Rostos de baixa qualidade **não criam** cluster, só são atribuídos.
- **Consolidação no encerramento:** reclusterização completa (aglomerativo com ligação média, ou HDBSCAN) para fundir clusters quebrados.
- **Uso na busca:** (a) acertos diretos → (b) expandir para fotos de rostos do mesmo cluster → (c) rotular como "Com certeza" só o que passa `τ_alto` direto ou pertence a cluster cujo centróide passa `τ_alto`.
- **Cuidados:** *chaining* (cluster contaminado juntando duas pessoas parecidas, comum com irmãos/gêmeos). Mitigação: limiar alto de atribuição, revisão do tamanho/dispersão do cluster, e feedback "esta não sou eu" que **separa** o rosto.
- **UX opcional (E2.6):** "Qual destes é você?" mostrando miniaturas do rosto dos 3 clusters mais próximos — maior precisão e aproveitamento de clusters mesmo quando a selfie é ruim.

## 5. Golden set e como medir (a coisa mais importante)

**Montagem (Spike S1):**

- 1 evento real da CBDE, ~1.500 fotos, **30–50 pessoas** rotuladas manualmente (nome interno/ID), incluindo casos difíceis: capacete, óculos, boné, perfil, movimento, longe, contra-luz, irmãos parecidos.
- Selfies de teste dessas pessoas tiradas com celulares diferentes (e algumas fotos "de rede social" para simular selfie ruim).
- Ferramenta simples de rotulagem (planilha + miniaturas, ou Label Studio). ~2–3 dias de trabalho humano.
- **Dados sensíveis:** manter o golden set em disco criptografado, acesso restrito, com autorização por escrito; apagar ao fim do projeto ou anonimizar.

**Métricas:**

| Métrica | Definição | Meta |
|---------|-----------|------|
| **Precisão@limiar** | das fotos entregues "Com certeza", quantas realmente têm a pessoa | ≥ 98% |
| **Recall@limiar** | das fotos em que a pessoa aparece com rosto ≥ 60 px, quantas foram encontradas | ≥ 90% (esporte) |
| **Taxa de falsa aceitação por busca** | média de fotos erradas por busca | ≤ 0,2 |
| **Sucesso da selfie** | selfies que geram ≥ 1 acerto verdadeiro | ≥ 95% |
| **Latência** | tempo de `embed(selfie)` e busca | ver [02](02-requisitos.md) |
| **Custo por 1.000 fotos** | CPU/segundos ou US$ API | menor melhor |

**Procedimento:** para cada motor, varrer o limiar de 0,2 a 0,7, desenhar curva Precisão×Recall, escolher `τ_alto` no ponto de precisão ≥ 98% e `τ_baixo` no ponto de recall ≥ 90%. Registrar tudo num relatório versionado (`flash/bench/reports/AAAA-MM-DD.md`). **Repetir a cada troca de motor/modelo e a cada novo tipo de evento.**

**Regra de decisão:** escolher o motor mais barato que cumpra as metas; em empate, o de licença mais limpa.

**Pontos de partida de limiar (para depois calibrar, não para usar às cegas):** a documentação do OpenCV sugere cosseno ≈ 0,363 para o SFace como limiar de "mesma pessoa" (comparação 1:1). Em busca 1:N com milhares de rostos o limiar seguro costuma ser **bem mais alto**, por isso a calibração acima é obrigatória.

## 6. Selfie: qualidade antes de pesquisar

No dispositivo (site) e no servidor (Instagram), validar antes de gastar busca:

- exatamente 1 rosto; rejeitar 0 ou ≥ 2 ("sai só você na foto, por favor");
- lado do rosto ≥ 160 px; nitidez ≥ mínimo; iluminação (histograma);
- ângulo ≤ 30°; olhos visíveis (óculos escuros? sugerir tirar); sem filtro de beleza pesado (heurística de suavização);
- **liveness-lite** (opcional, no site): pedir um leve movimento ou exigir câmera ao vivo (`getUserMedia` sem upload) no modo menores — reduz fotos de terceiros; não é anti-fraude forte.

## 7. Privacidade do vetor

O *embedding* é dado biométrico (permite identificar). Tratar como tal:

- Selfie: só o vetor sobrevive, em memória/sessão com TTL ≤ 24 h, criptografado quando em repouso.
- Rostos do evento: retenção limitada (padrão 90 dias após encerrar); depois só ficam as fotos (sem vetores).
- Opção avançada: **gerar o vetor da selfie no navegador** (ONNX Runtime Web) para que a imagem nem saia do aparelho. Exige que o modelo do índice seja leve o suficiente para baixar (SFace quantizado ≈ 18–37 MB, a validar). Fase 4.
- Exportar/portar: nunca exportar vetores para fora do tenant; backups criptografados.

## 8. Plano B e evolução

- **Motor híbrido:** SFace/licenciado para o índice em massa + reranking com motor mais forte nos top-K.
- **Fine-tuning:** não no início. Só se o golden set provar ganho e a licença dos dados permitir.
- **Plugins por vertical:** número de peito (corridas), cor do uniforme/time (esporte escolar), nome no crachá.
- **Aceleração:** CPU com ONNX Runtime + INT8 primeiro; GPU só sob demanda em evento gigante (aluguel por hora).
