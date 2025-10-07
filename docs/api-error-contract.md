# API Error Contract

## Standardized Error Envelope

All API endpoints (except legacy HTML and paywall routes) return errors in the following envelope:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "timestamp": "2025-01-01T00:00:00Z",
    "request_id": "00000000-0000-0000-0000-000000000000",
    "details": {
      "errors": [
        {"field": "email", "message": "Invalid email format", "type": "value_error"}
      ]
    }
  }
}
```

- `code`: Machine-readable error code (e.g., `VALIDATION_ERROR`, `UNAUTHORIZED`, `NOT_FOUND`).
- `message`: Human-readable error message.
- `timestamp`: ISO8601 UTC timestamp of error.
- `request_id`: Unique request identifier for tracing.
- `details`: Optional, may include validation errors or extra context.

## Request ID Correlation

Every error response includes a `request_id` header and field. Use this for tracing and support.

## Example Client Error Handling (Python)

```python
import requests
resp = requests.post("https://api.klerno.com/auth/login/api", json={"email": "bad", "password": "bad"})
if resp.status_code != 200:
    err = resp.json()["error"]
    print(f"Error {err['code']}: {err['message']} (Request ID: {err['request_id']})")
```

## Legacy/HTML Exceptions

- HTML endpoints and `/premium/advanced-analytics` may return legacy error shapes for compatibility.


## See Also

- [OpenAPI schema](../README.md)
- [tests/test_openapi_error_envelope.py](../tests/test_openapi_error_envelope.py)
