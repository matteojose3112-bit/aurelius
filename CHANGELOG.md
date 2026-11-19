# Changelog

## 0.2.0 — Data quality analysis

- Added duplicate-row grouping with occurrence counts.
- Added per-column missing-value analysis, including whitespace-only cells.
- Added data quality summary to the workspace.
- Expanded unit tests for duplicate and missing-value helpers.

## 0.1.1 — Continuous integration

- Added GitHub Actions for dependency installation, unit tests, and production builds.
- Verified the initial CI run: unit tests passed and the Vite production build completed successfully.

## 0.1.0 — JavaScript rebuild foundation

- Replaced the prior application tree on the dedicated rebuild branch.
- Started a vanilla JavaScript ES module application with Vite.
- Added browser-local CSV import, parsing, preview, and search.
- Added responsive dark interface and privacy messaging.
- Added Vitest coverage for parsing and dataset helpers.
