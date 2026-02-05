.PHONY: all dev-backend dev-frontend build install clean test

# Default target
all: install build

# Install dependencies
install:
	@echo "Installing Python dependencies..."
	pip install -r ui/backend/requirements.txt
	@echo "Installing frontend dependencies..."
	cd ui/frontend && npm install

# Development servers
dev-backend:
	@echo "Starting FastAPI backend on http://localhost:8000"
	cd ui && uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend:
	@echo "Starting Vite dev server on http://localhost:5173"
	cd ui/frontend && npm run dev

# Run both dev servers (requires two terminals)
dev:
	@echo "Run these in separate terminals:"
	@echo "  make dev-backend"
	@echo "  make dev-frontend"

# Build production frontend
build:
	@echo "Building frontend..."
	cd ui/frontend && npm run build

# Run tests
test:
	@echo "Running Python tests..."
	python -m pytest -q

# Clean build artifacts
clean:
	@echo "Cleaning..."
	rm -rf ui/frontend/dist
	rm -rf ui/frontend/node_modules
	rm -rf ui_runs
	rm -rf __pycache__
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

# Production server (static + API)
prod:
	@echo "Build first: make build"
	@echo "Then serve with: uvicorn ui.backend.main:app --host 0.0.0.0 --port 8000"

# Type checking
typecheck:
	cd ui/frontend && npx tsc --noEmit

# Lint
lint:
	cd ui/frontend && npm run lint
