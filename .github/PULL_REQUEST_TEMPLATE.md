## What changed
- Summary of the pre-mortem audit, hardening and test updates included in this PR (see AUDIT_SUMMARY.md).

## Checklist for reviewers
- [ ] Static pre-mortem checks pass (`python scripts/pre_mortem_checks.py`)
- [ ] Unit tests pass (`python -m pytest -q`)
- [ ] No intentional silent `except` remains in library code
- [ ] Concurrency and cancellation behavior reviewed for regressions

## Additional notes
- CI runs the pre-mortem checks and tests on PRs; please review the `AUDIT_SUMMARY.md` for context.
- If you want me to suppress test `__name__` warnings in the checker, say so and I'll include that in a follow-up commit.
