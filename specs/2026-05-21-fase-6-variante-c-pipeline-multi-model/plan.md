# Plan — Fase 6: Variante C — Pipeline Multi-Model

Sequência: estágio por estágio. Cada estágio é implementado e testado isoladamente antes de montar o pipeline completo. Isso preserva a capacidade de debugar um estágio sem ruído dos outros e garante que cada adaptador pode ser reutilizado na Fase 9.

## 1. Llama Guard client e classificador

- [ ] Criar `app/infrastructure/agents/variant_c/llama_guard_client.py` com função `classify_input(text: str) -> GuardVerdict`
- [ ] `GuardVerdict` é um dataclass/Pydantic model: `{ safe: bool, category: str | None, raw_response: str }`
- [ ] Cliente usa o SDK OpenAI-compatible (mesma instância da Variante B) apontando para `llama-guard-3-1b` no Groq
- [ ] Tratar timeout e erro 5xx com `fail_closed=True`: lançar `GuardUnavailableError` em vez de deixar passar
- [ ] Teste unitário `tests/unit/test_llama_guard_client.py` com mock do Groq: input seguro → `safe=True`, input com S2 → `safe=False, category="S2"`

## 2. Reutilização do AgentRuntime da Variante B

- [ ] Confirmar que `GroqAgentRuntime` da Variante B é instanciado por composição na Variante C — nenhuma linha copiada
- [ ] Criar `app/infrastructure/agents/variant_c/pipeline.py` com classe `MultiModelPipeline` que recebe `guard_client`, `agent_runtime`, `presidio_client` por injeção
- [ ] `MultiModelPipeline.run(input, actor_context)` executa os três estágios em sequência e retorna `PipelineResponse`
- [ ] `PipelineResponse` inclui campos: `response`, `trace` (lista de `TraceStep`), `guard_verdict`, `presidio_findings`
- [ ] Confirmar que os 7 campos originais de `TraceStep` estão preservados; adicionar tipos novos opcionais: `guard_verdict` e `presidio_findings` ao Literal

## 3. Presidio output filter e recognizers customizados

- [ ] Criar `app/infrastructure/agents/variant_c/presidio_client.py` com função `analyze_and_redact(text: str) -> RedactionResult`
- [ ] `RedactionResult`: `{ redacted_text: str, findings: list[PresidioFinding], blocked: bool }`
- [ ] Registrar recognizers customizados: `PAYMENT_TOKEN` (regex Luhn 16 dígitos) e `INTERNAL_SECRET` (prefixos definidos no seed)
- [ ] Criar `app/infrastructure/agents/variant_c/policy.py` com tabela `ENTITY_POLICY: dict[str, Literal["redact", "block"]]` — CPF/CNPJ/telefone/email → `"redact"`, PAYMENT_TOKEN/INTERNAL_SECRET → `"block"`
- [ ] Cliente HTTP chama o container Presidio Analyzer em `http://presidio:5002/analyze`
- [ ] Tratar container down com `fail_closed=True`: lançar `PresidioUnavailableError`
- [ ] Testes unitários `tests/unit/test_presidio_client.py`: CPF em texto → redacted; PAYMENT_TOKEN → blocked; texto limpo → sem alteração
- [ ] Teste de recognizer customizado direto contra Presidio (sem agente): PAYMENT_TOKEN e INTERNAL_SECRET detectados com threshold documentado

## 4. Orquestrador do pipeline e política de falha

- [ ] Implementar sequência em `MultiModelPipeline.run`:
  1. Chamar `guard_client.classify_input(input)` → se `safe=False`, retornar imediatamente com `GuardBlockedError`
  2. Chamar `agent_runtime.run(input, actor_context)` → obter `AgentResponse` com trace
  3. Chamar `presidio_client.analyze_and_redact(agent_response.response)` → aplicar política
  4. Montar `PipelineResponse` com trace completo dos 3 estágios
- [ ] Garantir fail-closed: `GuardUnavailableError` → propaga como 503; `PresidioUnavailableError` → propaga como 503
- [ ] Teste de integração com mocks `tests/integration/test_pipeline_orchestration.py`: timeout no Guard → 503; Presidio down → 503; fluxo feliz → trace com os 3 estágios presentes

## 5. Endpoint, log estruturado e smoke tests

- [ ] Adicionar roteamento `?variant=c` / `X-Variant: c` no `POST /api/agent/chat` (mesmo padrão da Variante B)
- [ ] Log estruturado por request: `{ input, llama_guard_verdict, agent_trace, presidio_findings, final_response }` persistido em `evidence/` com timestamp e session_token
- [ ] Atualizar `/health` (ou adicionar `/health/deep`) com verificação de conectividade ao container Presidio
- [ ] Escrever `tests/test_variant_c_pipeline.py` cobrindo os 3 caminhos obrigatórios (ver Validation)
- [ ] Atualizar `README.md`: adicionar Variante C na tabela de variantes e menção explícita ao container Presidio no setup
- [ ] Registrar ADR se `TraceStep` tiver recebido novos tipos de step
