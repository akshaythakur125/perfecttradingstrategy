#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

MODE="${1:-dev}"

case "$MODE" in
  dev)
    echo "Starting development environment..."
    # Start dependencies
    cd "$PROJECT_DIR"
    docker-compose -f docker/docker-compose.yml up -d postgres redis

    # Start backend
    cd "$PROJECT_DIR/backend"
    if [ ! -d "venv" ]; then
        python3 -m venv venv
    fi
    source venv/bin/activate
    pip install -q -r requirements.txt
    uvicorn main:app --reload --port 8000 &
    BACKEND_PID=$!

    # Start frontend
    cd "$PROJECT_DIR/frontend"
    if [ ! -d "node_modules" ]; then
        npm install
    fi
    npm run dev &
    FRONTEND_PID=$!

    echo ""
    echo "Backend:  http://localhost:8000"
    echo "Frontend: http://localhost:3000"
    echo ""
    echo "Press Ctrl+C to stop"

    trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT
    wait
    ;;

  prod)
    echo "Starting production environment..."
    cd "$PROJECT_DIR"
    docker-compose -f docker/docker-compose.yml up --build -d
    echo "Services started. Backend: http://localhost:8000"
    ;;

  test)
    echo "Running tests..."
    cd "$PROJECT_DIR/backend"
    if [ ! -d "venv" ]; then
        python3 -m venv venv
    fi
    source venv/bin/activate
    pip install -q -r requirements.txt
    python -m pytest tests/ -v --cov=. --cov-report=term-missing
    ;;

  *)
    echo "Usage: $0 {dev|prod|test}"
    exit 1
    ;;
esac
