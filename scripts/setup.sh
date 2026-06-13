#!/bin/bash
# FitIntel Pro — Quick Setup Script
# Usage: ./scripts/setup.sh [dev|prod]

set -e

ENV=${1:-dev}
echo "=== FitIntel Pro Setup ($ENV) ==="

# Check Python
python3 --version || { echo "Python 3.12+ required"; exit 1; }

# Create virtualenv
if [ ! -d ".venv" ]; then
    echo "Creating virtualenv..."
    python3 -m venv .venv
fi
source .venv/bin/activate

# Install deps
echo "Installing dependencies..."
pip install -q -r requirements.txt

# Create .env if not exists
if [ ! -f ".env" ]; then
    echo "Creating .env from example..."
    cp .env.example .env
fi

# Start services via docker-compose
if command -v docker-compose &> /dev/null || command -v docker &> /dev/null; then
    echo "Starting PostgreSQL & Redis..."
    docker compose -f docker-compose.yml up -d db redis
    sleep 5
fi

# Run migrations
echo "Running migrations..."
alembic upgrade head

# Seed data
echo "Seeding roles and permissions..."
python -c "
from app.db.session import SessionLocal
from app.db.seed.seed_permissions import seed_permissions
from app.db.seed.seed_roles import seed_roles
from app.db.seed.seed_admin import seed_admin
db = SessionLocal()
try:
    seed_permissions(db)
    seed_roles(db)
    seed_admin(db)
    db.commit()
    print('Seed completed')
except Exception as e:
    db.rollback()
    print(f'Seed error (may already exist): {e}')
finally:
    db.close()
"

echo ""
echo "=== Setup complete ==="
echo "Run: uvicorn app.main:app --reload"
echo "Swagger: http://localhost:8000/docs"
