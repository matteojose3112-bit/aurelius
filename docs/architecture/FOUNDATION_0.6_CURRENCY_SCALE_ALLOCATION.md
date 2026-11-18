# Foundation 0.6 — Currency-scale and minor-unit allocation contract

**Status:** Pure domain primitives implemented; portfolio lot integration remains a blocking gate.

## Purpose

The portfolio domain currently preserves exact unscaled Decimal quantities, prices, fees, and lot allocation facts. The ledger posts integer minor units. A settlement coordinator must not independently round journal values while leaving portfolio lot history at economically different values.

This step introduces reusable conversion/allocation primitives without changing existing lot behavior.

## Currency exponent source

- Every call receives the integer minor-unit exponent captured by the trade's immutable currency-definition snapshot.
- The helper does not query the current ISO registry, resolve by display name, or substitute a newer currency definition.
- Exponents are validated as integers from 0 through 9. The persisted currency registry remains authoritative for which exponents are valid for a real trade.

## Conversion policy

- Monetary values must be finite `Decimal` instances; booleans and binary floats are rejected.
- Final currency amounts are quantized once using `ROUND_HALF_UP`.
- Conversion produces exact integer minor units.
- Both directions enforce the ledger's signed 38-digit minor-unit magnitude bound.
- The helper does not decide which intermediate business values should be rounded. That point must be explicit in the lot/settlement integration.

## Deterministic allocation policy

`allocate_minor_units(total, weighted_keys)` apportions a non-negative integer total across positive Decimal weights:

1. Keys are unique, non-empty stable identifiers (the settlement integration will use lot UUID strings).
2. Entries are sorted lexically by key, independent of input iteration order.
3. Each entry except the final key receives its proportional share rounded down to an integer.
4. The final key receives the exact remaining minor units.
5. The resulting allocations always sum exactly to the requested total.

This avoids losing or creating minor units through independently rounded disposal rows. The final residual recipient is deterministic, not whichever row happened to arrive last from a database query.

## Explicit integration work still required

- Add the immutable currency-definition exponent to the domain execution context without re-resolving a current registry record.
- Determine and document rounding points for gross consideration, fees, net proceeds, acquisition basis, and disposal basis.
- Quantize acquisition lot basis once and ensure remaining basis after partial disposal is derived consistently.
- For multi-lot SELLs, allocate rounded total gross proceeds, sale fee, and cost basis to stable lot UUIDs; recompute per-allocation realized result and verify aggregate gain/loss equals the journal result exactly.
- Persist the same rounded Decimal values that correspond to the integer minor-unit journal amounts.
- Add replay, partial-lot, residual, multi-currency exponent, and PostgreSQL persistence tests before implementing the coordinator.

## Boundary

This PR adds a pure helper and its unit tests only. It does not modify existing lot calculations, database schema, trade execution persistence, journal posting, cash sufficiency, API routes, brokerage connections, or cash movement. The helper is not yet sufficient to authorize settlement.
