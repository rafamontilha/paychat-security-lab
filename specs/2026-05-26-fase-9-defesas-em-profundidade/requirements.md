# Requirements — Fase 9: Defesas em profundidade

## Scope

### In scope

- Composição de um `DefensePipeline` plugável a partir dos adaptadores em
  `app/infrastructure/defenses/`, consumindo a porta `DefenseLayer` (ADR-001)
- Cinco camadas de defesa implementadas e cobertas por testes unitários:
  - **Input**: sanitização (strip de controle + NFKC), separação prompt/dados por delimitadores,
    detector de perplexidade GPT-2, Rebuff (heurísticas + canary tokens)
  - **Output**: re-validação de tool calls via Pydantic, sandboxing com `actor_context`,
    filtro Presidio generalizado para **opt-in nas Variantes A e B**
  - **Plugin**: allow-list de ferramentas por perfil, **confirmação humana em `process_refund` > R$ 500**,
    audit log por chamada de ferramenta
  - **Anti-theft**: rate limit de 60 req/h por `session_token`, query budget com cooldown progressivo
  - **Disclosure**: data classification (`public`/`internal`/`pii`/`secret`) com redação ou bloqueio
- Opt-in de defesa por variante via configuração injetada por construção (A e B; C mantém pipeline próprio)
- Re-execução da matriz 3×6 com defesas ativas; evidências em `evidence/post_defense/`
- `notebooks/03_post_defense.ipynb` com cálculo de redução percentual de ASR por (variante, categoria)

### Out of scope

- **Output perturbation** (ruído em logits / truncamento) — deferido para post-MVP: os provedores
  gerenciados (Together AI e Anthropic) não expõem logits e Claude é black-box; inviável sem modelo
  self-hosted (ver roadmap, seção Post-MVP)
- Threat model STRIDE, scoring CVSS e impacto de negócio — Fase 10
- Relatório executivo e visualizações finais — Fase 11
- Novas categorias de ataque ou novos payloads — o conjunto da matriz 3×6 é o da Fase 8
- Substituição do modelo open-source por Llama 3.3 70B — decisão revisitável, fora desta fase

## Key Decisions

| Decisão | Escolha | Rationale |
|---------|---------|-----------|
| Sequenciamento | Por camada, na ordem do roadmap (input → output → plugin → anti-theft → disclosure → re-execução) | Cada camada testada antes da próxima; reduz acoplamento e facilita atribuir redução de ASR a uma camada específica |
| Plugabilidade | Defesas compostas em `DefensePipeline` que implementa a porta `DefenseLayer` | ADR-001: harness e runtime consomem a porta; ativar/desativar defesa é flag de config, não branch de código |
| Opt-in A e B | Defesas ativadas por configuração injetada por construção; C inalterada | Permite matriz com e sem defesa por variante sem duplicar pipeline; preserva paridade experimental |
| Output perturbation | **Excluído** desta fase | Depende de acesso a logits, indisponível em Together AI/Claude; manter como recomendação no relatório |
| Detector de perplexidade local (GPT-2) coexistindo com a stack | Lazy-load do GPT-2, execução **serial** e budget de RAM avaliado antes da re-execução | Máquina tem ~7.4 GB; durante a re-execução o Docker (api/db/redis/chroma/presidio) precisa estar no ar junto com o GPT-2 — não dá para fechar o Docker como na Fase 8 (white-box). Ritual de liberação: suspender apps não-críticos do Windows, pausar sync do OneDrive |
| Confirmação humana | `process_refund` > R$ 500 retorna `requires_confirmation: true` em vez de executar | Defesa direta contra excessive agency; LangGraph suporta interrupção human-in-the-loop |
| Canary tokens | Injetados no system prompt; vazamento na resposta marca tentativa de extração | Detecta system-prompt leakage sem heurística frágil de string-matching no input |
| Re-execução | Mesmo `EvidenceRecord` e mesma harness da Fase 8, apenas com pipeline de defesa ativo | Schema uniforme garante comparabilidade baseline vs pós-defesa célula a célula |

## Context

### Mission alignment

A Fase 9 entrega o **Entregável 2 — Defense Pattern Implementation** da especialização: padrões de
defense in depth para cada vulnerabilidade da matriz, com **redução mensurável de attack success rate**
e quantificação de risco residual. É o pilar do critério Distinction — "defense patterns demonstram
redução mensurável de ASR". Honra os princípios *security by design*, *red team first* (toda defesa
responde a um ataque documentado na Fase 8) e *defense in depth* (camadas independentes).

### Tech-stack alignment

- **Defesas**: adaptadores já existem em `app/infrastructure/defenses/` (`llama_guard.py`, `presidio.py`,
  `rebuff.py`, `rate_limiter.py`, `policy.py`); esta fase os compõe e generaliza para opt-in
- **Porta `DefenseLayer`**: `check_input(text) -> (allowed, reason)` e `filter_output(text) -> text`
  já definidos em `app/domain/ports/defense_layer.py`
- **Provedores em runtime**: Variante A via Anthropic API (Claude); Variantes B e C via **Together AI**
  (`LLM_BASE_URL=https://api.together.xyz/v1`, agente Llama 3.1 8B Turbo, guard Llama-Guard-4-12B).
  Together tem rate limit dinâmico — a throttle real da re-execução é a RAM local, não a API
- **Redis 7**: sustenta rate limit por sessão e query budget tracking
- **Presidio**: container local já usado na Variante C; generalizado para opt-in em A e B
- **Perplexidade (GPT-2 local)**: GPT-2 small via Transformers, mesmo modelo do apêndice white-box.
  Cabe na RTX 3050 (4 GB VRAM), mas na re-execução roda junto com a stack Docker (~7.4 GB de RAM total) —
  lazy-load + execução serial; budget de RAM avaliado antes de rodar a matriz
- **Notebook**: `notebooks/03_post_defense.ipynb` já existe como esqueleto; esta fase o preenche
- **Evidências**: `evidence/post_defense/` já criado; schema `EvidenceRecord` reaproveitado da Fase 8

### Dependencies

- **Fase 8 concluída**: matriz 3×6 baseline em `evidence/baseline/` é o ponto de comparação obrigatório
- **Variantes A, B, C operacionais**: `POST /api/agent/chat?variant={a,b,c}` (Fases 4, 5, 6)
- **Harness e `EvidenceRecord`**: `red_team/harness.py` operacional (Fases 7 e 8)
- **Audit log**: tabela `audit_log` e middleware de logging estruturado (Fase 2)
- **Seed data**: usuários por perfil necessários para validar allow-list e cross-actor (Fase 2)
