# Tech Stack · PayChat Security Lab

> Decisões técnicas, justificativas e alternativas consideradas

---

## Visão geral

O stack do projeto é organizado em oito camadas, cada uma com responsabilidade clara e ferramentas escolhidas para sustentar a análise comparativa entre as três arquiteturas. As decisões priorizam reprodutibilidade, custo controlado e cobertura de vetores de ataque relevantes para o domínio de payments.

| Camada | Responsabilidade | Ferramentas principais |
|---|---|---|
| Marketplace base | Sistema mínimo que sustenta os ataques | Python, FastAPI, PostgreSQL |
| Agente | Orquestração ReAct e tool calling | LangGraph |
| Modelos LLM | Inteligência das três variantes | Claude Sonnet 4.6, Llama 3.3 70B Turbo (Together AI), Llama Guard 4 (Together AI) |
| Infraestrutura | Persistência, cache e RAG | Docker Compose, Redis, ChromaDB |
| Red team | Execução sistemática de ataques | Garak, PyRIT, harness customizado, Transformers (white-box) |
| Defesas | Camadas de proteção em profundidade | Llama Guard 4, detector heurístico (Rebuff-style), Presidio (mock) |
| Avaliação | Métricas, testes e visualizações | Pytest, Jupyter, Pandas |
| Entrega | CI/CD, scoring e documentação | GitHub Actions, CVSS, Markdown |

---

## 1. Camada de marketplace base

### Python 3.11+

Linguagem padrão para projetos de ML e segurança aplicada. A versão 3.11 traz melhorias significativas de performance e suporte completo a type hints modernos, que vão ser usados consistentemente para tornar o código auditável.

### FastAPI

Framework web assíncrono. Escolhido porque:

- Documentação OpenAPI automática facilita a inspeção das ferramentas expostas ao agente
- Suporte nativo a Pydantic v2 garante validação de schema em todos os endpoints — tema central para insecure output handling
- Performance assíncrona necessária para sustentar a execução paralela da matriz de ataques
- Padrão de fato no ecossistema Python para APIs LLM em produção

**Alternativas consideradas:** Flask (sem validação nativa de schema), Django (overhead desnecessário), Starlette puro (sem benefícios sobre FastAPI).

### PostgreSQL 16

Banco relacional principal. Justificativa:

- Schema rigoroso para representar usuários, produtos, pedidos, transações e sessões com integridade referencial
- Permite simular cenários realistas de payments (transações, chargebacks, conciliação)
- Habilita ataques de SQL injection via tool calling do agente, o que é um vetor central de insecure output handling
- Extensão `pgcrypto` permite simular tokens de pagamento em formato Luhn de forma realista

### SQLAlchemy 2.0

ORM com suporte a tipagem estática completa. Usado para:

- Definir o schema do marketplace de forma declarativa
- Garantir que queries geradas pelo agente passem por uma camada com parametrização automática (defesa contra SQL injection no baseline e re-execução)
- Facilitar a criação de dados sintéticos via factories

---

## 2. Camada de agente

### LangGraph

Framework de orquestração para agentes ReAct e workflows multi-step. Escolhido em vez de LangChain puro porque:

- Suporta grafos de execução explícitos, o que torna o pipeline da Variante C (multi-model) auditável
- Permite implementar interrupções e human-in-the-loop necessárias para defesas de excessive agency
- Stateful por design, facilita análise de ataques multi-turno (Crescendo, Speak Out of Turn)
- Documentação e padrões maduros para tool calling com modelos OpenAI-compatible (Claude) e locais (Ollama)

### ReAct pattern

Padrão de raciocínio + ação descrito no paper *ReAct: Synergizing Reasoning and Acting in Language Models* (ICLR 2023), incluído na pasta do projeto. O padrão é central porque:

- É a arquitetura agentic mais difundida em aplicações LLM de produção
- Habilita naturalmente os vetores de excessive agency e insecure plugin design
- Permite trace de raciocínio que serve como evidência reproduzível dos ataques

### Tool calling

Ferramentas expostas ao agente, idênticas nas três variantes para garantir paridade funcional:

| Ferramenta | Função | Vetores que expõe |
|---|---|---|
| `search_products` | Busca no catálogo via RAG | Prompt injection indireta, RAG poisoning |
| `get_order` | Consulta pedidos por ID | Insecure plugin design, broken access control |
| `process_refund` | Inicia reembolso | Excessive agency, TOCTOU |
| `send_message` | Envia mensagem entre atores | Insecure output handling, exfiltration |
| `get_user_info` | Consulta dados de usuário | Sensitive information disclosure |

---

## 3. Camada de modelos LLM

### Claude Sonnet 4.6 (Variante A)

Modelo proprietário da Anthropic, acessado via API. Representa o estado da arte comercial em alinhamento e capacidades agentic.

**Justificativa:**
- Tool use nativo de alta qualidade, padrão no mercado
- Alinhamento via Constitutional AI, baseline forte contra prompt injection direta
- Ausência de acesso a logits e pesos define a fronteira de ataques aplicáveis (apenas black-box), o que é exatamente o cenário de produção realista para clientes de payments
- Identifier do modelo: `claude-sonnet-4-5` (versão mais recente disponível via API)

**Custo estimado para o projeto:** US$ 30–60 em chamadas durante toda a execução da matriz 3×6 (baseline + pós-defesa).

### Llama 3.3 70B Instruct Turbo (Variantes B e C)

Modelo open-source da Meta, acessado via Together AI (API OpenAI-compatible). Mesmo modelo nas duas variantes para isolar o efeito da arquitetura defensiva, não do modelo subjacente.

> **Migração documentada (ver ADR-002):** o projeto começou com Llama 3.1 8B Instant via Groq. Em runtime, B e C rodam **Llama 3.3 70B Turbo via Together AI**. A decisão foi tomada de forma consciente — não é label histórico. As variáveis `LLM_*` do `.env` são a fonte de verdade; o baseline e o pós-defesa de B/C foram coletados sob esta configuração e são consistentes entre si.

**Justificativa:**
- Hospedagem gerenciada dispensa hardware local (a máquina de desenvolvimento tem 8 GB de RAM)
- API OpenAI-compatible facilita integração com LangGraph e permite trocar entre variantes/providers mudando apenas a base URL
- Together AI tem rate limit dinâmico (sem tiers; só exige compra única de US$ 5), o que viabiliza suítes longas de red team — a throttle real do projeto passou a ser a RAM local, não a API
- O 70B é um alvo "mais próximo de produção" que o 8B, fortalecendo a comparação A (Claude) vs B/C (open-source gerenciado)
- Alinhamento Meta's safety training, mais permissivo que Claude, expõe vulnerabilidades mais facilmente

### Llama Guard 4 12B (Variante C)

Modelo classificador da Meta especializado em moderação de conteúdo. Usado como pré-filtro de input na Variante C, hospedado na Together AI.

**Justificativa:**
- Treinado especificamente para detectar conteúdo malicioso, prompt injection e jailbreak
- Disponível no catálogo Together AI, mesma autenticação e base URL que o modelo principal
- Padrão de fato em pipelines de defesa LLM em produção
- Saída no formato `safe` / `unsafe\nS<categoria>` consumida por `llama_guard.py` (`raw.lower().startswith("unsafe")`)

### GPT-2 small (apêndice white-box)

Modelo histórico da OpenAI, 124M parâmetros, pesos públicos via Hugging Face. Usado **exclusivamente** na seção de apêndice do relatório para demonstrar ataques white-box (GCG, MIA, gradient-based extraction).

**Justificativa:**
- Cabe folgadamente na RTX 3050 (4 GB VRAM), carregado via Hugging Face Transformers
- Pesos abertos permitem cálculo de gradientes e acesso completo a logits
- Modelo de demonstração técnica, não parte da matriz 3×6 comparativa
- Suficiente para validar a mecânica dos ataques white-box e justificar discussão arquitetural sobre exposição de superfície em deployments self-hosted

**Identifier:** `gpt2` no Hugging Face Hub.

### Por que inferência gerenciada como "embedded representativo"

A constituição classifica a Variante B como "embedded open-source model". A escolha de inferência gerenciada (Together AI) sobre self-hosting via Ollama merece nota explícita porque pode parecer contraditória.

**Argumento arquitetural:** o threat model funcional de um modelo open-source hospedado em Together AI é equivalente ao de um modelo open-source self-hosted em GPUs próprias, exceto por dois pontos endereçados na análise comparativa:

1. **Acesso a logits e gradientes:** Together AI não expõe (limitação que define a fronteira black-box vs white-box, explorada explicitamente no apêndice do relatório)
2. **Soberania de dados:** Together AI processa dados em infraestrutura de terceiros (consideração discutida na análise multi-model como recomendação de governança)

Para todos os outros vetores — prompt injection, insecure output handling, sensitive information disclosure, insecure plugin design, excessive agency — o comportamento do modelo é determinado pelos pesos, que são os mesmos.

Empresas de payments majoritariamente preferem inferência open-source gerenciada (Together, Groq, Bedrock) a self-hosting de GPUs por questão de custo operacional e SLA. A Variante B representa esse cenário dominante.

### Cliente OpenAI-compatible

Cliente `openai` com base URL ajustada para `https://api.together.xyz/v1` (variável `LLM_BASE_URL`). O cliente OpenAI permite uma única abstração para Claude e Llama na harness de red team, e trocar de provider (Together ↔ Groq) exige apenas mudar a base URL e o nome do modelo nas variáveis `LLM_*`.

---

## 4. Camada de infraestrutura

### Docker Compose

Orquestração local de todos os serviços. Garante que o ambiente seja reproduzível em qualquer máquina com Docker instalado.

**Serviços orquestrados:**
- `api`: aplicação FastAPI
- `db`: PostgreSQL 16 com volume persistente
- `redis`: cache de sessões e rate limiting
- `chroma`: ChromaDB para RAG

O filtro de PII da Variante C usa um **mock regex do Presidio** (`scripts/presidio_mock.py`) rodando no host em `:3000`, não o container Presidio Analyzer (ver justificativa em §6). O serviço `presidio` do compose não é usado.

Toda a inferência LLM é remota (Claude via Anthropic API, Llama 3.3 70B e Llama Guard 4 via Together AI). A máquina local executa a aplicação, a infraestrutura de suporte, o GPT-2 local do detector de perplexidade e os scripts de red team — uso de RAM da stack Docker ~627 MiB, dentro do limite de ~7.4 GB do host.

### Redis 7

Cache em memória usado para:

- Sessões de usuário simuladas
- Rate limiting de requisições ao agente (defesa contra model theft)
- Query budget tracking por sessão
- Conversação multi-turno (memória do agente)

### ChromaDB

Banco vetorial para o RAG sobre catálogo de produtos e FAQ. Escolhido em vez de Pinecone, Qdrant ou Weaviate porque:

- Roda localmente sem dependência de serviço externo
- API Python simples, integração direta com LangChain e LangGraph
- Suporta metadados, necessário para implementar RAG poisoning de forma controlada
- Documentação clara para inspeção e auditoria de embeddings

**Embedding model:** `sentence-transformers/all-MiniLM-L6-v2` via Sentence Transformers local. Modelo pequeno (~80 MB), roda em CPU sem impacto perceptível.

---

## 5. Camada de red team

### Garak

Framework open-source da NVIDIA especializado em red teaming de LLMs. Usado para:

- Execução automatizada de baterias de prompt injection conhecidas
- Probes pré-definidos para data leakage, jailbreak, malware generation
- Geração de relatórios estruturados por probe e por modelo
- Suporte nativo a múltiplos backends (OpenAI-compatible cobre Claude via wrapper e Ollama diretamente)

**Probes prioritários para o projeto:**
- `promptinject` — variantes de prompt injection
- `dan` — jailbreaks da família DAN
- `leakreplay` — extração de dados de treinamento
- `xss` — payloads de XSS via output do modelo
- `goodside` — prompts adversariais clássicos

### PyRIT

Framework da Microsoft para red teaming generativo. Complementar ao Garak para:

- Ataques multi-turno (Crescendo, Speak Out of Turn)
- Geração automatizada de variações de prompts adversariais
- Orquestração de "atacante LLM vs alvo LLM" (PAIR)
- Logging estruturado para evidências reproduzíveis

### Harness customizado

Scripts Python sob `red_team/custom/` que implementam ataques específicos do domínio marketplace, não cobertos por Garak ou PyRIT:

- RAG poisoning via cadastro de produto malicioso
- Cross-actor impersonation
- Tool chaining para exfiltração
- TOCTOU em refund flow
- Logic-chain injection contextual ao marketplace

### Hugging Face Transformers (apêndice white-box)

Biblioteca usada **exclusivamente** nos scripts de ataque white-box contra GPT-2 small. Permite:

- Carregamento direto de modelo e tokenizer com `AutoModelForCausalLM.from_pretrained("gpt2")`
- Acesso a logits brutos em cada token de saída
- Cálculo de gradientes via PyTorch (`loss.backward()`) para implementar GCG
- Manipulação de embeddings para ataques de inversão

Os scripts ficam isolados em `red_team/whitebox/` e rodam fora do pipeline principal, executados apenas durante a geração do apêndice técnico do relatório. Dependência adicional: `torch >= 2.5`.

---

## 6. Camada de defesas

### Llama Guard 4

Já listado na camada de modelos. Atua como pré-filtro de input na Variante C: detecta prompt injection e conteúdo malicioso antes de chegar ao modelo principal, rejeitando o request com 400 + categoria. O comportamento é fortemente dependente da categoria do ataque — bloqueia onde o vetor toca a taxonomia de conteúdo (privacidade S7, ação nociva), e passa onde é manipulação arquitetural pura (model theft, insecure plugin).

### Detector heurístico (Rebuff-style)

Detector de prompt injection inspirado no Rebuff, implementado de forma **customizada** em `app/infrastructure/defenses/rebuff.py` (`RebuffDetector`). Escopo entregue:

- Heurísticas regex baseadas em padrões conhecidos de injeção
- Canary tokens injetados no prompt para detectar leakage no output

> **Divergência consciente:** não usamos a biblioteca Rebuff (que traz detector baseado em LLM e integração com vector DB). Para o escopo do lab, um detector heurístico determinístico é mais auditável e reproduzível que um segundo LLM opinando — e evita custo/latência de chamada extra. Detector LLM e vector DB ficam fora de escopo.

### Presidio (mock)

Detecção e redação de PII na camada de output da Variante C, exposta em `:3000` via `scripts/presidio_mock.py`:

- Detecção de CPF, CNPJ, email, telefone, número de cartão (Luhn)
- Redação automática (`<REDACTED:TYPE>`) antes de retornar resposta ao usuário
- Entidades customizadas (`PAYMENT_TOKEN`, `INTERNAL_SECRET`)
- Política de redação configurável por nível de severidade

> **Divergência consciente:** usamos um **mock regex** fiel ao contrato `/analyze`, não o container Microsoft Presidio real. O Presidio real não traz reconhecedores nativos de CPF/CNPJ nem suporte a `pt`, então entregaria essencialmente os mesmos regexes custando ~2 GiB de RAM — inviável no budget de ~7.4 GB do host com o GPT-2 local e a stack Docker no ar.

### Rate limiter customizado

Implementação Python sobre Redis. Estratégias aplicadas:

- Limite de requests por minuto por sessão
- Limite de tokens por hora por usuário
- Detecção de padrões de extraction queries (queries muito similares em sequência curta)
- Cooldown progressivo em caso de comportamento suspeito

### Output perturbation (deferida — fora de escopo)

Defesa contra model theft via extraction, **não implementada** na entrega inicial. Exigiria adição de ruído controlado em logits antes da amostragem — e nem Together AI nem Groq expõem logits. Adiada para post-MVP (depende de modelo self-hosted). Contra model theft, a defesa entregue é o rate limiting do `AntiTheftGuard` (controle de volume); ver nota metodológica abaixo.

> **Nota metodológica (model theft):** o rate limiting é controle de volume, não de conteúdo. A redução de ASR para model theft é marcada **NÃO-APLICÁVEL** no relatório, porque (a) `block_rate = (volume − threshold)/volume` é aritmética do threshold, não medida de detecção; e (b) o ataque se completa dentro do threshold. Demonstra-se a quebra do indicador em vez de inflar um número de "redução %".

---

## 7. Camada de avaliação

### Pytest

Framework de testes. Usado para:

- Smoke tests garantindo paridade funcional entre as três variantes
- Regression tests que reexecutam todos os ataques após cada mudança de defesa
- Fixtures que populam dados sintéticos consistentes entre execuções
- Marcadores para separar testes funcionais de testes de segurança

### Jupyter Notebook

Notebook consolidado entregue ao final do projeto. Contém:

- Execução interativa da matriz 3×6 (baseline e pós-defesa)
- Visualizações comparativas dos resultados
- Análise de causa raiz por vetor com exemplos de payload
- Geração das tabelas e gráficos usados no relatório executivo

### Pandas + Matplotlib + Seaborn

Stack padrão para manipulação e visualização. Usado para:

- Carregar resultados estruturados das execuções de red team
- Calcular attack success rate, redução percentual, intervalos de confiança
- Gerar heatmaps da matriz 3×6
- Produzir gráficos de barras comparativos por categoria

---

## 8. Camada de entrega

### GitHub Actions

CI/CD básico para garantir qualidade do código entregue:

- Lint com `ruff` e formatação com `black`
- Type check com `mypy`
- Execução da suíte de testes funcionais a cada PR
- Build da imagem Docker para validação do ambiente

### CVSS v3.1

Padrão de scoring usado para priorizar remediações no relatório executivo. Cada vulnerabilidade encontrada recebe:

- Vetor CVSS completo
- Score base
- Score Environmental ajustado pelo contexto de payments (CR:H/IR:H/AR:M; Temporal omitido por indisponibilidade de E/RL para LLMs comerciais — ver `report/threat_model.md` §2.2)
- Tradução do score técnico para impacto de negócio (chargeback, account takeover, fraud loss)

### Markdown + Pandoc

Documentação técnica em Markdown, conversão para PDF via Pandoc quando necessário. Mantém o repositório legível no GitHub e permite gerar documento formatado para distribuição.

---

## Architecture Decision Records (ADRs)

ADRs registram decisões arquiteturais significativas tomadas durante o projeto, com contexto, alternativas consideradas e consequências. Cada ADR é imutável após aceito — mudanças exigem novo ADR que substitui ou complementa o anterior.

### ADR-001 — Clean Architecture right-sized como padrão de projeto

**Status:** Aceito

**Contexto:**
O projeto implementa três variantes funcionalmente equivalentes de um agente conversacional (A, B, C), executa uma matriz de ataques contra cada variante, aplica camadas de defesa plugáveis e mede redução de risco. A validade científica dos resultados depende de paridade comportamental entre as variantes e da capacidade de ativar ou desativar defesas individualmente sem alterar o pipeline experimental.

Sem um padrão arquitetural explícito, há três riscos materiais:
1. Duplicação de código entre variantes introduzindo divergências sutis que contaminam a matriz comparativa
2. Defesas acopladas ao pipeline principal, exigindo branches de código para cada combinação de defesas ativas
3. Estrutura desorganizada que prejudica auditoria do projeto por leitores externos (recrutadores, revisores técnicos do portfólio)

**Decisão:**
Adotar Clean Architecture em uma versão deliberadamente reduzida ("right-sized"), aplicando apenas três princípios e dispensando explicitamente o restante do canon.

**Princípios adotados:**

1. **Portas explícitas para o que varia entre variantes.**
   Tudo que difere entre as Variantes A, B e C — runtime do agente, defesas, persistência de evidências — é definido como interface (porta) no domínio. Cada variante é um adaptador da porta `AgentRuntime`. Cada defesa é um adaptador da porta `DefenseLayer`. A harness de red team consome as portas, nunca os adaptadores diretamente.

2. **Inversão de dependência para componentes injetados.**
   Agente recebe `tools`, `evidence_store`, `defense_pipeline` por construção, não por singleton nem configuração global. Isso viabiliza ativar ou desativar defesas via flag de configuração e garante que o pipeline experimental seja determinístico.

3. **Frameworks isolados na camada de infraestrutura.**
   FastAPI, SQLAlchemy, LangGraph, SDKs de modelos ficam confinados em `infrastructure/`. Domínio (entidades, portas) e aplicação (use cases) são Python puro com Pydantic. Testes unitários do domínio rodam sem inicializar Docker ou containers.

**Estrutura de pastas resultante:**

```text
app/
  domain/
    ports/
      agent_runtime.py
      defense_layer.py
      evidence_store.py
    entities/
      attack.py
      evidence.py
      finding.py
  application/
    use_cases/
      execute_attack.py
      apply_defense.py
      compute_metrics.py
  infrastructure/
    agents/
      variant_a_claude.py
      variant_b_llama.py
      variant_c_pipeline.py
    defenses/
      llama_guard.py
      presidio.py
      rebuff.py
      rate_limiter.py
    persistence/
      filesystem_evidence.py
      postgres_audit.py
    web/
      fastapi_app.py
  red_team/
    harness.py
    techniques/
      prompt_injection.py
      output_handling.py
      ...
```

**Princípios dispensados (com justificativa):**

| Princípio descartado | Justificativa |
|---|---|
| Camada de "interface adapters" entre application e infrastructure | Overkill para o tamanho do projeto; adiciona indireção sem benefício |
| DTOs separados das entidades | Entidades Pydantic atravessam camadas como decisão consciente; ganha-se simplicidade e perde-se pureza acadêmica |
| Mappers e factories sofisticados | Atrapalham debug de payloads adversariais; preferimos construção direta |
| Use cases para toda operação | Operações triviais (validação simples, cálculo de métrica) ficam como funções em `application/`, não como classes use case |
| "Domain não importa nada externo" no extremo | Pydantic é importado no domínio; decisão pragmática |

**Alternativas consideradas:**

- **Clean Architecture ortodoxa:** rejeitada por excesso de cerimônia incompatível com prazo de 6 semanas e natureza majoritariamente script-driven do red team
- **Estrutura modular plana sem vocabulário arquitetural:** rejeitada por não oferecer mecanismo claro para garantir paridade entre variantes nem plugabilidade de defesas
- **Hexagonal Architecture pura:** semelhante à decisão final na prática; a escolha de "Clean Architecture right-sized" é convenção de nomenclatura sem diferença material

**Consequências:**

- **Positivas:** paridade comportamental entre variantes garantida por construção; defesas plugáveis via configuração; domínio testável sem infra; código auditável por leitores externos; sinalização profissional adequada para vagas em payments
- **Negativas:** custo inicial de design (~1 dia adicional na Fase 1) para definir portas e estrutura; pequena curva de aprendizado se outros engenheiros entrarem no projeto
- **Riscos mitigados:** divergência sutil entre variantes; acoplamento entre pipeline experimental e defesas
- **Riscos não mitigados:** sobre-engenharia em áreas específicas se a aplicação dos princípios for inconsistente (revisão a cada fim de fase para garantir consistência)

**Aplicação no roadmap:**
- Fase 1 cria a estrutura de pastas e arquivos de porta
- Fases 4, 5, 6 implementam cada variante como adaptador da porta `AgentRuntime`
- Fase 9 implementa cada defesa como adaptador da porta `DefenseLayer`
- Toda fase que adiciona infraestrutura nova confina o framework correspondente em `infrastructure/`

**Revisão:**
Esta decisão deve ser revisitada se ao final da Fase 6 a estrutura estiver atrapalhando mais do que ajudando. Critério de revisão: tempo gasto em refatoração arquitetural superior a 20% do tempo total da fase.

---

### ADR-002 — Migração Groq → Together AI e upgrade Llama 3.1 8B → 3.3 70B nas Variantes B/C

**Status:** Aceito

**Contexto:**
O plano original (ADR de stack v1/v2) definia as Variantes B e C sobre Llama 3.1 8B Instant e Llama Guard 3 1B hospedados na Groq, justificado pelo free tier de 14.4K req/dia e pela latência da LPU. Durante a execução do red team, dois fatos mudaram o cálculo:

1. O free tier da Groq impõe limites diários e de tokens que interrompiam suítes longas de red team, exigindo fragmentar a coleta ao longo de dias.
2. O 8B é um alvo fraco para uma auditoria que se propõe "próxima de produção" — empresas de payments que adotam open-source gerenciado tendem a rodar modelos maiores.

O roadmap (`Post-MVP`) já previa o upgrade para 70B como item adiado, com a ressalva de que "confunde a variável experimental". A ressalva se aplica à comparação A vs B, não a B vs C.

**Decisão:**
Migrar B e C para **Llama 3.3 70B Instruct Turbo** e o guard para **Llama Guard 4 12B**, ambos via **Together AI** (API OpenAI-compatible, `LLM_BASE_URL=https://api.together.xyz/v1`). As variáveis `LLM_*` do `.env` são a fonte de verdade do runtime; o código (`variant_b_llama.py`) é dirigido por env e a Variante C compõe a B, então ambas trocam de provider/modelo juntas.

**Consequências:**
- **Positivas:** alvo mais próximo de produção; rate limit dinâmico da Together (sem tiers, só compra única de US$ 5) remove a Groq como gargalo — a throttle real passa a ser a RAM local; baseline e pós-defesa de B/C foram coletados integralmente sob 70B, logo são **consistentes entre si**.
- **Negativas:** a comparação A (Claude) vs B/C deixou de controlar o tamanho do modelo (8B → 70B); a justificativa de custo zero do free tier Groq não vale mais (custo real ~US$ 2 na coleta). B vs C permanece limpa (mesmo modelo, só a arquitetura defensiva muda).
- **Mitigação da ressalva do roadmap:** o objetivo central do projeto é comparar **arquiteturas defensivas** (A api-based vs B embedded vs C pipeline), não tamanhos de modelo; a diferença de porte A↔B é discutida explicitamente na análise comparativa do relatório.
- **Groq:** permanece como provider legado opcional (`GROQ_API_KEY`/`GROQ_MODEL` no `.env`), útil para smoke test alternativo, mas não é o caminho de runtime.

**Aplicação:** todas as referências a "Llama 3.1 8B via Groq" e "Llama Guard 3" em specs/README/notebooks são label histórico; o que executou é o desta ADR.

---

## Resumo de versões fixadas

```text
python                    3.11
fastapi                   0.115
sqlalchemy                2.0
postgresql                16
redis                     7
chromadb                  0.5
langgraph                 0.2
openai                    1.55 (cliente OpenAI-compatible para Claude, Together e Groq)
groq                      0.13 (SDK Python — provider legado, opcional)
transformers              4.46+ (apêndice white-box + perplexidade)
torch                     2.12+cpu (índice CPU do PyTorch; apêndice white-box + perplexidade)
claude-sonnet             4.5 (claude-sonnet-4-5)
llama                     meta-llama/Llama-3.3-70B-Instruct-Turbo (via Together AI)
llama-guard               meta-llama/Llama-Guard-4-12B (via Together AI)
gpt-2                     gpt2 (via Hugging Face Hub)
garak                     0.10
pyrit                     0.6
presidio                  mock regex (scripts/presidio_mock.py) — não o container Analyzer
rebuff                    detector heurístico customizado — não a biblioteca rebuff
```

---

## Custos estimados

| Item | Custo aproximado |
|---|---|
| Anthropic API (Claude Sonnet 4.6) | US$ 30–60 ao longo do projeto |
| Together AI (Llama 3.3 70B + Llama Guard 4) | ~US$ 2 reais gastos na coleta; exige compra única de US$ 5 (rate limit dinâmico, sem tiers) |
| Infraestrutura local (containers + scripts + GPT-2) | Zero — roda em laptop com ~7.4 GB de RAM |
| White-box em GPT-2 small (apêndice) | Zero — cabe na RTX 3050 de 4 GB |
| **Total estimado** | **US$ 35–65 (R$ 175–325)** |

---

## Decisões revisitáveis

Esta seção registra escolhas que podem ser revistas conforme o projeto avança:

- **Embedding model do RAG** — `all-MiniLM-L6-v2` pode ser substituído por modelo maior se a qualidade do RAG for insuficiente para os ataques de indirect injection
- **Modelo open-source nas Variantes B e C** — ~~revisável~~ **decisão tomada (ver ADR-002)**: migrado de Llama 3.1 8B (Groq) para Llama 3.3 70B Turbo via Together AI. Baseline e pós-defesa de B/C foram coletados sob esta configuração
- **Modelo do apêndice white-box** — GPT-2 small (124M) pode ser substituído por Pythia 410M ou TinyLlama 1.1B para cobertura técnica mais robusta, ainda dentro da capacidade da RTX 3050 de 4 GB
- **Sessão pontual em GPU cloud** — opcional, US$ 5–10 em RunPod ou Vast.ai para rodar GCG/MIA contra Llama 3.1 8B real, caso queiramos resultados white-box mais convincentes do que GPT-2 small
- **Pandoc para PDF** — pode ser substituído por Quarto se a saída exigir formatação mais elaborada
- **CVSS v3.1** — pode ser complementado pelo framework MITRE ATLAS específico para ML/IA no relatório final

---

*Documento vivo · v4 · alinhado ao runtime real (Together AI / Llama 3.3 70B / Guard 4, Presidio mock, Rebuff heurístico) — ver ADR-002*