.PHONY: help setup dev prod test lint clean

help:
	@echo "PerfectTradingStrategy Commands"
	@echo "  make setup    - Install all dependencies"
	@echo "  make dev      - Start development environment"
	@echo "  make prod     - Start production services"
	@echo "  make test     - Run all tests"
	@echo "  make lint     - Run linters"
	@echo "  make clean    - Clean up"

setup:
	cd backend && python3 -m venv venv && . venv/bin/activate && pip install -r requirements.txt
	cd frontend && npm install
	cp -n .env.example .env 2>/dev/null || true
	@echo "Setup complete. Edit .env with your configuration."

dev:
	@echo "Starting development environment..."
	docker-compose -f docker/docker-compose.yml up -d postgres redis
	cd backend && . venv/bin/activate && uvicorn main:app --reload --port 8000 &
	cd frontend && npm run dev &
	@echo "Backend: http://localhost:8000"
	@echo "Frontend: http://localhost:3000"

prod:
	docker-compose -f docker/docker-compose.yml up --build -d

test:
	cd backend && . venv/bin/activate && python -m pytest tests/ -v --cov=. --cov-report=term-missing

lint:
	cd backend && . venv/bin/activate && pip install flake8 black isort && isort . && black . && flake8 .
	cd frontend && npx tsc --noEmit

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf backend/venv frontend/node_modules .coverage htmlcov

chmod-scripts:
	chmod +x scripts/*.sh
