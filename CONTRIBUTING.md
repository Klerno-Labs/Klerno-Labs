# Contributing to Klerno Labs

Thank you for your interest in contributing to Klerno Labs! This document provides guidelines for contributing to our AI-powered AML risk intelligence platform.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Coding Standards](#coding-standards)
- [Testing Requirements](#testing-requirements)
- [Pull Request Process](#pull-request-process)
- [Security Guidelines](#security-guidelines)
- [Performance Considerations](#performance-considerations)

## Code of Conduct

Please read and follow our [Code of Conduct](CODE_OF_CONDUCT.md) to ensure a welcoming environment for all contributors.

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/Klerno-Labs.git
   cd Klerno-Labs
   ```
3. **Create a feature branch** from main:
   ```bash
   git checkout -b feature/your-feature-name
   ```

## Development Setup

### Prerequisites

- Python 3.11 or higher
- Docker and Docker Compose
- Git

### Quick Setup

```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate     # Windows

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# Run the application
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Docker Development

```bash
# Development build
docker build --target development -t klerno-labs:dev .
docker run -p 8000:8000 -v $(pwd):/app klerno-labs:dev
```

## Coding Standards

### Python Code Style

We use the following tools to maintain code quality:

- **Black** for code formatting (line length: 88)
- **isort** for import sorting
- **flake8** for linting
- **mypy** for static type checking
- **pytest** for testing

### Code Formatting

Before submitting code, ensure it's properly formatted:

```bash
# Format code
black app/
isort app/

# Check linting
flake8 app/

# Type checking
mypy app/

# Run tests
pytest
```

### Code Style Guidelines

1. **Follow PEP 8** standards with 88-character line limit
2. **Use type hints** throughout the codebase
3. **Write docstrings** for all public functions and classes using Google style
4. **Keep functions focused** and under 20 lines when possible
5. **Use meaningful variable names** that describe their purpose
6. **Avoid deep nesting** (max 3-4 levels)

### Import Organization

Imports should be organized in this order:
1. Standard library imports
2. Third-party library imports  
3. Local application imports

Use absolute imports and avoid circular dependencies.

### Example Code Structure

```python
"""Module docstring describing the module's purpose."""

from typing import Dict, List, Optional

import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.models import Transaction
from app.store import get_transactions


class TransactionRequest(BaseModel):
    """Request model for transaction operations."""
    
    wallet_address: str
    limit: Optional[int] = 100


async def process_transactions(
    request: TransactionRequest
) -> List[Dict[str, Any]]:
    """Process transactions for a given wallet.
    
    Args:
        request: Transaction request parameters
        
    Returns:
        List of processed transaction data
        
    Raises:
        HTTPException: If wallet address is invalid
    """
    if not request.wallet_address:
        raise HTTPException(status_code=400, detail="Wallet address required")
    
    transactions = await get_transactions(
        wallet=request.wallet_address,
        limit=request.limit
    )
    
    return [tx.dict() for tx in transactions]
```

## Testing Requirements

### Test Structure

- **Unit tests**: Test individual functions/methods in isolation
- **Integration tests**: Test component interactions
- **API tests**: Test endpoint functionality
- **Security tests**: Test security features

### Test Guidelines

1. **Write tests for all new code** (aim for >80% coverage)
2. **Use descriptive test names** that explain what's being tested
3. **Follow AAA pattern**: Arrange, Act, Assert
4. **Mock external dependencies** in unit tests
5. **Use fixtures** for common test data

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test categories
pytest -m unit
pytest -m integration
pytest -m security

# Run specific test file
pytest app/tests/test_compliance.py -v
```

### Test Example

```python
import pytest
from app.compliance import tag_category


class TestCompliance:
    """Test compliance tagging functionality."""
    
    def test_fee_detection(self):
        """Test that network fees are properly categorized."""
        # Arrange
        transaction = {
            "memo": "network fee",
            "amount": -1.0,
            "fee": 0.1
        }
        
        # Act
        result = tag_category(transaction)
        
        # Assert
        assert result == "fee"
    
    @pytest.mark.parametrize("memo,expected", [
        ("exchange deposit", "income"),
        ("salary payment", "income"),
        ("gas refill", "expense"),
    ])
    def test_category_detection(self, memo, expected):
        """Test various transaction categorizations."""
        transaction = {"memo": memo, "amount": 100.0}
        assert tag_category(transaction) == expected
```

## Pull Request Process

### Before Submitting

1. **Update documentation** if needed
2. **Add tests** for new functionality
3. **Run the full test suite** and ensure all tests pass
4. **Check code formatting** and linting
5. **Update CHANGELOG.md** if applicable

### PR Requirements

1. **Clear title** describing the change
2. **Detailed description** explaining:
   - What changes were made
   - Why the changes are needed
   - How to test the changes
3. **Link related issues** using "Fixes #123" or "Closes #123"
4. **Small, focused changes** (avoid large PRs when possible)
5. **Updated tests** and documentation

### PR Template

```markdown
## Description
Brief description of changes made.

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Tests pass locally
- [ ] Documentation updated
```

## Security Guidelines

### Security Requirements

1. **Never commit secrets** (API keys, passwords, etc.)
2. **Use environment variables** for configuration
3. **Validate all inputs** and sanitize user data
4. **Follow secure coding practices**
5. **Report security issues** privately to security@klerno.com

### Security Checklist

- [ ] No hardcoded credentials
- [ ] Input validation implemented
- [ ] SQL injection prevention
- [ ] XSS protection in place
- [ ] CSRF protection enabled
- [ ] Rate limiting configured
- [ ] Security headers set

## Performance Considerations

### Performance Guidelines

1. **Use async/await** for I/O operations
2. **Implement caching** for frequently accessed data
3. **Optimize database queries** with proper indexing
4. **Use connection pooling** for external services
5. **Profile code** to identify bottlenecks

### Performance Testing

```bash
# Run performance tests
pytest -m performance

# Profile specific functions
python -m cProfile -o profile.stats app/main.py
```

## Questions and Support

- **General questions**: Create a GitHub issue with the "question" label
- **Bug reports**: Create a GitHub issue with the "bug" label
- **Feature requests**: Create a GitHub issue with the "enhancement" label
- **Security issues**: Email security@klerno.com

## License

By contributing to Klerno Labs, you agree that your contributions will be licensed under the same license as the project.

---

Thank you for contributing to Klerno Labs! 🚀