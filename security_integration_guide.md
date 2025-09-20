# Security Integration Guide

```python
# Add to app/main.py after imports:

from app.security.middleware import (
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
    InputSanitizationMiddleware,
    APIKeyValidationMiddleware
)
from app.security.audit import audit_logger, AuditEventType

# Add middleware to app (add after app = FastAPI()):

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware, calls=100, period=60)
app.add_middleware(InputSanitizationMiddleware)
app.add_middleware(APIKeyValidationMiddleware)

# Example usage in endpoints:

@app.post("/login")
async def login(request: Request, credentials: UserCredentials):
    ip_address = request.client.host
    
    try:
        user = authenticate_user(credentials)
        if user:
            audit_logger.log_login(user.id, ip_address, success=True)
            return {"token": create_access_token(user)}
        else:
            audit_logger.log_login(credentials.username, ip_address, success=False)
            raise HTTPException(status_code=401, detail="Invalid credentials")
    except Exception as e:
        audit_logger.log_security_violation(
            {"error": str(e), "endpoint": "/login"},
            ip_address=ip_address
        )
        raise

```