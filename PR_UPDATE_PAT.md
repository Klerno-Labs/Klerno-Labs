# Updated PR notes — PAT & CI automation

This update adds precise instructions and examples for creating a fine-grained Personal Access Token (PAT) to allow CI to push formatting fixes, plus references to the new helper workflow that will create a branch and open a PR with formatting changes.

## Fine-grained PAT example (recommended)

To reduce token privileges, prefer a *fine-grained* token. When creating the token, choose:

- Resource owner: "Only select repositories" -> choose `Klerno-Labs/Klerno-Labs` (or the target repo).
- Permissions (minimum required):
  - Contents: Write (required to create branches and push commits)
  - Pull requests: Read & Write (required to open PRs via API)
  - Workflows: Read & write (optional; only needed if you plan to perform workflow-level actions)

This yields a token that can push a branch and open a PR while limiting access to just this repository.

## Classic PAT (less preferred) example

If using a classic token, grant these scopes (minimum):

- repo (full control of private repositories) — provides push access
- workflow (optional) — only needed for advanced actions

Classic tokens are broader in scope; prefer fine-grained tokens when possible.

## How to add the secret

1. Generate the token on https://github.com/settings/tokens (use 'Fine-grained token' if available).
2. In the repository, go to: Settings → Secrets and variables → Actions → New repository secret.
3. Name: `PUSH_TOKEN`
4. Value: paste the token

After adding the secret, CI workflows that reference `secrets.PUSH_TOKEN` can push branches and create PRs.

## Workflows added in this PR

- `.github/workflows/ruff.yml` — runs `ruff check .` on pushes and PRs.
- `.github/workflows/ruff-format.yml` — runs ruff formatting on PRs and attempts to push fixes back to the contributor branch when allowed (will use `PUSH_TOKEN` if set). If the PR originates from a fork the workflow will print changed files and instruct the contributor to format locally.
- `.github/workflows/ruff-create-pr.yml` — a helper workflow (manual dispatch) that will run `ruff format .`, create a new branch with fixes, push it using `PUSH_TOKEN`, and open a PR against `main` with the fixes.

## Notes & safety

- Use a fine-grained token where possible and limit permissions to the single repository.
- Keep `PUSH_TOKEN` secret; do not expose it in logs or PR comments.
- If you'd rather not allow CI to push, you can skip adding the secret and rely on the workflows to report changed files for maintainers or contributors to patch locally.

---

(End of automated PAT instructions.)
