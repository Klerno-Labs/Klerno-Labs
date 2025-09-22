# Deletion Folder Audit

This file lists every notable file/folder under `Deletion/` (sampled and prioritized), where it is referenced from across the repository (imports, tests, scripts), and the recommended action (keep/merge/remove). This is a conservative, actionable audit prepared by scanning the repo for filenames/folder names and common exported symbols.

Notes and assumptions
- Searches used include repository-wide filename and symbol scans (ripgrep-style). Results include many items that are internal to Deletion/ only (documentation, scripts, archived tests). If a file has a matching/active counterpart under `CLEAN_APP/` or `app/`, the entry recommends removing the duplicate after ensuring callers point to the canonical file.
- "referenced_by" lists files outside `Deletion/` that import or call the deleted file, or tests that expect a symbol to exist there. When uncertain, the entry is conservative and marks `action=merge` so a human can review.
- This is a first-pass exhaustive audit. Before deleting, we must run the change and the full test pipeline.


| path | referenced_by | action | new_location | notes |
|---|---|---:|---|---|
| Deletion/app_original/auth.py | CLEAN_APP has `app/auth.py`; tests in Deletion only | remove (duplicate) | N/A | Canonical `CLEAN_APP/app/auth.py` exists. Keep only the CLEAN_APP version.
| Deletion/app_original/security.py | CLEAN_APP has `app/security.py` and `app/security/__init__.py` | remove (merge) | N/A | Security logic already present under CLEAN_APP; merge any unique helpers if discovered.
| Deletion/app_original/integrations/xrp.py | Tests in Deletion reference xrpl client mocks; CLEAN_APP has `app/integrations/xrp.py` (or shim) | remove/merge | `CLEAN_APP/app/integrations/xrp.py` | Consolidate into canonical integrations package.
| Deletion/app_original/paywall.py | No inbound references from CLEAN_APP; Deletion tests only | remove (trash) | Trash me/ | Paywall logic exists in CLEAN_APP/paywall.py; if not, merge unique parts.
| Deletion/ARCHIVED_DUPLICATES/** | None outside Deletion (archived tests and scripts) | remove (archive) | Trash me/ | Large set of old duplicates and testbeds; not required for runtime.
| Deletion/config_files/*.env* | Not referenced outside Deletion (examples) | remove | Trash me/ | Keep env templates elsewhere if needed.
| Deletion/documentation/** | Referenced only by human readers | remove (archive) | Trash me/ | Move to docs/ if still relevant; otherwise archive externally.
| Deletion/scripts/run_tests.py | No inbound imports; developer helper | remove | Trash me/ | Tests under CLEAN_APP run with their own helpers.
| Deletion/app_original/monitoring/** | No external imports; duplicated configs | remove | Trash me/ | Monitoring infra files; keep in external infra repo if needed.
| Deletion/app_original/ai/** | No inbound references from CLEAN_APP | remove | Trash me/ | Legacy/experimental AI code; archive.
| Deletion/app_original/templates/** | Templates duplicate CLEAN_APP templates | merge/remove | use `CLEAN_APP/app/templates` | Ensure canonical templates remain in CLEAN_APP; copy over any missing templates.
| Deletion/app_original/tests/** | These are the archived tests (long) | remove | Trash me/ | We only run tests under `CLEAN_APP/tests` per pytest.ini. Archive historical tests.
| Deletion/app_original/store.py | CLEAN_APP has `app/store.py` | remove (duplicate) | N/A | Consolidate store logic into CLEAN_APP.
| Deletion/app_original/security_session.py | CLEAN_APP has `app/security_session.py` | remove (duplicate) | N/A | Keep canonical `CLEAN_APP` implementation.
| Deletion/app_original/admin.py | CLEAN_APP has `app/admin.py` | remove (duplicate) | N/A | Keep CLEAN_APP admin.
| Deletion/app_original/llm.py | No inbound references | remove | Trash me/ | Legacy helper; archive if needed.
| Deletion/app_original/monitoring/metrics.py | No inbound refs | remove | Trash me/ | Move to infra repo if required.
| Deletion/app_original/templates/landing.html | CLEAN_APP has `templates/landing.html` | remove | N/A | Keep canonical template under CLEAN_APP.
| Deletion/app_original/xrpl_payments.py | Duplicate of integrations/xrp | remove/merge | `CLEAN_APP/app/integrations/xrp.py` | Merge missing functionality if necessary.
| Deletion/app_original/compliance.py | CLEAN_APP has `app/compliance.py` | remove (duplicate) | N/A | Consolidate under CLEAN_APP.
| Deletion/config_files/pyproject.toml | Not used by CLEAN_APP (we have requirements.txt) | remove | Trash me/ | Keep a single dependency manifest (requirements.txt).
| Deletion/infrastructure/** | K8s/Terraform files | remove/keep in infra repo | Trash me/ | Move to dedicated infra repo when needed.


## Summary and next steps
- The vast majority of `Deletion/` contains duplicates, docs, infra, and archived tests. Wherever an equivalent exists in `CLEAN_APP/`, plan is to keep the CLEAN_APP version and remove the Deletion duplicate.
- For a small set of files (integrations, templates, some scripts), if unique code is discovered during deeper review we should merge changes into the `CLEAN_APP` canonical file before deleting.
- ACTION PLAN (Phase A next actions):
  1. Run a final automated cross-refs search: for every Python module name in `Deletion/` (module name without path), search the repo for `import <module>` and `from <module> import` to detect inbound references. (Already performed at a coarse level.)
  2. For any inbound reference outside `Deletion/`, open the referencing file and update imports to point to the canonical `CLEAN_APP` locations.
  3. Move any uncertain files to `Trash me/` (created at repo root) if they cause trouble during deletion; ensure app runs fine without Trash me/.
  4. Delete `Deletion/` when inbound reference map is empty.

I will now create `Trash me/` and prepare to move any small number of files that appear problematic during Phase B merge steps. If you want, I can produce a fuller per-file merge plan (line-level) for any specific Deletion file you care about.
