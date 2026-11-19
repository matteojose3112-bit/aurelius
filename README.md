# FinTrack — CSV Studio

A lightweight CSV inspection and cleaning workspace built primarily with vanilla JavaScript.

**Status:** JavaScript MVP foundation; automated tests and production build passing in GitHub Actions  
**Application:** CSV Studio  
**Approach:** Browser-first, privacy-conscious, no backend required for the MVP.

## What it does

- Import CSV files from your device.
- Parse quoted fields, escaped quotes, commas, and embedded newlines.
- Preview tabular data.
- Search across all columns.
- Inspect row, column, and empty-cell counts.
- Keep file processing inside the browser.

## Technology

- JavaScript (ES modules)
- HTML5
- CSS3
- Vite
- Vitest
- GitHub Actions

## Run locally

```bash
npm install
npm run dev
```

Run tests and production build:

```bash
npm test
npm run build
```

## Continuous integration

GitHub Actions automatically installs dependencies, runs the unit tests, and creates a production build for pushes to `main` and `rebuild/**` branches, as well as pull requests targeting `main`.

## Privacy

CSV files are read locally in the browser. This project does not upload imported data to a server.

## Project structure

```text
fintrack/
├── .github/
│   └── workflows/
│       └── ci.yml
├── index.html
├── src/
│   ├── csv.js
│   ├── main.js
│   └── styles.css
├── tests/
│   └── csv.test.js
├── package.json
└── vite.config.js
```

## Roadmap

See [ROADMAP.md](./ROADMAP.md) for the planned milestones and [CHANGELOG.md](./CHANGELOG.md) for implementation history.
