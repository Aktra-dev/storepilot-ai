#!/bin/bash
# ============================================
# StorePilot AI — Production Startup Script
# Untuk Railway / Render / Fly.io
# ============================================

echo "🚀 StorePilot AI — Starting production..."
echo "============================================"

# 1. Run migrations
echo "📦 Running database migrations..."
alembic upgrade head || {
    echo "⚠️  Alembic failed, falling back to create_all..."
    python -c "
from app.core.database import Base, engine
from app import models_registry
Base.metadata.create_all(bind=engine)
print('✅ Tables created via create_all()')
"
}

# 2. Seed data (hanya jika tabel kosong)
echo "🌱 Checking if database needs seeding..."
python -c "
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
engine = create_engine(settings.DATABASE_URL)
Session = sessionmaker(bind=engine)
db = Session()
try:
    result = db.execute(text('SELECT COUNT(*) FROM users'))
    count = result.scalar()
    if count == 0:
        print('  Database empty, seeding...')
        import subprocess
        subprocess.run(['python', 'scripts/seed.py'], check=True)
    else:
        print(f'  Database has {count} users, skipping seed.')
finally:
    db.close()
"

# 3. Start server
echo "🌐 Starting uvicorn..."
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
