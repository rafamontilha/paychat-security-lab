# Plan — Fase 2: Marketplace base

## 1. Schema e migrations

- [ ] Criar `app/domain/entities/user.py`, `product.py`, `order.py`, `transaction.py`, `session.py`, `message.py` com modelos Pydantic (entidades de domínio puras)
- [ ] Criar `app/infrastructure/persistence/models.py` com classes SQLAlchemy 2.0 declarativas para todas as tabelas: `users`, `products`, `orders`, `messages`, `transactions`, `sessions`, `audit_log`
- [ ] Incluir coluna `payment_token` em `transactions` como texto no formato Luhn válido (gerado via `pgcrypto` no seed)
- [ ] Inicializar Alembic: `alembic init migrations`
- [ ] Configurar `alembic.ini` para usar `DATABASE_URL` do `.env`
- [ ] Gerar e revisar migration inicial: `alembic revision --autogenerate -m "initial schema"`
- [ ] Validar que `alembic upgrade head` cria todas as tabelas sem erro

## 2. Seed script

- [ ] Criar `scripts/seed.py` com Faker configurado para locale `pt_BR`
- [ ] Gerar 50 usuários distribuídos em 4 perfis: `buyer` (30), `seller` (12), `support` (5), `admin` (3)
- [ ] Para cada usuário: nome, CPF fictício (`fake.cpf()`), email, telefone, API key gerada (`secrets.token_hex(16)`)
- [ ] Gerar 100 produtos com `seller_id` apontando para usuários `seller`; campos: título, descrição, preço, categoria, `created_at`
- [ ] Gerar 200 pedidos com `buyer_id` e `product_id` válidos; campos: status (`pending`, `completed`, `disputed`), valor, `created_at`
- [ ] Gerar 50 transações com `payment_token` em formato Luhn válido (usar biblioteca `luhn` ou implementar gerador simples); associar a pedidos existentes
- [ ] Gerar mensagens de amostra entre compradores e vendedores (mínimo 1 por pedido `disputed`)
- [ ] Seed idempotente: verificar existência antes de inserir ou truncar tabelas antes de popular
- [ ] Validar que `python scripts/seed.py` conclui sem erro e imprime contagens inseridas

## 3. Endpoints REST

- [ ] **Auth:** `POST /api/auth/login` — recebe `{ "api_key": "..." }`, valida contra tabela `users`, retorna `{ "session_token": "...", "role": "..." }`; sessão armazenada no Redis com TTL de 1 hora
- [ ] **Produtos:**
  - `GET /api/products` — lista todos, suporta query param `?search=` para filtro simples por título
  - `GET /api/products/{id}` — retorna produto por ID ou 404
- [ ] **Pedidos:**
  - `GET /api/orders` — lista pedidos do usuário autenticado (comprador vê os próprios; admin vê todos)
  - `GET /api/orders/{id}` — retorna pedido por ID respeitando RBAC; 403 se não autorizado
- [ ] **Usuários:** `GET /api/users/{id}` — requer perfil `support` ou `admin`; 403 para compradores e vendedores
- [ ] **Mensagens:** `POST /api/messages` — recebe `{ "recipient_id": int, "content": str }`; sender inferido do session token
- [ ] **Reembolsos:** `POST /api/refunds` — recebe `{ "order_id": int }`; requer ownership do pedido ou perfil `admin`; 403 caso contrário
- [ ] Middleware de autenticação: extrair `session_token` do header `Authorization: Bearer <token>`, injetar `actor_context` em cada request
- [ ] RBAC por endpoint: decorador ou dependência FastAPI que declara perfis permitidos e rejeita com 403

## 4. Middleware de audit log

- [ ] Criar `app/infrastructure/web/middleware/audit_log.py` como middleware Starlette
- [ ] Registrar em `audit_log` para toda requisição: `timestamp`, `session_token`, `user_id`, `role`, `method`, `path`, `status_code`, `request_body` (truncado a 500 chars), `response_time_ms`
- [ ] Excluir `GET /health` do log para não poluir auditoria
- [ ] Validar que após a sequência de smoke test manual, `audit_log` contém entradas para cada chamada realizada
