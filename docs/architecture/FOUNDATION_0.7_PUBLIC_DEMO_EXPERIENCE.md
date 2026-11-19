# Foundation 0.7 — Public Demo Experience

**Status:** Draft implementation on `feat/aurelius-public-demo-experience`  
**Date:** 2026-11-19

## Product objective

Provide a tangible Aurelius product surface before continuing deeper backend settlement work. The frontend root should open to a useful, polished portfolio-intelligence experience without requiring registration or a running API.

## Public experience

The public root page contains:

- Portfolio value, invested capital, available cash, and illustrative return metrics.
- Selectable performance windows and a synthetic historical series.
- Asset allocation across equities, fixed income, cash, and alternatives.
- Holdings table with position quantities, reference prices, market values, and weights.
- Activity examples and a research/watchlist section.
- Responsive desktop/mobile navigation and browser print support.

The demo data is illustrative and fixed in the frontend. It must never be presented as live quotes, account balances, actual returns, or investment advice.

## Data and safety boundary

The demo entry imports no API client and performs no network requests. It does not connect to financial institutions, import user records, read portfolio database state, access market-data providers, submit orders, or move money. Every figure is synthetic.

The existing authenticated FinTrack frontend is preserved as a separate `/workspace.html` build entry. This separation avoids silently replacing the legacy application while allowing the root page to serve as the public Aurelius showcase.

## Build and deployment shape

Vite builds two static entry points:

- `/` — Aurelius public demo.
- `/workspace.html` — legacy FinTrack workspace.

The build output is `frontend/dist/`. A static-site host can publish that directory without provisioning a backend or database for the demo.

## Acceptance checks

- Public root renders without login or API availability.
- Demo banner and no-connected-accounts disclosure are visible.
- Overview, Portfolio, Activity, and Research navigation works.
- Performance range selector updates its selected state and chart series.
- Holdings search filters the table.
- Legacy workspace remains a separate build entry.
- Frontend test suite and production build pass in CI.

## Deferred

Live account aggregation, authenticated portfolio APIs, current market data, FX conversion, valuation history, trade settlement, cash sufficiency enforcement, brokerage connectivity, order execution, and production financial records remain outside this milestone.
