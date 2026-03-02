#!/bin/bash
# Run database migration for new Lead and DataCaptureQuestion models

set -e

echo "🔄 Running database migration..."
echo ""

# Method 1: Using Docker (if backend is running)
if docker-compose ps | grep -q "backend.*Up"; then
    echo "✓ Backend container is running"
    echo "Running migration via Docker..."
    docker-compose exec backend alembic upgrade head
    echo ""
    echo "✅ Migration complete!"
else
    # Method 2: Using local Python (if venv exists)
    if [ -f "backend/.venv/bin/activate" ]; then
        echo "✓ Using local Python environment"
        cd backend
        source .venv/bin/activate
        alembic upgrade head
        echo ""
        echo "✅ Migration complete!"
    else
        echo "❌ Backend is not running and no local venv found"
        echo ""
        echo "Please either:"
        echo "  1. Start backend: docker-compose up -d backend"
        echo "  2. Or create venv: cd backend && python -m venv .venv && pip install -r requirements.txt"
        exit 1
    fi
fi

echo ""
echo "📊 New tables created:"
echo "  • leads - Lead-level data aggregation"
echo "  • data_capture_questions - Tenant-configurable questions"
