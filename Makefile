# ==============================================================================
# Klerno Labs - Development Makefile
# ==============================================================================
# Simplify common development tasks with make commands

.PHONY: help setup install run dev test lint format typecheck clean docker-build docker-run

# Default target
help: ## Show this help message
	@echo "Klerno Labs - Development Commands"
	@echo "=================================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

# Setup and Installation
setup: ## Set up development environment with virtual environment
	@echo "Setting up Klerno Labs development environment..."
	python -m venv .venv
	@echo "Virtual environment created. Activate with:"
	@echo "  source .venv/bin/activate  # Linux/Mac"
	@echo "  .venv\\Scripts\\activate     # Windows"

install: ## Install all dependencies
	@echo "Installing dependencies..."
	pip install --upgrade pip
	pip install -r requirements.txt
	@echo "✓ Dependencies installed"

install-dev: ## Install development dependencies
	@echo "Installing development dependencies..."
	pip install --upgrade pip
	pip install -r requirements.txt
	pip install pre-commit
	pre-commit install
	@echo "✓ Development dependencies installed"

# Running the Application
run: ## Run the application in development mode
	@echo "Starting Klerno Labs application..."
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev: ## Run with development settings and auto-reload
	@echo "Starting Klerno Labs in development mode..."
	TESTING=true uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 --log-level debug

prod: ## Run in production mode
	@echo "Starting Klerno Labs in production mode..."
	uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

# Testing
test: ## Run all tests
	@echo "Running tests..."
	pytest tests/ -v

test-health: ## Run health check tests only
	@echo "Running health check tests..."
	pytest tests/test_health.py -v

test-coverage: ## Run tests with coverage report
	@echo "Running tests with coverage..."
	pytest tests/ --cov=app --cov-report=html --cov-report=term -v
	@echo "Coverage report generated in htmlcov/"

test-watch: ## Run tests in watch mode
	@echo "Running tests in watch mode..."
	pytest-watch tests/ -- -v

# Code Quality
lint: ## Run all linting tools
	@echo "Running linting tools..."
	ruff check .
	flake8 app/ tests/ --max-line-length=100 --extend-ignore=E203,W503
	@echo "✓ Linting completed"

format: ## Format code with black and isort
	@echo "Formatting code..."
	black app/ tests/
	isort app/ tests/
	ruff format .
	@echo "✓ Code formatted"

format-check: ## Check code formatting without modifying
	@echo "Checking code formatting..."
	black --check app/ tests/
	isort --check-only app/ tests/
	ruff format --check .

typecheck: ## Run type checking with mypy
	@echo "Running type checking..."
	mypy app/ --ignore-missing-imports --no-strict-optional

security: ## Run security scans
	@echo "Running security scans..."
	bandit -r app/ -f json -o bandit-report.json
	pip-audit --desc
	@echo "✓ Security scan completed"

quality: lint typecheck security ## Run all code quality checks

# Docker
docker-build: ## Build Docker image
	@echo "Building Docker image..."
	docker build -t klerno-labs:latest .
	@echo "✓ Docker image built"

docker-run: ## Run application in Docker container
	@echo "Running Klerno Labs in Docker..."
	docker run -p 8000:8000 --name klerno-labs klerno-labs:latest

docker-dev: ## Run Docker container with development setup
	@echo "Running Klerno Labs development Docker..."
	docker run -p 8000:8000 -v $(PWD):/app --name klerno-labs-dev klerno-labs:latest

docker-clean: ## Remove Docker containers and images
	@echo "Cleaning Docker resources..."
	docker rm -f klerno-labs klerno-labs-dev 2>/dev/null || true
	docker rmi klerno-labs:latest 2>/dev/null || true

# Database
db-migrate: ## Run database migrations
	@echo "Running database migrations..."
	# Add migration commands here when using Alembic
	@echo "✓ Database migrations completed"

db-reset: ## Reset database (development only)
	@echo "Resetting database..."
	# Add database reset commands here
	@echo "✓ Database reset completed"

# Utilities
clean: ## Clean up temporary files and caches
	@echo "Cleaning up..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type f -name ".coverage" -delete
	rm -rf htmlcov/
	rm -rf .pytest_cache/
	rm -rf .ruff_cache/
	rm -rf .mypy_cache/
	rm -rf dist/
	rm -rf build/
	@echo "✓ Cleanup completed"

logs: ## Show application logs (if running in Docker)
	docker logs -f klerno-labs

health: ## Check application health
	@echo "Checking application health..."
	curl -f http://localhost:8000/health || echo "Application not running"

urls: ## Show all application URLs
	@echo "Klerno Labs Application URLs:"
	@echo "==============================="
	@echo "🏠 Landing Page:    http://localhost:8000/"
	@echo "📊 Dashboard:       http://localhost:8000/dashboard-ui?key=klerno_admin_2024"
	@echo "🔐 Login:           http://localhost:8000/login-ui"
	@echo "📝 Signup:          http://localhost:8000/signup-ui"
	@echo "🚨 Alerts:          http://localhost:8000/alerts-ui?key=klerno_admin_2024"
	@echo "📚 API Docs:        http://localhost:8000/docs"
	@echo "❤️  Health Check:   http://localhost:8000/health"
	@echo "⚡ WebSocket:       ws://localhost:8000/ws/alerts"

# Quick development workflow
dev-setup: setup install-dev ## Complete development setup
	@echo "✓ Development environment ready!"
	@echo "Run 'make dev' to start the application"

quick-start: install run ## Quick start for development

# CI/CD simulation
ci: format-check lint typecheck test ## Run CI pipeline locally
	@echo "✓ CI pipeline completed successfully"

# Release preparation
pre-commit: format lint typecheck test ## Run pre-commit checks
	@echo "✓ Pre-commit checks passed"