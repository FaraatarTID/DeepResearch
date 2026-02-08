Pre-Mortem Audit — DeepResearch

Scope
- Conducted pre-mortem static analysis and runtime hardening focused on silent failures, concurrency races, thread/event-loop issues, and IO atomicity.

High-level changes
- Replaced many silent/weak except blocks with `logger.exception` or structured `ExternalServiceError`.
- Bounded network fetch concurrency and made throttle-state updates atomic under locks.
- Added cooperative cancellation via `cancel_check` propagated through the pipeline.
- Avoided `asyncio.run` in library/UI code; used explicit event loops in `app.py` and `gui.py`.
- Implemented atomic file writes for DOCX and text outputs.
- Added `scripts/pre_mortem_checks.py` improvements and integrated it into CI.
- Added stress and unit tests for throttling and cancellation.

Files changed (high level)
- deep_research/utils.py
- deep_research/search.py
- deep_research/processing.py
- deep_research/core.py
- deep_research/pipeline.py
- deep_research/gui.py
- app.py
- scripts/pre_mortem_checks.py
- tests/* (added/updated)

How to review
1. Run the static checker locally: `python scripts/pre_mortem_checks.py`
2. Run tests: `python -m pytest -q`
3. Scan key files listed above for behavior changes.

Notes for reviewers
- Most remaining pre-mortem flags are test scaffolding (`__name__` assignments). These are intentional and can be ignored by the checker, or the checker can be updated to suppress them.
- CI already runs the pre-mortem checks and tests on PRs. See `.github/workflows/ci.yml`.

If approved, next steps
- Merge the branch and let CI run. Follow-up: extend the pre-mortem checker to suppress `__name__` in tests and optionally report findings as annotations in PRs.