# Requirements — Fase 2: Marketplace base

## Scope

### In scope

- Schema PostgreSQL via SQLAlchemy 2.0: tabelas `users`, `products`, `orders`, `messages`, `transactions`, `sessions`, `audit_log`
- Migrations versionadas via Alembic no repositório
- Seed script `scripts/seed.py`: 50 usuários (4 perfis), 100 produtos, 200 pedidos, 50 transações com tokens Luhn válidos, PII fictícia em locale `pt_BR`
- Endpoints REST mínimos com autenticação via header e sessão Redis: auth, products, orders, users, messages, refunds
- RBAC mínimo declarado por endpoint; rejeições retornam 403
- Middleware de audit log estruturado em todos os endpoints (exceto `/health`)

### Out of scope

- RAG e embeddings — Fase 3
- Dados "envenenados" para indirect injection — Fase 3
- Agente ReAct e tool calling — Fases 4–6
- Defesas (Llama Guard, Rebuff, Presidio) — Fase 9
- Frontend ou UI — fora do escopo total do projeto

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Migrations | Alembic versionado no repositório | Garante que qualquer clone limpo reconstrói o schema com `alembic upgrade head`; reprodutibilidade é merge blocker |
| Autenticação simulada | Header `Authorization: Bearer <session_token>` + Redis | Sem JWT real — escopo mínimo para sustentar ataques; Redis já no Compose da Fase 1 |
| RBAC | Dependência FastAPI por endpoint declarando perfis permitidos | Simples, auditável e suficiente para os cenários de excessive agency e insecure plugin design das Fases 7–8 |
| PII fictícia | Faker `pt_BR` para CPF, email, telefone | Dados sintéticos realistas sem expor dados reais; CPF e telefone são os formatos que o Presidio precisará detectar na Fase 6 |
| Tokens de pagamento | Luhn-válidos no campo `payment_token` de `transactions` | Vetor central para sensitive information disclosure; tokens com formato válido tornam o ataque mais realista do que strings aleatórias |
| Seed idempotente | Verificar existência ou truncar antes de popular | Permite reexecutar `seed.py` sem duplicar dados entre iterações de desenvolvimento |

## Context

### Mission alignment

A Fase 2 entrega o "alvo" sobre o qual toda a matriz 3×6 opera. Sem um marketplace funcional com usuários, produtos, pedidos e transações reais (ainda que sintéticos), nenhum dos ataques das Fases 7–8 tem superfície de ataque concreta. O critério Distinction exige documentação de causa raiz para cada vulnerabilidade — isso pressupõe que o sistema base seja determinístico e reproduzível.

### Tech-stack alignment

- **FastAPI 0.115 + Pydantic v2:** validação de schema nos endpoints é a camada de defesa passiva que o baseline (Fase 7) deve contornar para evidenciar insecure output handling
- **PostgreSQL 16 + pgcrypto:** extensão `pgcrypto` disponível para geração de tokens; SQLAlchemy 2.0 com parametrização automática previne SQL injection no baseline (diferença mensurável na Fase 9)
- **Redis 7:** já orquestrado no Compose; usado para sessões e será reutilizado na Fase 9 para rate limiting e query budget
- **Alembic:** padrão com SQLAlchemy 2.0; migrations versionadas são requisito de reprodutibilidade do roadmap

### Dependencies

- **Fase 1 concluída:** todos os containers (`db`, `redis`, `chroma`, `presidio`, `api`) sobem via `docker compose up`; `GET /health` retorna 200; variáveis de ambiente em `.env` configuradas
- Nenhuma dependência de Fases 3–6
