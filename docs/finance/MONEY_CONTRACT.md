# Aurelius Money and Currency Contract

**Status:** Initial implementation contract — 2026-11-17  
**Scope:** Domain-level foundation only. This contract does not migrate the existing database or change current API payloads.

## 1. Canonical representation

- Monetary values are exact decimal quantities, represented in Python by `decimal.Decimal`.
- Public API and import boundaries must accept and emit decimal strings (for example, `"1250.40"`), never JSON binary floating-point numbers as the source of financial truth.
- Persisted amounts must use fixed-precision decimal database types sized from documented product limits. Currency is stored explicitly beside every amount.
- Integer minor units are suitable for bounded calculations and interchange only when paired with an explicit currency code and exponent.
- Binary floats are prohibited in financial domain calculations, persistence contracts, and serialized monetary values.

## 2. Currency scale

Currency scale is a property of the currency, not a universal two-decimal assumption. The initial domain registry explicitly supports:

| Currency | Exponent | Example fixed-scale amount |
| --- | ---: | ---: |
| BHD | 3 | 1.234 |
| CAD | 2 | 1.23 |
| COP | 2 | 1.23 |
| EUR | 2 | 1.23 |
| GBP | 2 | 1.23 |
| JPY | 0 | 123 |
| KWD | 3 | 1.234 |
| USD | 2 | 1.23 |

The registry is intentionally explicit. Unknown codes fail closed; do not silently assume two decimals. Expand the registry through reviewed tests and authoritative currency metadata before supporting additional currencies.

## 3. Rounding

- The initial domain primitive uses decimal `ROUND_HALF_UP` when normalizing an amount to its currency scale.
- Intermediate calculations retain Decimal precision and are not rounded after every operation.
- Round only at defined monetary boundaries (currency minor-unit posting, display, settlement, or an explicitly specified conversion).
- Any future tax, interest, fee, allocation, or FX rule must declare its own legally/business-appropriate rounding boundary and tests. This default is a technical baseline, not a universal tax or banking rule.

## 4. Arithmetic and FX

- Addition and subtraction require identical currency codes.
- Cross-currency arithmetic is rejected.
- FX conversion must be an explicit application/domain operation using a rate with base currency, quote currency, observed/effective timestamp, source, retrieval timestamp, and conversion direction.
- A converted amount must retain the original amount/currency and the rate evidence used. Never overwrite native-currency truth with a reporting-currency estimate.

## 5. Input validation

- Accept Decimal values internally and decimal strings at external boundaries.
- Reject floats, booleans, NaN, positive/negative infinity, malformed strings, and unsupported currencies.
- Normalize currency codes to uppercase and validate a three-letter code.
- Negative amounts are permitted at the primitive level for reversals, corrections, and signed balances; individual use cases impose their own direction/positivity rules.

## 6. API migration policy

The existing FinTrack API currently exposes numeric JSON values and the existing database model uses floating-point columns on `main`. The new `Money` primitive does not silently change those contracts.

Before any endpoint migration:
1. Review the separate fixed-precision integration work (PR #12 and its source PRs).
2. Define versioned request/response schemas with decimal strings and explicit currency.
3. Add compatibility tests and a deliberate frontend decimal-string strategy; do not rely on JavaScript `Number` for exact financial arithmetic.
4. Design a reversible/verified database migration, backup, restore, and reconciliation plan.
5. Obtain explicit approval before production migration or deployment.

## 7. Initial implementation

`backend/app/domain/money.py` provides an immutable `Money` value object, an explicit initial currency registry, currency-scale normalization, fixed-scale serialization, exact integer-minor-unit construction and conversion, canonical zero serialization, and same-currency addition/subtraction. Its tests cover rounding, scale, float rejection, invalid values, unknown currencies, and cross-currency arithmetic.

## 8. Non-goals

This contract does not yet implement FX feeds, account balances, ledger posting, investment lots, market prices, tax calculations, or portfolio valuation. It does not constitute accounting, tax, or legal advice.
