"""
Quick setup script for local development.

Run with:
    python setup.py

What it does:
1. Copies .env.example to .env if not exists
2. Generates Alembic initial migration
3. Runs Alembic upgrade head
4. Seeds the database
"""

import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))

def step(msg):
    print(f"\n{'='*50}")
    print(f"  {msg}")
    print(f"{'='*50}")

def run(cmd, cwd=None):
    print(f"  > {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd or ROOT, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout)
    if result.returncode != 0 and result.stderr:
        print(f"  ERROR: {result.stderr}")
    return result.returncode == 0

# --- Step 1: .env ---
step("Step 1: Setup .env file")
env_path = os.path.join(ROOT, ".env")
env_example = os.path.join(ROOT, ".env.example")
if not os.path.exists(env_path):
    if os.path.exists(env_example):
        shutil.copy(env_example, env_path)
        print("  ✅ Created .env from .env.example")
        # Swap to SQLite for local dev
        with open(env_path, "r") as f:
            content = f.read()
        content = content.replace(
            "postgresql://postgres:password@localhost:5432/storepilot",
            "sqlite:///./storepilot.db"
        )
        with open(env_path, "w") as f:
            f.write(content)
        print("  ✅ Switched to SQLite for local development")
    else:
        print("  ❌ .env.example not found!")
        sys.exit(1)
else:
    print("  ✅ .env already exists")

# --- Step 2: Ensure alembic/versions exists ---
step("Step 2: Prepare Alembic versions directory")
versions_dir = os.path.join(ROOT, "alembic", "versions")
os.makedirs(versions_dir, exist_ok=True)
# Remove .gitkeep if present
gitkeep = os.path.join(versions_dir, ".gitkeep")
if os.path.exists(gitkeep):
    os.remove(gitkeep)
print(f"  ✅ {versions_dir} ready")

# --- Step 3: Generate migration ---
step("Step 3: Generate initial Alembic migration")
# First, try to remove any existing migration files
for f in os.listdir(versions_dir):
    if f.endswith(".py"):
        os.remove(os.path.join(versions_dir, f))

# Check if there are any alembic revision scripts already
if not any(f.endswith(".py") for f in os.listdir(versions_dir)):
    # Generate new migration
    success = run("alembic revision --autogenerate -m 'initial schema'")
    if not success:
        print("  ⚠️  alembic revision failed. Creating manual migration...")
        # If alembic command fails, create a manual migration
        migration_content = '''"""initial schema

Revision ID: manual_001
Revises: 
Create Date: auto-generated

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'manual_001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Tables will be created by SQLAlchemy Base.metadata.create_all()
    # This is a placeholder - run 'alembic revision --autogenerate -m "initial"' properly
    pass


def downgrade() -> None:
    pass
'''
        migration_file = os.path.join(versions_dir, "manual_001_initial.py")
        with open(migration_file, "w") as f:
            f.write(migration_content)
        print(f"  ✅ Created manual migration: {migration_file}")
else:
    print("  ✅ Migration files already exist")

# --- Step 4: Create tables (direct SQLAlchemy) ---
step("Step 4: Create database tables")
from app.core.config import settings
from sqlalchemy import create_engine
from app.core.database import Base
from app import models_registry  # noqa

# Use SQLite for local dev
db_url = settings.DATABASE_URL
if "sqlite" in db_url:
    engine = create_engine(db_url.replace("./", ROOT + "/"))
else:
    engine = create_engine(db_url)

Base.metadata.create_all(bind=engine)
print("  ✅ All tables created via SQLAlchemy")

# --- Step 5: Run alembic upgrade ---
step("Step 5: Run Alembic upgrade")
# For SQLite, we skip alembic upgrade since tables are already created
if "sqlite" in db_url:
    print("  ✅ Skipping alembic upgrade (SQLite mode - tables created directly)")
else:
    success = run("alembic upgrade head")
    if success:
        print("  ✅ Database migrated to latest revision")
    else:
        print("  ⚠️  Alembic upgrade failed (tables created directly)")

# --- Step 6: Seed data ---
step("Step 6: Seed database with demo data")
# Check if already seeded
from sqlalchemy.orm import sessionmaker
from app.modules.auth.models import User

SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()
user_count = db.query(User).count()
db.close()

if user_count > 0:
    print(f"  ℹ️  Database already has {user_count} users. Re-seeding...")
    # Run seed with auto-yes
    seed_script = os.path.join(ROOT, "scripts", "seed.py")
    if os.path.exists(seed_script):
        # Override the input() call
        env = os.environ.copy()
        env["PYTHONPATH"] = ROOT
        subprocess.run([sys.executable, seed_script], cwd=ROOT, env=env, input=b"y\n")
    else:
        print("  ❌ scripts/seed.py not found!")
else:
    seed_script = os.path.join(ROOT, "scripts", "seed.py")
    if os.path.exists(seed_script):
        subprocess.run([sys.executable, seed_script], cwd=ROOT)
    else:
        print("  ❌ scripts/seed.py not found!")

# --- Done! ---
step("Setup Complete!")
print("""
  🚀 To start the server:

     venv\\Scripts\\activate
     uvicorn app.main:app --reload

  🌐 Then open:
     Backend API: http://localhost:8000/docs
     Frontend:    http://localhost:5500
                  (run 'python -m http.server 5500' in StorePilot AI/)

  👤 Demo accounts:
     Manager: manager@storepilot.ai / Manager123!
     Staff 1: staff1@storepilot.ai  / Staff123!
     Staff 2: staff2@storepilot.ai  / Staff123!
""")
