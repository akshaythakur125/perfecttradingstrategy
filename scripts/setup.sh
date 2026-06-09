#!/usr/bin/env bash
set -euo pipefail

echo "=== PerfectTradingStrategy Setup ==="

# Check prerequisites
command -v python3 >/dev/null 2>&1 || { echo "Python 3 is required"; exit 1; }
command -v node >/dev/null 2>&1 || { echo "Node.js is required"; exit 1; }
command -v npm >/dev/null 2>&1 || { echo "npm is required"; exit 1; }

# Backend setup
echo ""
echo "--- Backend Setup ---"
cd "$(dirname "$0")/../backend"

if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "Virtual environment created"
fi

source venv/bin/activate
pip install -q -r requirements.txt
echo "Backend dependencies installed"

# Frontend setup
echo ""
echo "--- Frontend Setup ---"
cd "$(dirname "$0")/../frontend"

if [ ! -d "node_modules" ]; then
    npm install
    echo "Frontend dependencies installed"
fi

# Environment file
echo ""
echo "--- Environment Configuration ---"
cd "$(dirname "$0")/.."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo ".env file created from .env.example"
    echo "Please edit .env with your configuration"
fi

echo ""
echo "=== Setup Complete ==="
echo ""
echo "To start the backend:"
echo "  cd backend && source venv/bin/activate && uvicorn main:app --reload --port 8000"
echo ""
echo "To start the frontend:"
echo "  cd frontend && npm run dev"
echo ""
echo "To run tests:"
echo "  cd backend && source venv/bin/activate && pytest tests/ -v"
