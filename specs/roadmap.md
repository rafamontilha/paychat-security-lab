# Roadmap · PayChat Security Lab

Cada fase entrega uma capacidade testável. As fases são dimensionadas para 1–3 dias de trabalho focado. Uma fase está concluída quando os entregáveis podem ser verificados manualmente de ponta a ponta.

**Cross-cutting requirement — Reprodutibilidade:** toda fase que produz artefato (código, dados, evidência de ataque) deve ser reexecutável a partir de um clone limpo do repositório, com instruções no `README.md` da fase. Reprodutibilidade é merge blocker. Ver `TECH_STACK.md` — seções de Infraestrutura e Entrega — para padrões de containerização, fixação de versões e logging estruturado.

**Cross-cutting requirement — Evidências versionadas:** toda execução de ataque ou defesa que gere métrica deve produzir um artefato persistido em `evidence/` (JSON estruturado com timestamp, payload, response, success flag). Análises agregadas no notebook Jupyter consomem desses artefatos, nunca de re-execução ao vivo.

---

## Fase 1 — Setup do repositório e ambiente

**Goal:** repositório operacional, ambiente containerizado funcionando, integrações remotas validadas.

- Repositório GitHub criado com estrutura `app/`, `red_team/`, `defenses/`, `evidence/`, `notebooks/`, `report/`
- `pyproject.toml` com dependências fixadas conforme `TECH_STACK.md`
- `docker-compose.yml` orquestrando PostgreSQL 16, Redis 7, ChromaDB, container do Presidio Analyzer
- FastAPI app esqueleto com `GET /health` retornando `{ "status": "ok" }`
- Variáveis de ambiente em `.env.example`: `ANTHROPIC_API_KEY`, `GROQ_API_KEY`, `DATABASE_URL`, `REDIS_URL`, `CHROMA_URL`
- Script `scripts/smoke_test_models.py` que faz uma chamada de teste contra Claude Sonnet 4.6, Llama 3.1 8B (Groq) e Llama Guard 3 (Groq), reportando latência e tokens
- GitHub Actions com lint (`ruff`), format check (`black`) e type check (`mypy`) rodando em cada PR
- `README.md` com instruções de setup local (clonar, copiar `.env`, `docker compose up`, `python scripts/smoke_test_models.py`)

**Done when:** `docker compose up` inicia todos os containers sem erro, `curl localhost:8000/health` responde 200, e `python scripts/smoke_test_models.py` imprime resposta válida das três APIs.

---

## Fase 2 — Marketplace base

**Goal:** sistema mínimo de marketplace que sustenta todos os ataques posteriores. Sem agente ainda.

- Schema PostgreSQL via SQLAlchemy: tabelas `users`, `products`, `orders`, `messages`, `transactions`, `sessions`, `audit_log`
- Migrations via Alembic versionadas no repositório
- Seed script `scripts/seed.py` populando 50 usuários (4 perfis: comprador, vendedor, suporte, admin), 100 produtos, 200 pedidos, 50 transações com formato Luhn válido para tokens
- Dados sintéticos incluem PII fictícia (nomes, CPFs gerados, emails, telefones) e secrets simulados (chaves de API, tokens internos)
- Endpoints REST mínimos com autenticação via header `X-API-Key`:
  - `POST /api/auth/login` — autenticação simulada, retorna session token
  - `GET /api/products`, `GET /api/products/{id}`
  - `GET /api/orders`, `GET /api/orders/{id}`
  - `GET /api/users/{id}` (requer privilégio adequado)
  - `POST /api/messages` — envio de mensagem entre atores
  - `POST /api/refunds` — inicia reembolso (requer ownership ou privilégio admin)
- Middleware de logging estruturado em todos os endpoints (`audit_log`)
- RBAC mínimo: cada endpoint declara perfis permitidos; rejeição retorna 403

**Done when:** `python scripts/seed.py` popula a base, e uma sequência manual de `curl` consegue: autenticar como comprador, listar produtos, abrir um pedido, enviar mensagem ao vendedor — tudo registrado em `audit_log`.

---

## Fase 3 — RAG e dados para ataques indiretos

**Goal:** RAG operacional sobre catálogo e FAQ, com hooks que sustentam ataques de indirect injection.

- Embeddings via `sentence-transformers/all-MiniLM-L6-v2` rodando localmente
- Ingestão dos 100 produtos no ChromaDB com metadados (`seller_id`, `category`, `created_at`)
- Coleção separada de FAQ com 30 perguntas e respostas sintéticas sobre o marketplace
- Endpoint `POST /api/rag/search` recebe query, retorna top-k chunks
- Endpoint `POST /api/products` permite cadastro com título e descrição livres (vetor explícito de RAG poisoning)
- 5 produtos "envenenados" criados no seed para validação inicial: títulos e descrições com payloads de prompt injection conhecidos
- Script `scripts/validate_rag.py` faz queries de teste e imprime chunks retornados

**Done when:** consulta `python scripts/validate_rag.py "como solicito reembolso?"` retorna chunks relevantes da FAQ; consulta `python scripts/validate_rag.py "tênis preto"` retorna produtos relevantes incluindo os envenenados (visíveis para inspeção).

---

## Fase 4 — Variante A: agente Claude via Anthropic API

**Goal:** agente ReAct funcional com Claude Sonnet 4.6, sem guardrails adicionais. Baseline da matriz.

- Cliente LangGraph configurado para Claude via SDK Anthropic
- Cinco ferramentas registradas com schema validado: `search_products`, `get_order`, `process_refund`, `send_message`, `get_user_info`
- Cada ferramenta recebe `actor_context` (perfil + session token) injetado pelo runtime, não pelo modelo
- Endpoint `POST /api/agent/chat` recebe `{ session_token, message }`, executa loop ReAct, retorna `{ response, trace }`
- Trace inclui todos os pensamentos, tool calls com argumentos e tool returns para cada turno
- Limite de 10 iterações por turno; ultrapassagem retorna erro estruturado
- Conversação stateful via Redis por session_token
- System prompt em `app/agents/variant_a/system_prompt.py` com instruções de papel, ferramentas e políticas

**Done when:** `curl -X POST localhost:8000/api/agent/chat -d '{"session_token":"...", "message":"buscar tênis preto"}'` retorna resposta natural com trace mostrando uso de `search_products`; pedir reembolso de pedido alheio é negado com motivo registrado no trace.

---

## Fase 5 — Variante B: agente Llama via Groq API

**Goal:** Variante B funcionalmente equivalente à A, usando Llama 3.1 8B via Groq.

- Cliente Groq configurado via SDK OpenAI-compatible (`base_url=https://api.groq.com/openai/v1`)
- Mesmo registro de ferramentas e mesmo schema de tool calling da Variante A
- Endpoint `POST /api/agent/chat?variant=b` ou header `X-Variant: b` seleciona o caminho
- System prompt idêntico ao da Variante A (diferenças vão ser observadas no comportamento, não no prompt)
- Tratamento de rate limit: retry com backoff exponencial em caso de 429 do Groq
- Tratamento de tool calls divergentes do schema: rejeição estruturada com mensagem de erro retornada ao agente
- Suite de smoke tests `tests/test_variant_parity.py`: para 10 prompts benignos, ambas as variantes precisam invocar a mesma ferramenta principal

**Done when:** suíte de smoke tests passa com Variante A e B; mesma mensagem `"meu último pedido"` produz tool call equivalente em ambas, retornando o mesmo registro do banco.

---

## Fase 6 — Variante C: pipeline multi-model

**Goal:** Variante C com Llama Guard 3 (pré-filtro), Llama 3.1 8B (raciocínio), Presidio (output filter).

- Estágio 1: Llama Guard 3 via Groq classifica input do usuário. Categorias `unsafe` rejeitam request com 400 + motivo
- Estágio 2: Llama 3.1 8B via Groq executa o loop ReAct (mesmo código da Variante B)
- Estágio 3: output do agente passa pelo Presidio Analyzer (container local) com policies para PII brasileira (CPF, CNPJ, telefone, email) + entidades customizadas (`PAYMENT_TOKEN`, `INTERNAL_SECRET`)
- Detecções de PII no output disparam redação (substituição por `<REDACTED:TYPE>`) ou bloqueio total, configurável por nível de severidade
- Log estruturado em cada estágio: input → llama_guard_verdict → agent_trace → presidio_findings → final_response
- Endpoint `POST /api/agent/chat?variant=c` ou header `X-Variant: c`
- Suite de smoke tests `tests/test_variant_c_pipeline.py`: input com PII no payload é detectado no estágio 1; output que vazaria PII é redacted no estágio 3

**Done when:** suíte de smoke tests passa; uma mensagem benigna passa pelos três estágios e retorna resposta normal com trace completo dos três estágios; um payload "ignore previous instructions" é bloqueado no estágio 1.

---

## Fase 7 — Red team baseline: prompt injection + insecure output

**Goal:** executar 2 das 6 categorias da matriz contra as 3 variantes, sem defesas extras. Estabelecer pipeline de evidências.

- Harness customizada `red_team/harness.py` que recebe `(variant, attack_category, payload)`, executa, persiste em `evidence/baseline/`
- Estrutura JSON por evidência: `{ id, timestamp, variant, category, technique, payload, response, success_flag, trace }`
- Critério de `success_flag` definido por categoria (heurística + verificação manual amostral de 10%)
- **Prompt injection direta:** 20 payloads conhecidos (DAN, "ignore previous", role-play, ArtPrompt, persona modulation)
- **Prompt injection indireta:** 10 produtos envenenados com payloads em título/descrição; ataque consiste em pedir ao agente que liste produtos relevantes
- **Insecure output handling:** 15 payloads visando XSS em respostas (`<script>`, event handlers), SQL via tool calling, SSRF via URLs construídas
- Execução paralela com rate limit do Groq respeitado (semáforo de 30 req/min)
- Notebook `notebooks/01_baseline_pi_ioh.ipynb` carrega evidências, calcula attack success rate por (variante, categoria), gera tabela inicial da matriz

**Done when:** matriz parcial 3×2 (variantes × 2 categorias) preenchida com pelo menos 45 evidências por célula; notebook gera heatmap dos resultados.

---

## Fase 8 — Red team completo: 4 categorias restantes

**Goal:** completar a matriz baseline com model theft, sensitive disclosure, insecure plugin, excessive agency.

- **Model theft (black-box):** probing comportamental (50 queries de mesma intenção, medir consistência), surrogate model training (treinar GPT-2 fine-tuned com 500 pares query/response coletados de cada variante), system prompt extraction (10 técnicas conhecidas)
- **Sensitive information disclosure:** extração de PII de outros usuários via prompt injection (10 cenários), tentativa de extrair system prompt (5 técnicas), extração de credenciais de API via tool chaining (5 cenários)
- **Insecure plugin design:** TOCTOU em `process_refund` (validar status entre check e execute), parâmetros não validados em `send_message` (recipient_id arbitrário), confused deputy via tool chaining
- **Excessive agency:** comprador comum acionando ferramentas administrativas via injeção (10 cenários), cross-actor impersonation (5 cenários), logic-chain injection para escalada
- **Apêndice white-box (GPT-2 small):** scripts em `red_team/whitebox/` que rodam GCG (sufixo adversarial) e MIA simplificado contra GPT-2 carregado via Transformers; resultados separados em `evidence/whitebox/`
- Notebook `notebooks/02_baseline_complete.ipynb` consolida toda a matriz 3×6 baseline + apêndice white-box

**Done when:** matriz 3×6 baseline completa com pelo menos 30 evidências por célula; apêndice white-box mostra GCG funcionando em GPT-2 (sufixo encontrado, exemplo de bypass); notebook exporta tabela em CSV para uso no relatório.talvez

---

## Fase 9 — Defesas em profundidade

**Goal:** implementar defesas por camada e re-executar a matriz inteira.

### Camada de input
- Sanitização de entrada: strip de caracteres de controle, normalização Unicode (NFKC)
- Separação prompt/dados via delimitadores explícitos (`<USER_INPUT>...</USER_INPUT>`) no system prompt
- Detector de perplexidade via GPT-2 local: requests acima de threshold são logados e rejeitados
- Integração com Rebuff: heurísticas conhecidas + canary tokens

### Camada de output
- Schema validation: tool calls são re-validados via Pydantic antes de execução
- Sandboxing de execução de ferramentas: ferramentas executam em contexto com `actor_context` injetado, sem acesso ao raw input do modelo
- Filtro Presidio (já existe na Variante C) generalizado para opt-in nas Variantes A e B

### Camada de plugin
- Allow-list explícita de ferramentas por perfil de ator (comprador não pode chamar `process_refund` de pedido de outro usuário)
- Confirmação humana exigida para ações destrutivas (`process_refund` > R$ 500): agente retorna `requires_confirmation: true`
- Logs de auditoria estruturados em `audit_log` para toda chamada de ferramenta

### Anti-theft
- Rate limit por session_token: máximo 60 requests/hora ao endpoint do agente
- Query budget tracking: padrões de probing (queries muito similares em sequência curta) disparam cooldown progressivo
- Output perturbation deferida para post-MVP (depende de acesso a logits, não disponível em Groq)

### Disclosure
- Data classification layer: antes de retornar resposta, classifica conteúdo em `public`, `internal`, `pii`, `secret`; tipos sensíveis são redacted ou bloqueados conforme política

### Re-execução
- Toda a matriz 3×6 é re-executada com defesas ativadas; resultados persistidos em `evidence/post_defense/`
- Notebook `notebooks/03_post_defense.ipynb` calcula redução de attack success rate por célula e gera comparativo baseline vs pós-defesa

**Done when:** todas as 5 camadas de defesa implementadas e cobertas por testes unitários; matriz pós-defesa completa; notebook gera tabela de redução percentual por (variante, categoria).

---

## Fase 10 — Threat model e análise arquitetural

**Goal:** consolidar análise comparativa formal para o relatório.

- Documento `report/threat_model.md` com STRIDE aplicado a:
  - 4 atores (comprador, vendedor, suporte, atacante externo)
  - 3 arquiteturas (A, B, C)
- Diagrama de fluxo da Variante C identificando estágios e propagação potencial de ataques entre eles
- Análise de vulnerabilidades compostas no pipeline multi-model: 3 cenários documentados onde injeção sobrevive a Llama Guard mas é capturada por Presidio, e vice-versa
- Matriz de risco residual: para cada (variante, categoria), score CVSS v3.1 base e contextualizado para payments
- Trade-off analysis: tabela comparando A, B, C em latência média, custo operacional estimado por 1M requests, complexidade de operação
- Mapeamento explícito de cada vulnerabilidade encontrada para impacto de negócio em payments: account takeover, vendor impersonation, chargeback fraud, regulatory non-compliance

**Done when:** `report/threat_model.md` está completo com diagramas, matriz CVSS preenchida, tabela de trade-offs e mapeamento de impacto. Documento revisado para garantir que cada finding na matriz 3×6 tem entrada correspondente no threat model.

---

## Fase 11 — Relatório executivo

**Goal:** produzir o relatório de auditoria pronto para revisão de liderança técnica em payments.

- Estrutura final do `report/SECURITY_AUDIT.md`:
  - Executive summary (1 página) com top 5 findings, redução agregada de risco, recomendações priorizadas
  - Contexto e escopo
  - Threat model resumido (linka para `threat_model.md`)
  - Matriz 3×6 baseline vs pós-defesa (heatmap visual)
  - Análise arquitetural comparativa (A vs B vs C)
  - Findings detalhados por categoria com causa raiz, evidência, impacto, remediação
  - Risco residual quantificado por arquitetura
  - Remediações priorizadas (CVSS + impacto de negócio)
  - Apêndice técnico: catálogo de técnicas, white-box em GPT-2, decisões arquiteturais
- Notebook consolidado `notebooks/00_audit_report.ipynb` gera todas as visualizações usadas no relatório
- Conversão para PDF via Pandoc (`make report-pdf`)
- Revisão final: leitura completa para garantir ausência de jargão desnecessário; cada afirmação tem evidência referenciada

**Done when:** `report/SECURITY_AUDIT.md` está completo; PDF gerado sem erros; uma leitura externa (você mesmo após 24h de distância) consegue navegar do executive summary aos detalhes técnicos sem ambiguidade.

---

## Fase 12 — Publicação e portfólio

**Goal:** projeto publicado e configurado como item de portfólio profissional.

- README do repositório raiz com: missão em 3 parágrafos, badges (CI, license, docs), diagrama da arquitetura, instruções de setup, link para o relatório, créditos
- LICENSE definida (sugestão: MIT para o código, CC BY 4.0 para o relatório)
- Repositório tornado público no GitHub
- Tag de release `v1.0.0` criada apontando para o commit final
- Post no LinkedIn como projeto de portfólio:
  - Título: "LLM Security: Vulnerabilities and Defense Patterns — Applied AI Engineering Specialization"
  - Descrição de 200 palavras com escopo, achados principais, stack e link
  - Imagem com heatmap da matriz 3×6 (do notebook)
- Entrada no perfil LinkedIn em "Projetos"

**Done when:** link público do repositório acessível, README renderiza corretamente no GitHub, relatório PDF baixável; post no LinkedIn publicado com link funcional.

---

## Post-MVP (Adiados)

Os seguintes itens estão explicitamente fora do escopo da entrega inicial (Fases 1–12):

- **Upgrade para Llama 3.3 70B** na Variante C — depende de tier pago do Groq ou contraparte; cenário "mais próximo de produção" mas que confunde a variável experimental
- **GPU cloud para white-box completo em Llama 3.1 8B** — US$ 5–10 de RunPod ou Vast.ai para GCG/MIA rigoroso; opcional se quisermos resultados white-box mais robustos
- **Fine-tuning para demonstração de backdoor** — exige Together AI (Groq não oferece fine-tuning); fica como demonstração avançada se houver tempo
- **Output perturbation como defesa quantificável** — depende de acesso a logits; inviável com Groq, faria sentido com modelo self-hosted
- **Multi-tenant e múltiplos marketplaces simulados** — escopo expandido para análise comparativa entre verticais de payments
- **Ataques multimodais** — exigiriam variantes com modelos visão+texto; fora do enunciado original
- **Ataques em tempo de treinamento** (data poisoning, sleeper agents) — exigem acesso ao pipeline de treinamento; entram apenas como recomendação de governança no relatório
- **Suite Garak + PyRIT exaustiva** — versão MVP usa subconjunto curado; execução completa com todos os probes fica como follow-up
- **Avaliação econômica detalhada** — cálculo de TCO por arquitetura com cenários de tráfego de produção
- **Webhook de notificação para findings críticos** durante o red team — útil se o projeto virar serviço contínuo
- **Integração com MITRE ATLAS** — mapeamento completo dos findings para o framework, em complemento ao CVSS

---

*Documento vivo · v1 · revisado a cada conclusão de fase*