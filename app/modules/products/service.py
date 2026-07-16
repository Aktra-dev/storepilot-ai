"""
Product Master Data — business logic (CRUD).

Handles all database operations for products: create, read, update, delete,
list with filtering/pagination, and SKU uniqueness validation.
"""

import uuid
from typing import List, Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundException, ValidationException
from app.modules.products.models import Product
from app.modules.products.schemas import ProductCreate, ProductUpdate


class ProductService:
    """Product CRUD operations."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, data: ProductCreate) -> Product:
        """Create a new product."""
        existing = self.db.query(Product).filter(Product.sku == data.sku).first()
        if existing:
            raise ValidationException(f"Product with SKU '{data.sku}' already exists")

        product = Product(
            id=uuid.uuid4(),
            sku=data.sku,
            name=data.name,
            category=data.category,
            minimum_stock=data.minimum_stock,
        )
        self.db.add(product)
        self.db.commit()
        self.db.refresh(product)
        return product

    def get(self, product_id: uuid.UUID) -> Product:
        """Get a product by ID."""
        product = self.db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise NotFoundException(f"Product {product_id} not found")
        return product

    def get_by_sku(self, sku: str) -> Optional[Product]:
        """Get a product by SKU. Returns None if not found."""
        return self.db.query(Product).filter(Product.sku == sku).first()

    def get_list(
        self,
        skip: int = 0,
        limit: int = 100,
        category: Optional[str] = None,
        search: Optional[str] = None,
    ) -> tuple[List[Product], int]:
        """
        List products with optional filtering and pagination.
        Returns (list of products, total count).
        """
        query = self.db.query(Product)

        if category:
            query = query.filter(Product.category == category)
        if search:
            pattern = f"%{search}%"
            query = query.filter(
                or_(
                    Product.sku.ilike(pattern),
                    Product.name.ilike(pattern),
                )
            )

        total = query.count()
        products = query.order_by(Product.created_at.desc()).offset(skip).limit(limit).all()
        return products, total

    def list_all(self) -> List[Product]:
        """List all products (for dropdowns, etc.)."""
        return self.db.query(Product).order_by(Product.name).all()

    def update(self, product_id: uuid.UUID, data: ProductUpdate) -> Product:
        """Update a product."""
        product = self.get(product_id)

        if data.sku is not None:
            existing = self.db.query(Product).filter(
                Product.sku == data.sku,
                Product.id != product_id,
            ).first()
            if existing:
                raise ValidationException(f"Product with SKU '{data.sku}' already exists")
            product.sku = data.sku

        if data.name is not None:
            product.name = data.name
        if data.category is not None:
            product.category = data.category
        if data.minimum_stock is not None:
            product.minimum_stock = data.minimum_stock

        self.db.commit()
        self.db.refresh(product)
        return product

    def delete(self, product_id: uuid.UUID) -> None:
        """Delete a product."""
        product = self.get(product_id)
        self.db.delete(product)
        self.db.commit()

    def search(self, query: str) -> List[Product]:
        """Search products by name or SKU (for autocomplete)."""
        pattern = f"%{query}%"
        return (
            self.db.query(Product)
            .filter(
                or_(
                    Product.sku.ilike(pattern),
                    Product.name.ilike(pattern),
                )
            )
            .order_by(Product.name)
            .limit(20)
            .all()
        )
