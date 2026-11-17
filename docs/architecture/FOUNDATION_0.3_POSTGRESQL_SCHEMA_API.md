# Foundation 0.3 — Global PostgreSQL Persistence Architecture

**Status:** Proposed schema/API design; not implemented  
**Depends on:** Foundation 0.1 Money and Foundation 0.2 Accounts & Ledger  
**Decisions:** [ADR-003](ADR-003-canonical-money-storage.md), [Global Markets Architecture](FOUNDATION_0.3_GLOBAL_MARKETS.md)

## 1. Scope

Aurelius is an international financial intelligence platform, not a country-specific finance app. It must support international users, multi-currency accounts, global instruments, exchanges, market calendars, FX data, and jurisdiction-aware reporting.

This document defines a PostgreSQL persistence design. It does not add SQLAlchemy models, Alembic migrations, API routes, credentials, hosted services, or production writes. Authenticated server context supplies ownership; client-supplied owner IDs are ignored.

## 2. Authentication and ownership decision

Inspection of backend/app/models.py, backend/app/auth.py, and the initial Alembic migration confirms:
- User.id is an INTEGER primary key.
- JWT sub is str(user.id); authentication parses it back to an integer.
- Legacy transaction, budget, and goal tables use INTEGER user_id foreign keys to users.id.

**Decision:** first-release financial_accounts.owner_id, journal_entries.owner_id, idempotency_records.owner_id, audit_events.owner_id, and accounting_periods.owner_id use INTEGER references to users.id. created_by and actor_id also reference users.id. Do not introduce UUID login identities or a second auth principal in this milestone. Domain adapters may retain string IDs internally but must validate/convert at persistence boundaries.

New financial ownership FKs use ON DELETE RESTRICT; deleting a login must not cascade-delete accounting history. Organization/household ownership can later be introduced as a separate financial_owners abstraction, with explicit migration, rather than conflating user identity with legal ownership.

## 3. PostgreSQL baseline and enforcement

The repository does not pin a PostgreSQL major version. The legacy Render Blueprint provisions a database but does not declare its version. **CI baseline: PostgreSQL 16.** This is a test baseline, not confirmation of the existing hosted database version. Inspect the actual managed database before any future deployment or migration; do not upgrade it as part of this work.

**Decision: deferred constraint triggers** enforce journal-wide invariants at transaction commit. SQLAlchemy writes the journal header and all posting rows in one transaction. Initially deferred PostgreSQL constraint triggers validate at least two postings, exact debit/credit equality, owner/currency/version consistency, account status, and reversal symmetry. Append-only triggers and runtime-role grants prohibit UPDATE/DELETE of immutable rows. Direct invalid INSERT sequences must fail at commit in integration tests.

## 4. Canonical money and global currency registry

Persist positive integer minor-unit posting magnitudes in PostgreSQL NUMERIC(38,0), with a hard bound of 1 through 10^38 - 1. No binary floats for authoritative financial values.

The currency registry is versioned and sourced from the official ISO 4217 Maintenance Agency (SIX). Each immutable definition records:
- Alphabetic code and numeric code (numeric code stored as a three-character string to preserve leading zeros).
- Currency name, minor-unit exponent, registry release, source URL, effective dates, and status.
- Distinction between current currencies, historical denominations, fund codes, and precious-metal/reference codes.

Only definitions with a valid minor-unit exponent may denominate ordinary cash accounts. Historical codes remain available for old transactions but cannot be selected for new accounts by default. Never silently rewrite an account's exponent when the registry changes.

Non-ISO assets such as cryptocurrencies use a separate namespaced asset/unit registry and instrument-specific precision; they are not misrepresented as ISO fiat currencies. Commodities, derivatives, securities, and fund units are instruments, not cash currencies.

Accounts and journal headers snapshot currency code, exponent, and registry version. Each journal is single-currency. Cross-currency transfers are represented as explicitly linked FX legs with rate source, timestamp, base/quote convention, fees, and realized FX accounting; mixed-currency journal balancing is prohibited.

API amounts are integer minor-unit strings plus currency, or canonical decimal strings plus currency. Python uses integers/Decimal; browser clients use strings or a decimal library. JSON floating-point money is prohibited.

## 5. Logical schema

Ledger entity IDs are UUIDs; authenticated user IDs remain INTEGER. Timestamps are UTC timestamptz. Effective dates are calendar dates governed by the owner's configured accounting timezone.

### currency_definitions
- code CHAR(3), registry_version INTEGER; composite primary key.
- numeric_code CHAR(3) nullable; name TEXT; exponent SMALLINT nullable (0..4).
- registry_release, source_url, valid_from, valid_to, is_current.
- Immutable after publication. Exponent NULL is allowed only for non-cash reference codes.

### financial_accounts
- id UUID primary key; owner_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT.
- name, account_type (ASSET/LIABILITY/EQUITY/INCOME/EXPENSE), status (OPEN/CLOSED).
- currency_code and currency_registry_version FK to currency_definitions.
- created_at, closed_at. Account owner/type/currency/version immutable.
- Composite unique (id, owner_id) supports owner-scoped posting foreign keys.

### journal_entries
- id UUID primary key; owner_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT.
- effective_date, recorded_at timestamptz, description, currency code/version snapshot.
- status POSTED; reversal_of UUID UNIQUE nullable; correction_of UUID nullable.
- created_by INTEGER REFERENCES users(id) ON DELETE RESTRICT.
- Composite unique (id, owner_id, currency_code, currency_registry_version).

### journal_postings
- id UUID primary key; journal_entry_id UUID; owner_id INTEGER; account_id UUID.
- side DEBIT/CREDIT; amount_minor NUMERIC(38,0) positive integral; created_at.
- Composite FK (journal_entry_id, owner_id) to journal_entries.
- Composite FK (account_id, owner_id) to financial_accounts.
- Deferred trigger verifies account currency/version matches journal and account is OPEN.

### idempotency_records
- id UUID; owner_id INTEGER FK users; operation; idempotency_key; SHA-256 request_hash.
- journal_entry_id nullable; response_status; response_body JSONB; created_at; completed_at.
- Unique (owner_id, operation, idempotency_key). Retain at least as long as journal history.

### audit_events
- id UUID; owner_id and actor_id INTEGER FKs users; event_type; aggregate_type/id.
- occurred_at; reason; versioned payload JSONB excluding secrets; correlation_id.
- Append-only for runtime role.

### accounting_periods
- id UUID; owner_id INTEGER FK users; starts_on; ends_on; status OPEN/CLOSED; closed_at.
- Exclusion constraint prevents overlapping periods for one owner.

### financial_owner_preferences
- owner_id INTEGER primary key FK users.
- Optional base currency code/version, IANA accounting_timezone, locale, reporting calendar.
- Base currency is a reporting preference, never a restriction on account or instrument currencies. Changing it never rewrites historical ledger values.

## 6. Global markets domain

- Cash currencies use ISO 4217.
- Securities use stable internal instrument IDs plus ISIN/FIGI and listing identifiers where available.
- Exchanges/venues use ISO 10383 Market Identifier Codes (MIC), retaining venue timezone and trading calendar.
- Tickers are not globally unique; identify instruments by internal ID plus listing/venue and identifier namespace.
- Prices retain quote currency, unit, source, observed_at, market session, and adjustment methodology.
- Portfolio holdings/orders reference instruments, not currency codes.
- FX observations retain bid/ask/mid semantics, base/quote convention, provider, timestamp, and source provenance.
- Residence, tax jurisdiction, account location, exchange location, and instrument domicile are separate dimensions.
- Global capability does not imply every broker, exchange, security, or data feed is legally available in every jurisdiction; provider coverage and licensing are explicit.

## 7. Invariants and transaction

At commit:
1. Every posted journal has at least two postings.
2. Debit total equals credit total exactly.
3. Every posting owner matches both journal and account owner.
4. Account currency/version equals journal snapshot.
5. Only OPEN accounts receive ordinary postings.
6. A reversal source is unique and reversal lines exactly invert the original.
7. Posted journals, postings, audit events, and published currency definitions cannot be updated/deleted by runtime role.
8. Effective date falls in an OPEN accounting period.
9. Idempotency key and journal result commit atomically.

Transaction: authenticate owner; claim owner+operation+key with canonical request hash; replay same hash or conflict on changed hash; lock affected accounts in sorted UUID order; re-check ownership/status/currency/period/reversal; insert journal and postings; let deferred triggers validate; persist response and commit. Any failure rolls back all writes. Retry transient errors with same idempotency key.

## 8. API sketches

POST /v1/ledger/journals uses Idempotency-Key header. Owner and actor are derived from authenticated context. Request money values are strings, e.g. currency=USD and amount_minor="125000". Success returns immutable journal ID, effective_date, recorded_at, currency snapshot, and postings. Same-key replay returns stored response with replay metadata.

GET /v1/accounts/{account_id}/balance?as_of=YYYY-MM-DD returns account ID, currency/version, exact balance_minor string, and as_of date. Balance derives from postings; cached values are never authoritative.

Errors: 400 malformed schema; 401/403 authentication/authorization; 409 idempotency conflict, closed account, duplicate reversal; 422 unbalanced/currency mismatch/range; 503 exhausted transient retry.

## 9. PostgreSQL verification

Use disposable PostgreSQL 16 and independent connections:
- Empty schema migration and rollback/re-upgrade.
- Registry release/current/historical/exponent snapshots and immutability.
- Reject zero, negative, fractional, malformed, and >38-digit magnitudes.
- Reject unbalanced, single-line, mixed-currency/version, and cross-owner posting sequences at commit.
- Same-key same-payload and same-key different-payload races.
- Competing reversal race; account close versus concurrent posting.
- Failure injection after key claim, header insert, partial postings, validation, and before commit.
- Timeout-after-commit replay; owner isolation; append-only permission checks.
- Accounting period and timezone behavior; amount/aggregate boundaries.

SQLite remains for fast unit tests only. It cannot establish PostgreSQL row-locking, deferred-trigger, or isolation guarantees.

## 10. Implementation gates

Auth/FK inspection is complete: INTEGER users.id. PostgreSQL 16 is the CI baseline; actual hosted version remains unverified. Deferred constraint triggers are selected. Implement only in an isolated branch with disposable PostgreSQL CI. Confirm hosted version and reversible legacy migration before any production changes.
