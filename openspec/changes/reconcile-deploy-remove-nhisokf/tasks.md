# Tasks: consolidate deploy on `deploy/`; remove `nhisokf/`

## 1. Remove the duplicate
- [x] 1.1 Confirm `nhisokf/` is unreferenced outside itself (only `.gitignore` + a draft change referenced it)
- [x] 1.2 `git rm -r nhisokf/` and delete its untracked artifacts (`.venv`, `.cache`, `node_modules`, `cdk/dist`)
- [x] 1.3 Drop the `nhisokf/**` rules from `.gitignore`

## 2. Make `deploy/` canonical
- [x] 2.1 Confirm `deploy/` targets `src/nhis_okf/agentcore_app.py` + the committed `.okf/` bundle (no code change needed)
- [x] 2.2 Note the canonical deploy structure (one `deploy/` tree; agent stays in `src/nhis_okf/`) in the repo docs (CLAUDE.md)

## 3. Closeout
- [x] 3.1 `./.venv/bin/pytest -q` still green (89); `nhis verify`/`trends`/`compile`/`conformance` unchanged (no src touched)
- [x] 3.2 `openspec validate reconcile-deploy-remove-nhisokf --strict` passes
