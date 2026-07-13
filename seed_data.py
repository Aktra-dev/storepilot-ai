"""
Seed script — inserts sample/demo data covering the full pipeline: a
manager user, products, inventory, sales, one operational analysis with
a finding, a generated task, and a pending approval.

Usage (after create_tables.py has run):
    python seed_data.py

Safe to re-run — it checks for existing rows by unique fields (email,
sku) before inserting, so it won't create duplicates.
"""

import hashlib
from datetime import date, timedelta

from app import models_registry  # noqa: F401
from app.core.database import SessionLocal
from app.modules.approvals.models import Approval, ApprovalStatus
from app.modules.auth.models import User, UserRole
from app.modules.inventory.models import Inventory
from app.modules.operational_analysis.models import (
    AnalysisStatus,
    FindingType,
    OperationalAnalysis,
    OperationalFinding,
    Severity,
)
from app.modules.products.models import Product
from app.modules.sales.models import Sale
from app.modules.tasks.models import Task, TaskPriority, TaskStatus


def hash_password(raw_password: str) -> str:
    # NOTE: placeholder only. Replace with a real hashing library
    # (e.g. passlib[bcrypt]) once the auth module is actually implemented.
    return hashlib.sha256(raw_password.encode()).hexdigest()


def main() -> None:
    db = SessionLocal()
    try:
        # --- Manager user ---
        manager = db.query(User).filter_by(email="manager@storepilot.ai").first()
        if not manager:
            manager = User(
                name="Budi Manager",
                email="manager@storepilot.ai",
                password_hash=hash_password("password123"),
                role=UserRole.MANAGER,
            )
            db.add(manager)
            db.flush()
            print("Created user: manager@storepilot.ai")

        # --- Products ---
        product_seed = [
            {"sku": "SKU-001", "name": "Indomie Goreng", "category": "Food", "minimum_stock": 20},
            {"sku": "SKU-002", "name": "Aqua 600ml", "category": "Beverage", "minimum_stock": 30},
            {"sku": "SKU-003", "name": "Roti Tawar", "category": "Bakery", "minimum_stock": 10},
        ]
        products = {}
        for data in product_seed:
            product = db.query(Product).filter_by(sku=data["sku"]).first()
            if not product:
                product = Product(**data)
                db.add(product)
                db.flush()
                print(f"Created product: {data['sku']}")
            products[data["sku"]] = product

        # --- Inventory (one batch per product for this demo) ---
        today = date.today()
        inventory_seed = [
            {"sku": "SKU-001", "quantity": 5, "expiry_date": today + timedelta(days=30)},
            {"sku": "SKU-002", "quantity": 50, "expiry_date": None},
            {"sku": "SKU-003", "quantity": 8, "expiry_date": today + timedelta(days=2)},
        ]
        for data in inventory_seed:
            product = products[data["sku"]]
            existing = db.query(Inventory).filter_by(product_id=product.id).first()
            if not existing:
                db.add(
                    Inventory(
                        product_id=product.id,
                        quantity=data["quantity"],
                        expiry_date=data["expiry_date"],
                    )
                )
                print(f"Created inventory record for: {data['sku']}")

        # --- Sales (5 days of history for SKU-001, used by stockout calc) ---
        if db.query(Sale).count() == 0:
            for days_ago in range(5):
                db.add(
                    Sale(
                        product_id=products["SKU-001"].id,
                        quantity=5,
                        total_amount=15000 * 5,
                        sale_date=today - timedelta(days=days_ago),
                    )
                )
            print("Created 5 sample sales records for SKU-001")

        db.flush()

        # --- Operational analysis + finding + task + approval (demo pipeline) ---
        if db.query(OperationalAnalysis).count() == 0:
            analysis = OperationalAnalysis(
                status=AnalysisStatus.COMPLETED,
                summary="Demo run: 1 stockout risk detected on SKU-001.",
                ai_provider="fallback",
            )
            db.add(analysis)
            db.flush()

            finding = OperationalFinding(
                analysis_id=analysis.id,
                finding_type=FindingType.STOCKOUT,
                product_id=products["SKU-001"].id,
                severity=Severity.HIGH,
                title="Indomie Goreng hampir habis",
                description=(
                    "Stok tersisa 5 unit, estimasi habis dalam 1 hari "
                    "berdasarkan rata-rata penjualan 5 hari terakhir."
                ),
                confidence=0.9,
            )
            db.add(finding)
            db.flush()

            task = Task(
                finding_id=finding.id,
                title="Reorder Indomie Goreng",
                description="Ajukan pemesanan ulang minimal 30 unit sebelum akhir minggu.",
                priority=TaskPriority.HIGH,
                assigned_role="staff",
                status=TaskStatus.PENDING,
            )
            db.add(task)
            db.flush()

            db.add(
                Approval(
                    task_id=task.id,
                    manager_id=manager.id,
                    status=ApprovalStatus.PENDING,
                )
            )
            print("Created 1 operational_analysis -> 1 finding -> 1 task -> 1 approval")

        db.commit()
        print("\nSeed data inserted successfully.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
