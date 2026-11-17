# ADR-003 — Canonical Monetary Persistence

- **Status:** Proposed for Foundation 0.3 review
- **Date:** 2026-11-17
- **Decision:** Store monetary quantities as integer minor units in PostgreSQL `NUMERIC(38,0)`, paired with an immutable currency code and a versioned currency-exponent definition.

## Context

Aurelius supports currencies with zero, two, and three fractional decimal places. A universal two-decimal column is incorrect for currencies such as JPY and KWD. PostgreSQL `BIGINT` is exact but limited to 19 decimal digits and can overflow in long-lived aggregate balances. Binary floating point is unacceptable for authoritative money.

## Decision

- Persist each journal posting's positive magnitude in `NUMERIC(38,0)` as integer minor units. The debit/credit side is a separate constrained field.
- The value must be integral, greater than zero, and no greater than `10^38 - 1`. The application domain must enforce the same bound before persistence.
- Store ISO currency code, exponent, and registry version on the account; journal postings inherit currency through the account and must match the journal's currency. Persist a currency snapshot (code, exponent, registry version) on the journal header to make historical interpretation stable.
- The registry is versioned and append-only. Never silently change an existing currency's exponent. A new registry version is an explicit migration decision.
- API monetary inputs and outputs use either canonical decimal strings plus currency or integer minor-unit strings plus currency. Never use JSON floating-point numbers for authoritative values.
- Convert between major-unit decimal strings and minor units using decimal/integer arithmetic only. No binary float conversion at any boundary.

## Bounds and operational limits

PostgreSQL `NUMERIC(38,0)` supports at most 38 decimal digits. This is the hard persisted magnitude ceiling, not a target transaction size. Domain validation rejects values outside the range before SQL execution. Account balance queries use exact numeric aggregation; any derived result outside the documented bound is an integrity/operational error, never a wrapped value.

A future product-level limit should be substantially lower and configurable per owner/account, but must remain an explicit policy rather than an undocumented database assumption. This ADR does not set a business transaction cap.

## Trade-offs

- `NUMERIC(38,0)` is wider and slower than `BIGINT`, but avoids premature overflow while retaining exact integer semantics.
- The explicit exponent snapshot makes historical display stable and makes currency-registry changes auditable.
- The design does not perform FX conversion. A journal is single-currency; cross-currency transfers require a separately designed FX transaction with explicit rates, fees, and gain/loss accounting.

## Consequences

- SQLAlchemy mapping must use `Numeric(38, 0, asdecimal=True)`; application code must convert only to/from Python integers, never floats.
- PostgreSQL integration tests are mandatory for constraints, aggregate bounds, transaction isolation, and concurrency behavior.
- Legacy `Numeric(14,2)` fields remain isolated from the canonical ledger and require an explicit migration/adapter.
