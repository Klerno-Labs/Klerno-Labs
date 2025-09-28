Create PR script (TypeScript + Node)

This small utility creates a GitHub pull request from a local branch using a short-lived PAT.

## Usage

1. Copy `.env.example` to `.env` and fill in `GITHUB_TOKEN` (short-lived PAT), then update owner/repo if necessary.
2. Install dependencies:

   ```powershell
   npm install
   ```

3. Run in dev mode (requires Node 18+):

   ```powershell
   npm run dev
   ```

4. The script will output the PR URL and optionally request reviewers (if `REVIEWERS` env var is set).

## Security

- Use a short-lived PAT with minimal scope (repo or public_repo).
- Revoke the token after use.

## Notes

- The script reads the PR body from `PR_BODY_typing_sweep.md` by default; update `PR_BODY_FILE` env var to point elsewhere.
