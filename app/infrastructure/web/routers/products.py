from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.infrastructure.persistence.database import get_db
from app.infrastructure.persistence.models import Product
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
