import chromadb
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.infrastructure.persistence.database import get_db
from app.infrastructure.persistence.models import Product, Role
from app.infrastructure.rag.client import get_chroma_client
from app.infrastructure.rag.ingest import ingest_single_product
from app.infrastructure.web.dependencies import ActorContext

router = APIRouter(prefix="/api/products", tags=["products"])


class ProductOut(BaseModel):
    id: int
    title: str
    description: str
    price: float
    category: str
    seller_id: int

    model_config = {"from_attributes": True}


class ProductCreate(BaseModel):
    title: str
    description: str
    price: float
    category: str


@router.get("", response_model=list[ProductOut])
def list_products(
    actor: ActorContext,
    search: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    q = db.query(Product)
    if search:
        q = q.filter(Product.title.ilike(f"%{search}%"))
    return q.all()


@router.get("/{product_id}", response_model=ProductOut)
def get_product(
    product_id: int,
    actor: ActorContext,
    db: Session = Depends(get_db),
):
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return product


@router.post("", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
def create_product(
    body: ProductCreate,
    actor: ActorContext,
    db: Session = Depends(get_db),
    chroma: chromadb.ClientAPI = Depends(get_chroma_client),
):
    if actor["role"] not in (Role.seller.value, Role.admin.value):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only sellers and admins can create products",
        )
    product = Product(
        title=body.title,
        description=body.description,
        price=body.price,
        category=body.category,
        seller_id=actor["user_id"],
    )
    db.add(product)
    db.commit()
    db.refresh(product)

    # Hook: upsert into ChromaDB immediately (intentionally unsanitised — RAG poisoning vector)
    ingest_single_product(chroma, product)
    return product
