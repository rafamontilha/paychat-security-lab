# Plan — Fase 9: Defesas em profundidade

Sequência por camada, na ordem do roadmap. Cada camada é implementada como adaptador da
porta `DefenseLayer` (ADR-001), coberta por testes unitários e ativável via configuração
antes de passar à próxima. A re-execução da matriz só começa após as 5 camadas prontas.

## 1. Camada de input
- [ ] Compor `DefensePipeline` a partir dos adaptadores existentes em `app/infrastructure/defenses/`, consumindo a porta `DefenseLayer` (`check_input` / `filter_output`)
- [ ] Flag de configuração de defesa por variante (opt-in para A e B; C já tem pipeline próprio) injetada por construção, sem singleton
- [ ] Sanitização de entrada: strip de caracteres de controle + normalização Unicode NFKC
- [ ] Separação prompt/dados via delimitadores explícitos `<USER_INPUT>...</USER_INPUT>` no system prompt das variantes
- [ ] Avaliar budget de RAM: GPT-2 local + stack Docker (api/db/redis/chroma/presidio) coexistindo em ~7.4 GB; documentar ritual de liberação (suspender apps não-críticos, pausar sync do OneDrive) — Docker NÃO pode ser fechado durante a re-execução
- [ ] Detector de perplexidade via GPT-2 local (lazy-load, execução serial): requests acima do threshold são logados e rejeitados
- [ ] Integração Rebuff (`defenses/rebuff.py`): heurísticas de injeção conhecidas + canary tokens injetados no prompt para detectar leakage
- [ ] Testes unitários: sanitização, threshold de perplexidade, disparo de canary token

## 2. Camada de output
- [ ] Re-validação de tool calls via Pydantic antes da execução (schema validation)
- [ ] Sandboxing de ferramentas: execução com `actor_context` injetado pelo runtime, sem acesso ao raw input do modelo
- [ ] Generalizar filtro Presidio (`defenses/presidio.py`, hoje só na Variante C) para opt-in nas Variantes A e B via `filter_output`
- [ ] Testes unitários: rejeição de tool call fora do schema; redação de PII no output em A/B com Presidio ativo

## 3. Camada de plugin
- [ ] Allow-list explícita de ferramentas por perfil de ator (comprador não chama `process_refund` de pedido alheio)
- [ ] Confirmação humana para ação destrutiva: `process_refund` > R$ 500 retorna `requires_confirmation: true`
- [ ] Log de auditoria estruturado em `audit_log` para toda chamada de ferramenta
- [ ] Testes unitários: allow-list nega ferramenta fora do perfil; refund acima do limite exige confirmação

## 4. Camada anti-theft
- [ ] Rate limit por `session_token` sobre Redis: máximo 60 requests/hora ao endpoint do agente (`defenses/rate_limiter.py`)
- [ ] Query budget tracking: padrões de probing (queries muito similares em sequência curta) disparam cooldown progressivo
- [ ] Testes unitários: limite de 60/h bloqueia o 61º request; cooldown progressivo em sequência de queries similares

## 5. Camada de disclosure
- [ ] Data classification layer: classifica conteúdo da resposta em `public` / `internal` / `pii` / `secret` antes de retornar
- [ ] Tipos sensíveis (`pii`, `secret`) são redacted ou bloqueados conforme política em `defenses/policy.py`
- [ ] Testes unitários: cada classe é detectada; política redige ou bloqueia conforme severidade

## 6. Re-execução da matriz e notebook
- [ ] Re-executar a matriz 3×6 completa com defesas ativadas, **serial** (limite real é a RAM local, não a API Together AI); usar runner seguro com restart/health-check entre batches
- [ ] Persistir evidências em `evidence/post_defense/` com o mesmo schema `EvidenceRecord` do baseline
- [ ] Preencher `notebooks/03_post_defense.ipynb`: carregar baseline + pós-defesa, calcular redução de attack success rate por célula
- [ ] Gerar tabela de redução percentual por (variante, categoria) e comparativo baseline vs pós-defesa
