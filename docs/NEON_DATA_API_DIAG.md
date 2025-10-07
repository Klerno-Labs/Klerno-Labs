# Neon Data API: Quick Diagnostics

Use this when the optional Neon test fails or you want to validate credentials.

Requirements:
- VITE_NEON_DATA_API_URL: Your Data API base (e.g. https://.../rest/v1)
- NEON_API_KEY: A Neon Auth access token (JWT) for a signed-in user, not a management API key

Steps:
1) Set env vars in the same shell session that will execute code.
2) Run the PowerShell probe:
   - scripts/test-neon-rest.ps1
   - It prints status/body for base and /notes queries.
3) Run the Python diagnostic:
   - python scripts/neon_diag.py
   - It decodes the JWT header/claims (no signature check) and performs root + /notes calls.

Common outcomes:
- 401 Unauthorized: Token missing, expired, or wrong type. Fetch a valid Neon Auth user access token.
- 404 Not Found (on /notes): Table doesn't exist in the DB behind the Data API. Ensure migrations ran on the same DB the REST endpoint uses.
- 400 Bad Request: Often a PostgREST error or JWT claim mismatch. Inspect body for hints (e.g., RLS policies, invalid role, malformed query).

If you need help interpreting the output, share the status code and the non-sensitive parts of the response body (avoid posting raw tokens).
