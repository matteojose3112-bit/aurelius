# Foundation 0.3 — Global PostgreSQL Persistence Architecture

**Status:** SQLAlchemy models and Alembic migration implemented on a draft feature branch; PostgreSQL 16 CI validation in progress. API and posting application service are not yet implemented.

**Depends on:** Foundation 0.1 Money, Foundation 0.2 Accounts & Ledger, and [ADR-003](ADR-003-canonical-money-storage.md).

## 1. Scope and boundaries

Aurelius is an international financial intelligence platform, not a country-specific finance app. It must support international users, multi-currency accounts, global instruments, exchanges, market calendars, FX data, and jurisdiction-aware reporting.

The current implementation adds a persistence schema and database-level guards. It does not connect API routes, production data, hosted databases, brokerage services, or deployment infrastructure. Authenticated server context supplies ownership; client-supplied owner IDs are ignored.

## 2. Authentication and ownership

Repository inspection confirms:
- User.id is an INTEGER primary key.
- JWT subject serializes User.id as a string; authentication parses it back to integer.
- Legacy finance tables use INTEGER user_id references to users.id.

The first Aurelius persistence implementation therefore uses INTEGER owner_id / actor_id references to users.id with ON DELETE RESTRICT. Ledger aggregate IDs use UUID. There is no second login identity or silent UUID conversion. Future organizations/households require an explicit financial-owner abstraction.

## 3. PostgreSQL baseline and enforcement

PostgreSQL 16 is the disposable CI baseline. The existing hosted database major version remains unverified and must be checked before any future migration or deployment.

The Alembic migration installs PostgreSQL-only:
- Initially deferred constraint triggers that validate a complete journal at commit.
- Append-only protections for published currency definitions, posted journals/postings, and audit events.
- Immutable account identity protection.
- One-time idempotency completion protection.
- A GiST exclusion constraint preventing overlapping accounting periods for one owner.

SQLite is used for fast model/migration tests only. It does not prove PostgreSQL trigger, lock, or concurrency behavior.

## 4. Exact monetary persistence

Posting magnitudes are exact integer minor units. The PostgreSQL column uses unconstrained-precision NUMERIC plus a database CHECK:
- amount_minor = trunc(amount_minor)
- amount_minor > 0
- amount_minor < 10^38

This allows at most 38 integer digits and, unlike NUMERIC(38,0), rejects fractional input instead of rounding it to scale zero before the CHECK executes. SQLAlchemy maps the field as Numeric(asdecimal=True) with no declared scale. The application accepts Python integers only. No binary floats are authoritative.

The currency registry is sourced from SIX, the ISO 4217 Maintenance Agency. Current and historical definitions are immutable versioned records. Historical List Three entries retain code, numeric code, name, country association, and jurisdiction-specific withdrawal dates; their minor-unit exponent is not inferred where the source does not publish one.

## 5. Implemented logical schema

### currency_definitions
- UUID id; code CHAR(3); numeric_code CHAR(3) nullable; name.
- minor_unit_exponent nullable; registry_list (one/three); registry_release; published_on.
- fund flag; withdrawal_key; withdrawn_label; countries JSON; source_url; created_at.
- Unique (code, registry_release, registry_list, withdrawal_key).
- Published definitions are append-only.

### financial_accounts
- UUID id; owner_id INTEGER FK users.id ON DELETE RESTRICT.
- name; account_type (ASSET/LIABILITY/EQUITY/INCOME/EXPENSE); status (OPEN/CLOSED).
- currency_definition_id UUID FK to immutable currency_definitions.
- created_at; closed_at.
- Composite unique (id, owner_id, currency_definition_id) supports posting owner/currency FKs.
- Owner, account type, currency definition, ID, and creation time are immutable; name/status can change through audited application workflows.

### journal_entries
- UUID id; owner_id INTEGER FK users.id; effective_date; recorded_at; description.
- currency_definition_id UUID FK to currency_definitions; status POSTED only.
- reversal_of UUID nullable UNIQUE; correction_of UUID nullable; created_by INTEGER FK users.id.
- Composite unique (id, owner_id) and (id, owner_id, currency_definition_id).
- Reversal/correction source references are owner-scoped.
- Posted journals are append-only.

### journal_postings
- UUID id; journal_entry_id UUID; owner_id INTEGER; account_id UUID; currency_definition_id UUID.
- side DEBIT/CREDIT; amount_minor exact NUMERIC; created_at.
- Composite FK (journal_entry_id, owner_id, currency_definition_id) to journal_entries.
- Composite FK (account_id, owner_id, currency_definition_id) to financial_accounts.
- These FKs prevent cross-owner and cross-currency-definition postings.

### idempotency_records
- UUID id; owner_id INTEGER FK users; operation; idempotency_key; SHA-256 request_hash.
- journal_entry_id nullable and owner-scoped; response_status and response_body nullable while pending; created_at; completed_at.
- Unique (owner_id, operation, idempotency_key).
- Identity/hash are immutable; a pending record can be completed once; completed results cannot be changed or deleted.

### audit_events
- UUID id; owner_id and actor_id INTEGER FKs users; event_type; aggregate_type/id.
- occurred_at; reason; versioned JSON payload excluding secrets; correlation_id.
- Append-only.

### accounting_periods
- UUID id; owner_id INTEGER FK users; starts_on; ends_on; status OPEN/CLOSED; closed_at.
- PostgreSQL exclusion constraint prevents overlapping date ranges for the same owner.

### financial_owner_preferences
- owner_id INTEGER primary key FK users.
- Optional base_currency_definition_id; IANA accounting_timezone; locale; reporting_calendar.
- Base currency is a reporting preference, not a restriction on account or instrument currencies. Changing it never rewrites historical ledger amounts.

## 6. Database-enforced journal invariants

At transaction commit:
1. Every posted journal has at least two postings.
2. Debit total equals credit total exactly.
3. Every posting owner matches journal owner and account owner.
4. Account currency definition matches journal currency definition.
5. Ordinary journals post only to OPEN accounts; reversals can correct closed-account history.
6. A reversal source is unique and reversal lines exactly invert the original account/side/amount multiset.
7. Posted journals, postings, audit events, and published currency definitions cannot be updated/deleted.
8. Accounting periods cannot overlap for one owner.
9. Idempotency identity and final response are protected.

The posting service must lock affected account rows in sorted UUID order, re-check owner/status/currency/period/reversal eligibility, insert header and postings, complete the idempotency result, and commit once. That service is the next implementation milestone; the database triggers are already represented in the migration but still require PostgreSQL CI validation.

## 7. Global markets domain boundaries

- Cash currencies use ISO 4217.
- Securities use stable internal instrument IDs plus ISIN/FIGI and listing identifiers where available.
- Exchanges/venues use ISO 10383 MIC, retaining venue timezone and trading calendar.
- Tickers are not globally unique; a listing is a time-bounded relationship between an instrument and venue.
- Prices retain quote currency, unit, source, observed_at, market session, and adjustment methodology.
- Holdings/orders reference instruments, not currency codes.
- FX observations retain bid/ask/mid semantics, base/quote convention, provider, timestamp, and source provenance.
- Residence, tax jurisdiction, account location, exchange location, and instrument domicile are separate dimensions.
- Provider coverage, data licensing, and jurisdiction eligibility are explicit; global architecture does not imply every market or broker is available everywhere.

See [Global Asset Coverage](FOUNDATION_0.3_GLOBAL_ASSET_COVERAGE.md).

## 8. API and application-service gates

The future journal API uses an Idempotency-Key header. Owner and actor are derived from authenticated context. Amounts are integer minor-unit strings plus currency or canonical decimal strings plus currency. JSON floats are prohibited.

The account-balance API derives balances from immutable postings; cached values are never authoritative. API routes are intentionally not implemented until PostgreSQL persistence tests pass.

## 9. PostgreSQL verification plan

The disposable PostgreSQL 16 CI job is being added to validate:
- Empty-database Alembic migration and PostgreSQL-specific trigger creation.
- Balanced and unbalanced journals, single-posting rejection, closed-account rejection, and exact reversal symmetry.
- Fractional minor-unit rejection and the 38-digit boundary.
- Append-only protection and one-time idempotency completion.
- Same-key concurrent insert serialization and atomic rollback.
- Owner/currency composite FK enforcement and period-overlap exclusion.

More exhaustive posting-service tests will cover same-key/same-payload replay, changed-payload conflict, competing reversals, close/post races, retry after unknown commit outcome, and failure injection at each transaction stage.

## 10. Release gates

- Auth/FK inspection is complete: INTEGER users.id.
- Currency registry implementation and SQLite tests are in place.
- SQLAlchemy models and Alembic migration are implemented on a draft branch.
- PostgreSQL 16 CI validation must pass before the posting application service is built.
- Actual hosted database version, backup/restore, legacy reconciliation, and reversible production migration remain unverified and out of scope.
