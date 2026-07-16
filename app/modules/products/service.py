"""
Product Master Data — business logic (CRUD).

Handles all database operations for products: create, read, update, delete,
list with filtering/pagination, and SKU uniqueness validation.
"""

import uuid
from typing import Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundException, ValidationException
from app.modules.products.models import Product
from app.modules.products.schemas import (
    ProductCreate,
    ProductListParams,
    ProductUpdate,
)


class ProductService:
    """Product CRUD operations."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, data: ProductCreate) -> Product:
        """
        Create a new product.

        Raises:
            ValidationException: If SKU already exists.
        """
        # Check SKU uniqueness
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
        """
        Get a product by ID.

        Raises:
            NotFoundException: If product not found.
        """
        product = self.db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise NotFoundException(f"Product {product_id} not found")
        return product

    def get_by_sku(self, sku: str) -> Optional[Product]:
        """
        Get a product by SKU.

        Returns None if not found (no exception raised).
        """
        return self.db.query(Product).filter(Product.sku == sku).first()

    def list(
        self,
        skip: int = 0,
        limit: int = 100,
        category: Optional[str] = None,
        search: Optional[str] = None,
    ) -> tuple[list[Product], int]:
        """
        List products with optional filtering and pagination.

        Returns:
            Tuple of (list of products, total count)
        """
        query = self.db.query(Product)

        # Filter by category
        if category:
            query = query.filter(Product.category == category)

        # Search by SKU or name
        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                or_(
                    Product.sku.ilike(search_pattern),
                    Product.name.ilike(search_pattern),
                )
            )

        # Get total before pagination
        total = query.count()

        # Apply pagination
        products = query.order_by(Product.created_at.desc()).offset(skip).limit(limit).all()

        return products, total

    def list_all(self) -> list[Product]:
        """List all products (for dropdowns, etc.)."""
        return self.db.query(Product).order_by(Product.name).all()

    def update(self, product_id: uuid.UUID, data: ProductUpdate) -> Product:
        """
        Update a product.

        Raises:
            NotFoundException: If product not found.
            ValidationException: If SKU conflicts with another product.
        """
        product = self.get(product_id)

        # Update SKU if provided
        if data.sku is not None:
            existing = self.db.query(Product).filter(
                Product.sku == data.sku,
                Product.id != product_id,
            ).first()
            if existing:
                raise ValidationException(f"Product with SKU '{data.sku}' already exists")
            product.sku = data.sku

        # Update other fields
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
        """
        Delete a product.

        Note: This is a hard delete. Consider implementing soft-delete
        if product has related records (sales, inventory, findings).

        Raises:
            NotFoundException: If product not found.
        """
        product = self.get(product_id)
        self.db.delete(product)
        self.db.commit()

    def search(self, query: str) -> list[Product]:
        """
        Search products by name or SKU (for autocomplete, etc.).
        """
        search_pattern = f"%{query}%"
        return (
            self.db.query(Product)
            .filter(
                or_(
                    Product.sku.ilike(search_pattern),
                    Product.name.ilike(search_pattern),
                )
            )
            .order_by(Product.name)
            .limit(20)
            .all()
        )
