#!/usr/bin/env python
"""
Seed database with sample data for development/testing.

Run with:
    python scripts/seed.py

Creates:
- 1 Manager user
- 2 Staff users
- 10 Products with categories
- Inventory records (stock + expiry)
- 30 days of sales history
"""

import uuid
from datetime import date, timedelta
from decimal import Decimal
import random

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add project root to path
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.core.database import Base
from app.core.config import settings
from app import models_registry  # noqa: F401
from app.modules.auth.models import User, UserRole
from app.modules.products.models import Product
from app.modules.inventory.models import Inventory
from app.modules.sales.models import Sale
from app.core.security import hash_password

# Sample data
CATEGORIES = ["Minuman", "Makanan", "Snack", "ATK", "Kebersihan", "Frozen", "Sembako"]

PRODUCTS_DATA = [
    {"sku": "MIN-001", "name": "Aqua 600ml", "category": "Minuman", "min_stock": 50},
    {"sku": "MIN-002", "name": "Teh Botol Sosro 400ml", "category": "Minuman", "min_stock": 30},
    {"sku": "MIN-003", "name": "Pocari Sweat 500ml", "category": "Minuman", "min_stock": 20},
    {"sku": "MKN-001", "name": "Indomie Goreng", "category": "Makanan", "min_stock": 100},
    {"sku": "MKN-002", "name": "Nasi Goreng Instan", "category": "Makanan", "min_stock": 40},
    {"sku": "SNK-001", "name": "Chitato Sapi Panggang", "category": "Snack", "min_stock": 60},
    {"sku": "SNK-002", "name": "Tango Wafer Coklat", "category": "Snack", "min_stock": 40},
    {"sku": "ATK-001", "name": "Pulpen Standard Hitam", "category": "ATK", "min_stock": 200},
    {"sku": "KBR-001", "name": "Sabun Mandi Cair", "category": "Kebersihan", "min_stock": 25},
    {"sku": "FRZ-001", "name": "Kentang Goreng Frozen 1kg", "category": "Frozen", "min_stock": 15},
]


def create_users(db):
    """Create sample users."""
    print("Creating users...")
    
    # Manager
    manager = User(
        id=uuid.uuid4(),
        name="Budi Manager",
        email="manager@storepilot.ai",
        password_hash=hash_password("Manager123!"),
        role=UserRole.MANAGER,
    )
    db.add(manager)
    
    # Staff
    staff1 = User(
        id=uuid.uuid4(),
        name="Siti Staff",
        email="staff1@storepilot.ai",
        password_hash=hash_password("Staff123!"),
        role=UserRole.STAFF,
    )
    db.add(staff1)
    
    staff2 = User(
        id=uuid.uuid4(),
        name="Andi Staff",
        email="staff2@storepilot.ai",
        password_hash=hash_password("Staff123!"),
        role=UserRole.STAFF,
    )
    db.add(staff2)
    
    db.commit()
    print(f"  Created: 1 manager, 2 staff")
    return [manager, staff1, staff2]


def create_products(db):
    """Create sample products."""
    print("Creating products...")
    
    products = []
    for p in PRODUCTS_DATA:
        product = Product(
            id=uuid.uuid4(),
            sku=p["sku"],
            name=p["name"],
            category=p["category"],
            minimum_stock=p["min_stock"],
        )
        db.add(product)
        products.append(product)
    
    db.commit()
    print(f"  Created: {len(products)} products")
    return products


def create_inventory(db, products):
    """Create inventory records with stock and expiry dates."""
    print("Creating inventory...")
    
    inventories = []
    for product in products:
        # Create 1-3 batches per product
        num_batches = random.randint(1, 3)
        for i in range(num_batches):
            # Expiry date: some near, some far, some None (non-perishable)
            if product.category in ["Frozen", "Minuman", "Makanan"]:
                days_to_expiry = random.randint(3, 90)
                expiry = date.today() + timedelta(days=days_to_expiry)
            else:
                expiry = None
            
            # Stock quantity - some low (below min), some normal, some high
            stock_level = random.choices(
                ["low", "normal", "high"], 
                weights=[0.2, 0.6, 0.2]
            )[0]
            
            if stock_level == "low":
                qty = random.randint(0, product.minimum_stock)
            elif stock_level == "high":
                qty = random.randint(product.minimum_stock * 3, product.minimum_stock * 5)
            else:
                qty = random.randint(product.minimum_stock + 1, product.minimum_stock * 3)
            
            inv = Inventory(
                id=uuid.uuid4(),
                product_id=product.id,
                quantity=qty,
                expiry_date=expiry,
            )
            db.add(inv)
            inventories.append(inv)
    
    db.commit()
    print(f"  Created: {len(inventories)} inventory records")
    return inventories


def create_sales(db, products, days=30):
    """Create 30 days of sales history."""
    print(f"Creating {days} days of sales history...")
    
    sales = []
    today = date.today()
    
    for day_offset in range(days):
        sale_date = today - timedelta(days=day_offset)
        
        # More sales on weekends
        is_weekend = sale_date.weekday() >= 5
        base_transactions = random.randint(8, 15) if is_weekend else random.randint(3, 8)
        
        for _ in range(base_transactions):
            product = random.choice(products)
            qty = random.randint(1, 5)
            
            # Price based on category
            base_prices = {
                "Minuman": (3000, 8000),
                "Makanan": (2500, 10000),
                "Snack": (5000, 15000),
                "ATK": (2000, 25000),
                "Kebersihan": (8000, 30000),
                "Frozen": (20000, 50000),
                "Sembako": (10000, 50000),
            }
            min_price, max_price = base_prices.get(product.category, (5000, 20000))
            unit_price = random.randint(min_price, max_price)
            
            sale = Sale(
                id=uuid.uuid4(),
                product_id=product.id,
                quantity=qty,
                total_amount=unit_price * qty,
                sale_date=sale_date,
            )
            db.add(sale)
            sales.append(sale)
    
    db.commit()
    print(f"  Created: {len(sales)} sale records")
    return sales


def main():
    print("=" * 50)
    print("Seeding StorePilot AI Database")
    print("=" * 50)
    
    # Create engine
    engine = create_engine(settings.DATABASE_URL)
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        # Check if already seeded
        existing_users = db.query(User).count()
        if existing_users > 0:
            response = input(f"\nDatabase already has {existing_users} users. Re-seed? (y/N): ")
            if response.lower() != 'y':
                print("Seeding cancelled.")
                return
            else:
                print("\nClearing old data...")
                # Delete in correct order (foreign key dependencies)
                from app.modules.sales.models import Sale
                from app.modules.inventory.models import Inventory
                from app.modules.products.models import Product
                from app.modules.approvals.models import Approval
                from app.modules.tasks.models import Task
                from app.modules.operational_analysis.models import OperationalAnalysis, OperationalFinding
                db.query(Sale).delete()
                db.query(Approval).delete()
                db.query(Task).delete()
                db.query(OperationalFinding).delete()
                db.query(OperationalAnalysis).delete()
                db.query(Inventory).delete()
                db.query(Product).delete()
                db.query(User).delete()
                db.commit()
                print("  Old data cleared.")
        
        # Seed data
        users = create_users(db)
        products = create_products(db)
        inventories = create_inventory(db, products)
        sales = create_sales(db, products, days=30)
        
        print("\n" + "=" * 50)
        print("✅ Seeding complete!")
        print("=" * 50)
        print("\nDemo accounts:")
        print("  Manager: manager@storepilot.ai / Manager123!")
        print("  Staff 1: staff1@storepilot.ai / Staff123!")
        print("  Staff 2: staff2@storepilot.ai / Staff123!")
        print("\nRun tests:")
        print("  python -m pytest tests/ -v")
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()