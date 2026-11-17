# Aurelius Foundation 0.1 — Implementation Status

Last updated: 2026-11-17

## Completed in this work branch

- Added an isolated `Money` value object using Python `Decimal`.
- Added explicit initial currency exponent metadata for BHD, CAD, COP, EUR, GBP, JPY, KWD, and USD.
- Added fixed-scale decimal-string serialization and integer minor-unit conversion.
- Added same-currency addition/subtraction and rejection of implicit FX arithmetic.
- Added tests for rounding, currency scales, float rejection, non-finite values, unknown currencies, and cross-currency operations.
- Documented the money contract and architecture decision record.

## Not yet complete

- No database models or Alembic migrations have changed.
- Existing FinTrack API monetary fields still use numeric JSON and float-backed model columns on main.
- The new domain primitive is not wired into existing endpoints.
- No frontend monetary arithmetic has been migrated.
- No accounts, double-entry ledger, reconciliation, liabilities, FX conversion, investment holdings, market data, or AI features have been implemented.
- CI has not yet validated this branch.

## Acceptance checks

- [ ] Backend unit tests pass in GitHub Actions.
- [ ] Existing backend and frontend test suites remain green.
- [ ] Static review confirms domain module has no infrastructure imports.
- [ ] Follow-up API/database migration design is reviewed before implementation.
- [ ] No production migration or deployment occurs without explicit approval.
