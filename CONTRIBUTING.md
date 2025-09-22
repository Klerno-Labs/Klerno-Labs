# Contributing

Thanks for helping improve this repo. Quick notes to get you started locally.

## Local dev & tests (Windows PowerShell)

```powershell
python -m venv .venv-py311
. .\.venv-py311\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
# Optional: install dev/test helpers
python -m pip install -r dev-requirements.txt
python -m pytest -q
```

## Branches & PRs

- Create a feature branch from `main`:

```bash
git checkout -b feat/your-feature
```

- Commit small, focused changes with descriptive messages.
- Open a PR against `main`, assign reviewers, and link any related issue.

## Tests & CI

- CI runs on Python 3.11 and uses `dev-requirements.txt` for test extras.
- Keep tests small and deterministic; mark long-running tests with `@pytest.mark.integration`.

## Contacts

- Primary reviewers: Alice, Bob
- For infra/CI: DevOps team
