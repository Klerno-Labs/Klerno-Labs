Archived modules (kept for reference; not used by the running app):

- app/ai_agent.py → archive/app_ai_agent.py
- app/auth_sso.py → archive/app_auth_sso.py
- app/integrations/bscscan.py → archive/app_integrations_bscscan.py
- live.html → archive/live.html

To restore, move a file back to its original path. These are optional features or experiments not wired into `app/main.py`.

Notes:
- auth_sso.py requires Authlib and OAuth client setup; it was not included in the router, so it’s archived.
- bscscan.py provided BSC utilities but wasn’t wired into endpoints; xrp integration remains active.
- The top-level live.html was a static demo landing; the app now serves a minimal root page and templates under `app/templates`.
