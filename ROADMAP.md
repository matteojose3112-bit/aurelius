# Aurelius Roadmap — FinTrack Transformation

Last updated: 2026-11-17

## Product direction

**Aurelius** is the planned AI financial intelligence and investment operating system evolving from the FinTrack personal-finance MVP.

**Current status: assessment and architecture planning.** No AI agents, market-data integrations, forecasting, paper trading, or brokerage connections are implemented. The current application remains the FinTrack MVP until changes are separately reviewed, merged, and deployed.

**Guiding principle:** evidence, exact calculations, transparency, and downside protection over confident-sounding answers.

## Phase 0 — Repository and financial-core stabilization (first priority)

### Repository baseline and release coordination
- [x] Inspect the default-branch repository structure, backend/frontend implementation, tests, Render Blueprint, branches, open PRs, and open issue.
- [x] Identify the difference between deployed/main code and the more advanced integration/documentation draft branches.
- [x] Produce the Aurelius transformation assessment and initial architecture recommendation.
- [x] Record preliminary provider options and licensing/cost caveats.
- [ ] Reconcile overlapping documentation PRs #8 and #11; do not merge automatically.
- [ ] Review PR #9 (FastAPI form-parser security fix) independently; it is not included in integration PR #12.
- [ ] Resolve issue #6's status against the fixed-precision implementation in PRs #10/#12.
- [ ] Complete a clean, reviewed integration plan for PRs #3, #4, #5, #7, #9, and #10. PR #12 currently integrates #3/#5/#7/#10, but is not a substitute for reviewing each source PR.
- [ ] Keep all PRs draft until security, data migration, and deployment gates are satisfied.

### Financial correctness and data model
- [ ] Establish a documented money contract: currency code, currency-specific scale/minor units, exact calculations, rounding policy, and serialization contract.
- [ ] Avoid converting exact Decimal values to binary floats at the API boundary for financial truth; choose decimal-string or integer-minor-unit API representation and migrate frontend calculations safely.
- [ ] Model financial accounts, opening balances, transfers, liabilities, and account ownership before claiming complete net-worth/accounting support.
- [ ] Add multi-currency support with explicit native/functional/reporting currencies and timestamped FX rates.
- [ ] Design an auditable transaction/ledger model, reconciliation status, immutable import history, and correction/reversal workflow.
- [ ] Add golden-case tests for rounding, aggregation, negative balances, refunds, transfers, FX conversion, leap/month boundaries, and currency precision.
- [ ] Preserve account isolation across every new table, endpoint, report, export, and background task.

### Operational and security prerequisites
- [ ] Plan durable PostgreSQL hosting, backups, and a tested restore before the documented free database expiry on 2026-12-02.
- [ ] Confirm current live Render health and correct service URLs before relying on the existing deployment; no Blueprint sync or deployment without approval.
- [ ] Configure shared rate-limit storage and verify trusted-proxy/client-IP handling before multi-instance production.
- [ ] Review JWT lifecycle, password recovery/email verification, security headers, audit logging, secret handling, dependency updates, and access-control tests.
- [ ] Establish a privacy/data-retention policy before storing brokerage statements, tax documents, or AI conversation context.

**Phase 0 exit criteria:** clean integration CI; reviewed security fixes; exact money/currency contract; passing accounting golden tests; explicit deployment/backup plan; no unresolved critical security or data-loss risks.

## Phase 1 — Financial Core
- Expand the current transaction/budget/goal MVP into account-based personal finance.
- Build account balances, opening balances, transfers, liabilities, net worth, income/expense statements, cash flow, budgets, and forecasts.
- Add reconciliation, recurring transactions, CSV import/export, duplicate detection, and source documents.
- Introduce multi-currency records and auditable FX conversion.
- Deliver a financial overview with explainable calculations and clear data-completeness indicators.

## Phase 2 — Market Intelligence
- Add watchlists, instruments, identifiers, exchanges, asset classes, historical prices, and quote timestamps.
- Integrate macroeconomic series, company filings, financial statements, corporate actions, and news.
- Normalize data behind provider adapters; retain raw source references and ingestion metadata.
- Add caching, rate-limit handling, retries, provider health, stale-data warnings, and reconciliation between sources.
- Start with end-of-day data; do not imply real-time access unless the selected license and feed support it.

## Phase 3 — AI Financial Partner
- Build a central assistant that can answer questions using authorized personal financial data and cited market evidence.
- Add specialist roles: Market Analyst, Fundamental Analyst, Trading Analyst, Accountant, Risk Manager, Financial Educator, Research Analyst, Independent Reviewer.
- Use typed inputs/outputs, bounded tools, source citations, explicit uncertainty, and role-specific permissions.
- Add Investment Thesis Tracker and append-only Decision Journal.
- Require an independent second opinion for significant decisions; show disagreements rather than forcing false consensus.

## Phase 4 — Investment and Trading Intelligence
- Add fundamental/valuation analysis, peer comparisons, technical indicators, support/resistance, volatility, and momentum.
- Add risk/reward, position sizing, concentration, liquidity, and drawdown calculations.
- Implement paper portfolios and simulated orders only, with fees, slippage, corporate actions, and clear simulation labels.
- Backtest with point-in-time data, survivorship-bias controls, look-ahead-bias controls, and out-of-sample validation.
- Keep brokerage execution disabled.

## Phase 5 — Predictive Analytics
- Establish a prediction registry with immutable timestamp, probability, horizon, target, model/version, evidence, and outcome rule.
- Track calibration, Brier score, log loss, hit rate, benchmark comparisons, and confidence intervals where appropriate.
- Compare simple baselines against complex models; retain models only when they demonstrate out-of-sample value.
- Show scenario ranges and assumptions, never deterministic promises.
- Monitor drift and retire unreliable models.

## Phase 6 — Autonomous Monitoring
- Add scheduled market/filing/macro monitoring, thesis invalidation checks, portfolio drift alerts, and unusual-movement detection.
- Produce daily, weekly, and monthly reports with source timestamps and change summaries.
- Add user-configurable alert thresholds, quiet periods, deduplication, retries, and delivery audit logs.
- Use a background worker or scheduled job only when justified by real workload; never let scheduled AI tasks execute trades.

## Phase 7 — Professional Reliability
- Complete threat modeling, security/privacy audits, dependency and supply-chain review, and access-control testing.
- Add end-to-end tests, provider contract tests, data-quality monitoring, model evaluation, audit-log integrity, backup/restore drills, and disaster recovery.
- Add role-based permissions, retention/export/delete workflows, observability, cost controls, and incident procedures.
- Review licensing and jurisdiction-specific legal obligations before external distribution or commercial use.

## First practical development milestone: Aurelius Foundation 0.1

**Scope:** documentation + architecture contract + financial-core risk register; no AI framework, provider subscription, or external integration yet.

1. Reconcile the draft PR landscape and create a safe release baseline.
2. Specify the exact money/currency/API representation, including the current Decimal-to-float boundary problem.
3. Draft domain boundaries and initial PostgreSQL entities for accounts, currencies, ledger entries, instruments, source observations, theses, decisions, and predictions—without implementing all tables at once.
4. Define a canonical evidence schema and provider adapter interface.
5. Add a small set of deterministic accounting golden tests before any AI feature.
6. Establish CI coverage and documentation conventions for the Aurelius branch.

**Milestone acceptance:** architecture decision records are reviewed; financial correctness tests pass; no external data or AI calls are required for CI; all proposed agent tools are read-only; the existing FinTrack workflows remain intact.

## Proposed architecture

Start as a **modular monolith**:

- backend/app/domain/: money, ledger, accounts, portfolio, market, risk, research, decisions, predictions.
- backend/app/application/: use cases and orchestration interfaces.
- backend/app/providers/: SEC, FRED, market-data, FX, and news adapters.
- backend/app/intelligence/: central coordinator, specialist prompts/contracts, evidence assembly, independent review.
- backend/app/api/: focused FastAPI routers and versioned schemas.
- backend/app/jobs/: later scheduled ingestion/reporting tasks.
- frontend/src/features/: finance, portfolio, markets, research, decisions, education, settings.
- PostgreSQL: normalized records, provenance, audit events, prediction history; optional full-text search first, vector retrieval only after evaluation.

**Agent boundaries:** specialists do not connect directly to databases or providers. They request bounded tools through the application layer. The application layer validates every request, performs deterministic calculations, enforces user permissions, and logs consequential actions. The independent reviewer receives the evidence and proposed conclusion, not merely the first agent's persuasive narrative.

## Preliminary provider evaluation (no selection or purchase)

| Provider | Best initial role | Cost/limits observed 2026-11-17 | Important caveat |
|---|---|---|---|
| SEC EDGAR | U.S. filings and XBRL company facts | Public API, no key; fair-access ceiling 10 requests/second | Declare User-Agent; server-side access; no CORS on data.sec.gov |
| FRED | U.S. macroeconomic time series | API key required; no subscription price identified in reviewed terms | Third-party series rights may apply; display required notice |
| FMP | Broad fundamentals, ratios, news, multi-asset data | Basic free 250 calls/day; Starter $19/mo billed annually; Premium $49; Ultimate $99 | Tier coverage varies; display/redistribution requires separate licensing agreement |
| Alpha Vantage | Lightweight quote/history prototype | Free 25 requests/day; premium tiers for higher usage and real-time/delayed U.S. quotes | Too constrained for broad autonomous monitoring on free tier |
| Massive (Polygon) | U.S. market data, aggregates, WebSockets | Stocks Basic free 5 calls/min; Starter $29/mo; Developer $79; Advanced $199 | Individual-use tiers differ from business plans; verify display/commercial licensing |

Official references: [SEC EDGAR APIs](https://www.sec.gov/search-filings/edgar-application-programming-interfaces), [SEC fair access](https://www.sec.gov/about/developer-resources), [FRED terms](https://fred.stlouisfed.org/docs/api/terms_of_use.html), [FMP pricing](https://site.financialmodelingprep.com/pricing-plans), [Alpha Vantage limits](https://www.alphavantage.co/support/api-key/), [Massive pricing](https://massive.com/pricing). Pricing and entitlements change; re-check before implementation. This is a preliminary screen, not a legal licensing opinion.

**Initial recommendation:** SEC + FRED + one free EOD feed for a provider-neutral prototype. Do not buy a subscription yet. Compare actual symbol coverage, corporate actions, history depth, timestamp quality, reliability, API limits, display rights, commercial rights, and total cost before selecting a paid source.

## Current FinTrack release baseline (preserved, not yet shipped)

- Main branch is the older MVP. The latest inspected main tree does not include frontend/package-lock.json; its CI uses npm install.
- PR #12 integration branch has the lockfile, npm ci, fixed-precision money, CSV escaping, account-isolation coverage, login/register rate limits, populated SQLite/PostgreSQL migration tests, Vitest 4.1.12, and lazy-loaded charts. CI run #114 passed all three jobs.
- PR #11 contains release documentation updates and CI run #115 passed its backend/frontend jobs.
- PR #9 is a separate open draft security fix and is not in PR #12.
- PR #4 contains proposed Render URL/CORS corrections; no Blueprint sync was performed.
- PRs #8 and #11 are overlapping documentation work and require coordination.
- All changes remain unmerged drafts. No deployment, Render infrastructure change, production migration, paid service, or production data write was performed.

## Non-negotiable release gates

- No merge, deployment, Render Blueprint sync, infrastructure/secrets change, paid subscription, brokerage connection, money movement, or production data write without explicit approval.
- Real-money trading stays disabled.
- Do not represent forecasts as guarantees or unsupported market data as verified.
- Back up and test restore before any production database migration or reliance on durable financial records.
- Keep the original FinTrack application functional throughout the transformation.

## Historical FinTrack roadmap

The prior MVP roadmap and release notes are retained below for traceability.

---

# FinTrack Roadmap

Last updated: 2026-11-10

## Current release: 2.2.1

**Status: Deployed on Render; infrastructure and API health verified. Live user-workflow acceptance testing remains.**

### Live infrastructure

- Render Blueprint: `fintrack` (`exs-dbkhp88m7kps7396um8g`)
- API: [https://fintrack-api-l1wa.onrender.com](https://fintrack-api-l1wa.onrender.com)
- Frontend: [https://fintrack-web-int6.onrender.com](https://fintrack-web-int6.onrender.com)
- Database: `fintrack-db` (PostgreSQL 18, free tier)
- Repository: `matteojose3112-bit/fintrack`, branch `main`

### Deployment and verification

- [x] Create Render Blueprint from repository configuration.
- [x] Provision API service, static frontend, and PostgreSQL database.
- [x] Deploy API successfully and confirm Render reports it live.
- [x] Deploy frontend successfully with the production authentication API URL fix (merge commit `1549d9641a036cc72cd479b54624289b11fd6dd5`).
- [x] Confirm API health checks return HTTP 200.
- [x] Confirm PostgreSQL is available and expected schema tables exist: users, transactions, budgets, goals, and Alembic version.
- [x] Confirm frontend production build completes.
- [ ] Manually verify live account registration and login in a browser.
- [ ] Verify live transaction creation, listing, and deletion.
- [ ] Verify live budgets and savings-goal creation/progress/contributions.
- [ ] Verify CSV export and cross-account data isolation.

### Product and engineering

- [x] Responsive dashboard and transaction management.
- [x] Budget management and savings goals.
- [x] Monthly analytics and CSV export.
- [x] Registration, login, JWT authentication, and password hashing.
- [x] User-scoped financial records and API integration tests.
- [x] PostgreSQL support and Alembic initial schema migration.
- [x] GitHub Actions test and production-build workflow.
- [ ] Broader accessibility and keyboard-navigation audit.
- [ ] Password reset and email verification.
- [ ] API rate limiting and additional abuse protection.
- [ ] Automated database backups and restore testing.
- [ ] Legacy SQLite data import/upgrade utility.
- [ ] Review and remediate frontend npm audit findings (3 moderate, 1 high, 2 critical).
- [ ] Reduce or split the frontend production bundle (currently above 500 kB minified).

## Production readiness notes

The current Render PostgreSQL database is on the free tier and is scheduled to expire on December 2, 2026. Upgrade to durable paid resources and configure backups before storing real financial information. The live deployment and API health are verified, but browser-based end-to-end workflows and production security review are still outstanding. FinTrack is a portfolio/educational application, not a bank or financial-advice service.

---

Last reviewed: 2026-11-03

## Current direction — 2026-11-03

**Deployed portfolio application · Live acceptance and production-readiness work outstanding.** Next priorities: complete live registration/login and transaction, budget, goal, export, and account-isolation browser tests; review/remediate frontend dependency audit findings; reduce the production bundle; and plan a durable database upgrade with backups before the free PostgreSQL expiry on 2026-12-02. Do not store durable real financial records on the expiring free-tier database. A broader accessibility/keyboard audit and legacy SQLite import path remain open.


## Release-readiness update — 2026-11-09

**Current state: five focused hardening PRs are open as drafts; none is merged or deployed.** Their individual CI runs have passed, but this does not establish that the combined changes integrate cleanly.

### Draft pull requests

- [ ] **#3 — Account isolation regression tests:** draft PR; CI passed. Include in combined integration validation.
- [ ] **#4 — Production API URL and CORS configuration:** draft PR; CI passed. Review configuration before any authorized Render Blueprint sync.
- [ ] **#5 — CSV formula-injection protection:** draft PR; CI passed. Include in combined integration validation.
- [ ] **#7 — Authentication rate limiting:** draft PR; CI passed. Plan shared Redis/Valkey storage for multi-instance production and verify trusted-proxy/client-IP behavior before deployment.
- [ ] **#10 — Fixed-precision monetary amounts:** draft PR; CI passed. Add/perform populated legacy-data migration coverage and verify PostgreSQL conversion behavior before considering production migration.

### Updated next steps

1. Build and test a combined integration branch for PRs #3, #5, #7, and #10; review #4's deployment configuration separately.
2. Add migration regression coverage using populated pre-migration data and validate the PostgreSQL migration path for PR #10.
3. Run controlled live browser acceptance tests for registration/login, transactions, budgets, goals, CSV export, and account isolation after an approved deployment.
4. Review the frontend dependency audit findings and production bundle-size warning.
5. Arrange a durable PostgreSQL plan, verified backup, and restore procedure before the current free database expires on **2026-12-02**.

### Safety and release gates

- No draft PR has been merged; no production deployment or migration has been initiated.
- Do not sync Render Blueprint changes, alter infrastructure/secrets, or write production data without explicit approval.
- Back up production data and verify a restore path before any schema migration.
- The live app remains a portfolio/educational project, not a bank or financial-advice service.



## Release-readiness update — 2026-11-10

### Completed validation
- [x] Add a populated legacy SQLite migration regression to PR #10; CI run #91 passed.
- [x] Build a combined integration draft PR #12 covering PRs #3, #5, #7, and #10; initial combined CI run #92 passed.
- [x] Review PR #4's Render API URL and CORS diff; no Blueprint sync or live configuration change.
- [x] Review the PostgreSQL migration code path statically; no production or non-production PostgreSQL migration was run.

### Remaining release gates
1. Obtain a fresh CI run for the latest PR #12 head (a small whitespace-handling correction was committed after run #92).
2. Execute the populated-data migration against a disposable PostgreSQL instance and verify data rounding, indexes, foreign keys, and schema revision.
3. Confirm trusted-proxy/client-IP behavior and provision private shared Redis/Valkey storage before deploying rate limits to multiple instances.
4. Re-run the frontend dependency audit, assess remediation, and measure the current production bundle.
5. Complete live browser acceptance only after an explicitly approved deployment.
6. Arrange durable PostgreSQL hosting, a verified backup, and a tested restore before 2026-12-02.

PR #12 is an integration test vehicle, not a merge authorization or a replacement for reviewing the individual draft PRs. No PR has been merged; no Render sync, deployment, production migration, infrastructure/secrets change, or production data write was performed.


### Additional migration validation — 2026-11-10
- [x] Add a PostgreSQL 16 service job to the integration CI workflow.
- [x] Execute the populated legacy-data migration against disposable PostgreSQL; integration CI run #96 passed.
- [x] Confirm all three integration CI jobs passed: backend, frontend, and populated PostgreSQL migration.


### Frontend maintenance follow-up — 2026-11-10
- [x] Re-run npm audit in CI and identify affected packages and severity.
- [ ] Plan and test the major Vitest upgrade to 4.1.12 (audit's reported fix path); affected packages are dev/test dependencies.
- [ ] Re-run npm audit after the upgrade and verify the lockfile is committed and reproducible.
- [ ] Split the 617.25 kB minified JavaScript chunk (172.34 kB gzip) using route-level lazy loading/manual chunks where appropriate.
- [ ] Investigate Recharts zero-width/zero-height warnings emitted by frontend tests.
- [ ] Update GitHub Actions setup-node/checkout usage for the announced Node 20 action deprecation warning.

- [x] Re-run the complete integration pipeline with npm audit reporting enabled; CI run #99 passed all three jobs.


## Frontend maintenance update — 2026-11-10

- [x] Upgrade Vitest to 4.1.12; integration CI run #107 reports zero npm audit vulnerabilities.
- [x] Lazy-load dashboard Recharts panels; initial JS reduced from 617.25 kB to 179.05 kB (54.73 kB gzip), with a separate 438.31 kB charts chunk (118.18 kB gzip).
- [x] Verify backend tests, frontend tests/build, and populated PostgreSQL migration together; all passed in CI run #107.
- [ ] Remove or properly simulate Recharts chart dimensions in jsdom tests to eliminate zero-width/zero-height warnings.
- [ ] Update GitHub Actions checkout/setup-node from v4 to Node 24-compatible action versions to remove Node 20 deprecation warnings.
- [ ] Add and commit a reproducible frontend package lockfile; current workflow still runs npm install without a committed lockfile.


### Reproducible frontend install — 2026-11-12
- [x] Confirm no frontend lockfile exists and keep CI on `npm install` rather than breaking it with `npm ci`.
- [x] Add a temporary CI artifact upload for the lockfile generated by npm install on the next successful run.
- [ ] Retrieve a genuine `frontend/package-lock.json` from CI or a network-enabled Node environment and commit it.
- [ ] Change CI to `npm ci` only after the committed lockfile is present.
- [ ] Verify the lockfile install, Vitest 4.1.12, zero-vulnerability audit, frontend tests/build, backend tests, and PostgreSQL migration in one complete run.
- **Blocker:** the current execution environment cannot reach GitHub/npm and has no cached npm metadata; offline lockfile generation failed. No fabricated lockfile was added.


### Reproducible frontend install — completed 2026-11-12
- [x] Generate and commit the genuine npm lockfile at `frontend/package-lock.json` (lockfileVersion 3).
- [x] Replace `npm install` with `npm ci` in frontend CI.
- [x] Remove temporary lockfile-bootstrap permissions and branch-write logic; CI is read-only again.
- [x] Verify clean install, Vitest 4.1.12, zero-vulnerability npm audit, frontend tests/build, backend tests, and populated PostgreSQL migration; all passed in CI run #114.
