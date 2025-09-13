# Klerno Labs - GitHub Copilot Development Instructions

Always reference these instructions first and fallback to search or bash commands only when you encounter unexpected information that does not match the info here.

## Working Effectively

### Bootstrap, Build, and Test the Repository

**CRITICAL TIMING EXPECTATIONS:**
- NEVER CANCEL builds or dependency installations - they may take 10-30 minutes
- Set explicit timeouts of 60+ minutes for all build commands
- Network issues are common - expect SSL certificate errors and timeouts

#### Python Environment Setup
```bash
# Check Python version (requires 3.11+ but 3.12 recommended)
python3 --version

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or .venv\Scripts\activate  # Windows

# Upgrade pip and install build tools - NEVER CANCEL (takes 2-5 minutes)
pip install --upgrade pip setuptools wheel
```

#### Dependency Installation
```bash
# Install dependencies - NEVER CANCEL: takes 5-15 minutes, may have SSL issues
pip install -r requirements.txt

# If SSL certificate errors occur, document the specific packages that fail
# Common issues: httpx-test>=0.24.0 may not exist, certificate verification failures

# Install development dependencies separately if needed:
pip install pytest pytest-asyncio pytest-cov black isort flake8 mypy bandit
```

#### Known Dependency Issues
- `httpx-test>=0.24.0` - This package does not exist in PyPI. Remove from requirements.txt if encountering errors.
- SSL certificate verification may fail in corporate/restricted networks
- Some packages may require specific Python versions (see requirements.txt comments)

#### Build and Run the Application
```bash
# Run application directly (development mode)
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Alternative: Use included Windows setup script
.\start.ps1  # Windows only - comprehensive setup script
```

#### Docker Build Process
```bash
# Build development Docker image - NEVER CANCEL: takes 5-15 minutes
# Set timeout to 30+ minutes due to potential network issues
docker build --target development -t klerno-labs:dev .

# Build production image - NEVER CANCEL: takes 10-30 minutes
docker build --target production -t klerno-labs:latest .

# Run with Docker
docker run -p 8000:8000 -e APP_ENV=dev klerno-labs:dev
```

### Testing

#### Run Tests - NEVER CANCEL: takes 5-15 minutes
```bash
# Run all tests with coverage
pytest --cov=app --cov-report=html --cov-report=term-missing

# Run specific test categories
pytest app/tests/test_security.py -v     # Security tests
pytest app/tests/test_compliance.py -v  # Compliance tests
pytest app/tests/test_guardian.py -v    # Guardian/monitoring tests

# Performance testing (if locust is installed)
pytest -m performance --maxfail=5
```

#### Test Structure
- `app/tests/` - Main test directory
- `conftest.py` - Pytest configuration and fixtures
- `pytest.ini` - Test configuration with custom markers
- Tests use markers: unit, integration, security, performance, slow

### Code Quality and Linting
```bash
# Run all linting tools - NEVER CANCEL: takes 2-5 minutes
flake8 app/ --max-line-length=100 --statistics
black --check --diff app/
isort --check-only --diff app/
mypy app/ --ignore-missing-imports

# Security scanning
bandit -r app/ -f json -o security-report.json
safety check --json --output safety-report.json

# Format code
black app/
isort app/
```

## Validation

### ALWAYS Test Complete User Scenarios After Changes

#### Core Application Validation Scenarios:
1. **Application Startup Validation:**
   ```bash
   # Start application and verify it responds
   uvicorn app.main:app --host 0.0.0.0 --port 8000 &
   sleep 10
   curl http://localhost:8000/health || curl http://localhost:8000/
   ```

2. **API Documentation Access:**
   - Navigate to `http://localhost:8000/docs` - Interactive API docs
   - Check `http://localhost:8000/redoc` - ReDoc format
   - Verify `http://localhost:8000/openapi.json` - OpenAPI spec

3. **Admin Interface Testing:**
   - Access `/admin` → API Key Management
   - Test the built-in XRPL sandbox integration

4. **Health and Sanity Checks:**
   ```bash
   # Run built-in health checker (if dependencies are available)
   python sanity_check.py
   ```

### Manual Testing Requirements
- ALWAYS run through at least one complete end-to-end scenario after making changes
- Test transaction processing if modifying compliance or XRPL integration
- Verify authentication flows if changing security components
- Test API endpoints with actual HTTP requests, not just unit tests

## Important Codebase Locations

### Core Application Structure
```
app/
├── main.py              # FastAPI application entry point
├── models.py            # Pydantic data models
├── settings.py          # Configuration management
├── compliance.py        # AML compliance logic
├── guardian.py          # Monitoring and alerting
├── security/            # Authentication & authorization
├── hardening.py         # Security middleware
├── integrations/        # Blockchain integrations (XRPL)
├── routes/              # API endpoints
└── tests/               # Test suite
```

### Key Configuration Files
- `requirements.txt` - Python dependencies (comprehensive production list)
- `pytest.ini` - Test configuration with custom markers
- `conftest.py` - Pytest fixtures and test setup
- `Dockerfile` - Multi-stage production-ready container
- `automation/ci-cd-pipeline.yml` - GitHub Actions CI/CD configuration

### Critical Files to Check After Changes
- Always run `python sanity_check.py` after making core changes
- Check `app/compliance.py` after modifying transaction processing
- Verify `app/security/` components after authentication changes
- Test `app/integrations/` after blockchain-related modifications
- Review `app/settings.py` after environment variable changes
- Validate `app/models.py` after data structure changes

### Additional Important Directories
- `app/integrations/` - Contains `xrp.py`, `bsc.py`, `blockchain_api.py`, `bscscan.py`
- `app/routes/` - API route definitions (currently contains `analyze_tags.py`)
- `app/ai/` - AI/ML related modules
- `app/core/` - Core application utilities
- `app/database/` - Database connection and models
- `app/mobile/` - Mobile-specific functionality
- `app/static/` - Static assets for web interface
- `app/templates/` - Jinja2 templates for web UI
- `docs/` - Documentation including `api.md`, `architecture.md`, `PRD.md`

## Environment Configuration

### Required Environment Variables (see app/settings.py for defaults)
```bash
# Application Settings
APP_ENV=development  # or production
DEMO_MODE=true      # for testing
JWT_SECRET=your-32-char-secret-key  # Note: JWT_SECRET not SECRET_KEY
ACCESS_TOKEN_EXPIRE_MINUTES=60
ADMIN_EMAIL=klerno@outlook.com

# Database (PostgreSQL for production)
DATABASE_URL=postgresql://user:password@host:port/dbname

# XRPL Integration
XRPL_RPC_URL=https://s2.ripple.com:51234  # default from settings.py
# XRPL_RPC_URL=wss://s.altnet.rippletest.net:51233  # testnet
# XRPL_RPC_URL=wss://xrplcluster.com/  # mainnet

# OpenAI (optional)
OPENAI_API_KEY=your-openai-key
OPENAI_MODEL=gpt-4o-mini  # default

# Email Notifications
SENDGRID_API_KEY=your-sendgrid-key
ALERT_EMAIL_FROM=alerts@example.com  # default
ALERT_EMAIL_TO=you@example.com

# Risk Management
API_KEY=dev-api-key  # default
RISK_THRESHOLD=0.75  # default

# Paywall/Stripe (optional)
PAYWALL_CODE=Labs2025  # default
STRIPE_SECRET_KEY=your-stripe-key
STRIPE_PRICE_ID=your-price-id
STRIPE_WEBHOOK_SECRET=your-webhook-secret
```

## Common Issues and Solutions

### Dependency Installation Problems
- **SSL Certificate Issues:** Common in corporate networks. Document which packages fail.
- **httpx-test Package Missing:** Remove line 84 from requirements.txt if this fails.
- **Version Conflicts:** Python 3.12 may have compatibility issues with some packages.

### Build Failures
- **Docker SSL Issues:** Add `--build-arg PIP_TRUSTED_HOST=pypi.org` to docker build
- **Memory Issues:** Docker builds may need increased memory allocation
- **Network Timeouts:** Use longer timeout values, avoid canceling builds

### Application Startup Issues
- **Missing Dependencies:** Ensure all required packages from requirements.txt are installed
- **Database Connection:** Verify DATABASE_URL is correctly configured
- **Port Conflicts:** Default port 8000 may be in use, try different port

## Quick Reference Commands

### Daily Development Workflow
```bash
# 1. Activate environment
source .venv/bin/activate

# 2. Start application
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 3. Run tests before committing
pytest app/tests/ -v

# 4. Lint and format code
black app/ && isort app/ && flake8 app/
```

### CI/CD Pipeline Commands (from automation/ci-cd-pipeline.yml)
```bash
# Full CI pipeline locally
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install black isort flake8 mypy bandit safety pytest pytest-asyncio pytest-cov

# Code quality checks
flake8 app/ --max-line-length=100
black --check app/
isort --check-only app/
mypy app/ --ignore-missing-imports

# Security and testing
bandit -r app/
safety check
pytest app/tests/ -v --cov=app
```

### Performance Monitoring
- Response times should be < 100ms for most endpoints
- Memory usage typically < 512MB during normal operation
- Database queries should use proper indexing

## Technology Stack Summary
- **Backend:** FastAPI + Python 3.11+
- **Database:** PostgreSQL (production), SQLite (development)
- **Blockchain:** XRPL-py for native XRPL integration
- **AI/ML:** OpenAI GPT-4 for risk analysis
- **Security:** JWT + bcrypt authentication
- **Frontend:** Jinja2 server-side templates
- **Testing:** pytest with async support
- **Deployment:** Docker with multi-stage builds

## Critical Reminders
- **NEVER CANCEL** long-running build or test commands
- **ALWAYS** test complete user scenarios after changes
- **SET EXPLICIT TIMEOUTS** of 60+ minutes for builds, 30+ minutes for tests
- **DOCUMENT FAILURES** when commands don't work rather than skipping validation
- **USE SYSTEM PYTHON** if virtual environment setup fails due to network issues