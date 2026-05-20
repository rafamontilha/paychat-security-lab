#!/usr/bin/env python
# ruff: noqa: E402, I001
"""Seed script — populates the database with synthetic data for red team experiments."""

import random
import secrets
import sys
from pathlib import Path

# Allow running as `python scripts/seed.py` from repo root
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

from sqlalchemy.orm import Session as OrmSession  # noqa: E402

from app.infrastructure.persistence.database import get_engine  # noqa: E402
from app.infrastructure.persistence.models import (  # noqa: E402
    AuditLog,
    Message,
    Order,
    OrderStatus,
    Product,
    Role,
    Session as DbSession,
    Transaction,
    User,
)

try:
    from faker import Faker
except ImportError:
    sys.exit("Run: uv sync --group dev")

fake = Faker("pt_BR")
random.seed(42)
fake.seed_instance(42)

CATEGORIES = ["Eletrônicos", "Moda", "Casa", "Esportes", "Livros", "Brinquedos"]

PROFILE_COUNTS = {
    Role.buyer: 30,
    Role.seller: 12,
    Role.support: 5,
    Role.admin: 3,
}


def _luhn_token(length: int = 16) -> str:
    digits = [random.randint(0, 9) for _ in range(length - 1)]
    total = 0
    for i, d in enumerate(reversed(digits)):
        if i % 2 == 0:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    check = (10 - total % 10) % 10
    digits.append(check)
    return "".join(map(str, digits))


def _format_card(raw: str) -> str:
    return "-".join(raw[i : i + 4] for i in range(0, 16, 4))


def seed(db: OrmSession) -> None:
    # Idempotency: clear existing data respecting FK constraints
    for model in [AuditLog, Transaction, Message, DbSession, Order, Product, User]:
        db.query(model).delete()
    db.commit()

    # Users
    users: dict[Role, list[User]] = {role: [] for role in Role}
    for role, count in PROFILE_COUNTS.items():
        for _ in range(count):
            cpf = fake.cpf()
            u = User(
                name=fake.name(),
                cpf=cpf,
                email=fake.unique.email(),
                phone=fake.phone_number()[:20],
                api_key=secrets.token_hex(16),
                role=role,
            )
            db.add(u)
            users[role].append(u)
    db.flush()

    # Products (100)
    products: list[Product] = []
    for _ in range(100):
        seller = random.choice(users[Role.seller])
        p = Product(
            title=fake.catch_phrase(),
            description=fake.text(max_nb_chars=200),
            price=round(random.uniform(10.0, 2000.0), 2),
            category=random.choice(CATEGORIES),
            seller_id=seller.id,
        )
        db.add(p)
        products.append(p)
    db.flush()

    # Orders (200)
    orders: list[Order] = []
    statuses = (
        [OrderStatus.pending] * 80 + [OrderStatus.completed] * 80 + [OrderStatus.disputed] * 40
    )
    random.shuffle(statuses)
    for i in range(200):
        buyer = random.choice(users[Role.buyer])
        product = random.choice(products)
        o = Order(
            buyer_id=buyer.id,
            product_id=product.id,
            status=statuses[i],
            amount=float(product.price),
        )
        db.add(o)
        orders.append(o)
    db.flush()

    # Transactions (50) — Luhn-valid payment tokens
    completed_orders = [
        o for o in orders if o.status in (OrderStatus.completed, OrderStatus.disputed)
    ]
    tx_orders = random.sample(completed_orders, min(50, len(completed_orders)))
    for o in tx_orders:
        raw = _luhn_token(16)
        t = Transaction(
            order_id=o.id,
            payment_token=_format_card(raw),
            amount=o.amount,
        )
        db.add(t)

    # Messages — at least 1 per disputed order
    disputed = [o for o in orders if o.status == OrderStatus.disputed]
    for o in disputed:
        buyer = db.get(User, o.buyer_id)
        seller = db.get(User, db.get(Product, o.product_id).seller_id)
        msg = Message(
            sender_id=buyer.id,
            recipient_id=seller.id,
            content=f"Tenho um problema com o pedido #{o.id}. {fake.sentence()}",
        )
        db.add(msg)

    db.commit()

    total_users = sum(PROFILE_COUNTS.values())
    print("Seed concluído:")
    counts = ", ".join(f"{r.value}={c}" for r, c in PROFILE_COUNTS.items())
    print(f"  {total_users} usuários ({counts})")
    print(f"  {len(products)} produtos")
    print(f"  {len(orders)} pedidos")
    print(f"  {len(tx_orders)} transações com tokens Luhn")
    print(f"  {len(disputed)} mensagens de disputa")
    print()
    print("API keys de exemplo para smoke tests:")
    for role in [Role.buyer, Role.admin, Role.support]:
        u = users[role][0]
        print(f"  {role.value:8s}  api_key={u.api_key}  user_id={u.id}")


if __name__ == "__main__":
    from sqlalchemy.orm import sessionmaker

    engine = get_engine()
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with SessionLocal() as db:
        seed(db)
