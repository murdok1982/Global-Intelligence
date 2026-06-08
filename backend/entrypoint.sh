#!/bin/bash
set -e
echo "Running database migrations..."
alembic upgrade head
echo "Seeding military database..."
python -m scripts.seed_military_data || echo "Seed completed or already seeded"
echo "Starting server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2
