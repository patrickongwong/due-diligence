# Due Diligence

Equity research due diligence toolkit for Claude Code. Generates PDF reports for any stock ticker.

These skills are part of the first phase of a Due Diligence. The first phase is mainly are about getting a rough picture about a company before any further work is put in.

## Skills

| Command | What It Does |
|---------|-------------|
| `/dd-1bear TICKER` | Bear Case One-Pager — bearish theses from analysts, investors, journalists |
| `/dd-1honesty TICKER` | Management Honesty Check — did management deliver on projections? |
| `/dd-1ind TICKER` | Industry Analysis — market share, competitors, ecosystem |
| `/dd-1vl TICKER` | Value Line One-Pager — 15 years of financials on one page |
| `/dd-price-chart TICKER` | Annotated Price Chart — price history with event annotations |

## Installation

Claude Code uses a **marketplace** system for plugins. This repo serves as both the marketplace and the plugin, so installation is two steps:

### Step 1: Add the marketplace

This registers the Due Diligence repository as a plugin source in your Claude Code installation.

```bash
claude plugin marketplace add patrickongwong/due-diligence
```

This clones the repo to `~/.claude/plugins/marketplaces/due-diligence/` and reads the plugin index from `.claude-plugin/marketplace.json`.

### Step 2: Install the plugin

```bash
claude plugin install due-diligence
```

This copies the plugin's skills into Claude Code's cache at `~/.claude/plugins/cache/due-diligence/due-diligence/1.0.0/`. The 5 slash commands (`/dd-1bear`, `/dd-1honesty`, `/dd-1ind`, `/dd-1vl`, `/dd-price-chart`) are now available in any Claude Code session.

### Step 3: Install Python dependencies

The skills generate PDFs using Python. Install the dependencies upfront:

```bash
pip install -r ~/.claude/plugins/cache/due-diligence/due-diligence/1.0.0/requirements.txt
```

Or skip this step — each script will auto-install its own dependencies the first time it runs.

### Updating

To pull the latest version:

```bash
claude plugin update due-diligence
```

### Uninstalling

```bash
claude plugin uninstall due-diligence
claude plugin marketplace remove due-diligence
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DD_OUTPUT_DIR` | No | `./due-diligence` | Directory where PDF reports are saved. Each ticker gets a subfolder. |
| `EDGAR_IDENTITY` | No | — | Your name and email for SEC EDGAR access (e.g., `"Jane Doe jane@example.com"`). Used by `/dd-1vl` to fetch 15 years of SEC filing data. Falls back to Yahoo Finance if not set. |

To set these permanently, add them to your shell profile (`~/.zshrc` or `~/.bashrc`):

```bash
export DD_OUTPUT_DIR="$HOME/research/due-diligence"
export EDGAR_IDENTITY="Jane Doe jane@example.com"
```

Or set them in Claude Code's settings:

```bash
claude config set env.DD_OUTPUT_DIR ~/research/due-diligence
claude config set env.EDGAR_IDENTITY "Jane Doe jane@example.com"
```

## Usage

Each skill is invoked as a slash command in Claude Code:

```
> /dd-1bear AAPL
> /dd-1honesty TSLA
> /dd-1ind MSFT
> /dd-1vl GOOG
> /dd-price-chart AMZN 2015-2025
```

Reports are saved to `$DD_OUTPUT_DIR/<TICKER>/` (default: `./due-diligence/<TICKER>/`).

### What each skill produces

**`/dd-1bear`** — Compiles the strongest bearish arguments against a stock. Researches sell-side analyst downgrades, famous short-sellers, and financial journalist bear theses. Fact-checks everything. Outputs a one-page PDF with thematic bear theses and clickable source links.

**`/dd-1honesty`** — Finds what management publicly projected (revenue targets, margin goals, store openings, product launches) and checks whether they delivered. Outputs a 2-3 page PDF with projection vs. actual tables and narrative analysis.

**`/dd-1ind`** — Maps the competitive landscape: market share trends, competitor performance, a "silver bullet" analysis (which competitor each player would most want to eliminate), and the industry ecosystem (suppliers, customers, regulations). Outputs a 3-5 page PDF.

**`/dd-1vl`** — Fetches 15 years of financial data from SEC EDGAR and Yahoo Finance. Renders a dense, Value Line-style single-page PDF with historical financials, price chart, capital structure, quarterly data, growth rates, and ROIC.

**`/dd-price-chart`** — Fetches price history, detects significant moves, researches what caused each one, fact-checks the headlines, and renders a publication-quality annotated price chart with an event reference table.

## License

MIT
