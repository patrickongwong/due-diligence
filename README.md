# Due Diligence

Equity research due diligence toolkit for Claude Code. A structured, multi-phase process for researching any publicly traded company.

## Skills

### Phase 1 — First Look

Get a rough picture of a company before committing to deeper work. Each skill produces a standalone PDF report.

| Command | What It Does |
|---------|-------------|
| `/dd-phase1 TICKER` | **Run all five Phase 1 skills in parallel** |
| `/dd-1bear TICKER` | Bear Case One-Pager — bearish theses from analysts, investors, journalists |
| `/dd-1honesty TICKER` | Management Honesty Check — did management deliver on projections? |
| `/dd-1ind TICKER` | Industry Analysis — market share, competitors, ecosystem |
| `/dd-1vl TICKER` | Value Line One-Pager — 15 years of financials on one page |
| `/dd-1price-chart TICKER` | Annotated Price Chart — price history with event annotations |

### Phase 2 — Deep Dive

Build the research infrastructure for serious analysis.

| Command | What It Does |
|---------|-------------|
| `/dd-2dataroom TICKER` | Dataroom — index of all SEC filings, proxy statements, shareholder letters, earnings transcripts |
| `/dd-2financials TICKER` | Financial Statements — multi-year IS/BS/CF extraction to JSON + formatted Excel |
| `/dd-2super-commentaries TICKER` | Superinvestor Commentaries — what the smartest money has publicly said about a stock |

### Utility

| Command | What It Does |
|---------|-------------|
| `/dd-zettelfy` | Assign zettel IDs to new prospect folders in `dd Due Diligence/` |

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

This copies the plugin's skills into Claude Code's cache at `~/.claude/plugins/cache/due-diligence/due-diligence/1.0.0/`. All slash commands are now available in any Claude Code session.

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
> /dd-phase1 AAPL           # run all Phase 1 reports in parallel
> /dd-1bear AAPL             # or run individually
> /dd-1vl GOOG
> /dd-1price-chart AMZN 2015-2025

> /dd-zettelfy               # organize new prospect folders
> /dd-2dataroom AAPL         # build the filing index
> /dd-2financials AAPL       # extract financial statements
> /dd-2super-commentaries AAPL  # collect superinvestor commentary
```

Phase 1 PDF reports are saved to `$DD_OUTPUT_DIR/<TICKER>/` (default: `./due-diligence/<TICKER>/`). Phase 2 outputs go into the `dd Due Diligence/` Zettelkasten structure.

### What each skill produces

**`/dd-phase1`** — Orchestrator that dispatches all five Phase 1 skills in parallel for a ticker.

**`/dd-1bear`** — Compiles the strongest bearish arguments against a stock. Researches sell-side analyst downgrades, famous short-sellers, and financial journalist bear theses. Fact-checks everything. Outputs a one-page PDF with thematic bear theses and clickable source links.

**`/dd-1honesty`** — Finds what management publicly projected (revenue targets, margin goals, store openings, product launches) and checks whether they delivered. Outputs a 2-3 page PDF with projection vs. actual tables and narrative analysis.

**`/dd-1ind`** — Maps the competitive landscape: market share trends, competitor performance, a "silver bullet" analysis (which competitor each player would most want to eliminate), and the industry ecosystem (suppliers, customers, regulations). Outputs a 3-5 page PDF.

**`/dd-1vl`** — Fetches 15 years of financial data from SEC EDGAR and Yahoo Finance. Renders a dense, Value Line-style single-page PDF with historical financials, price chart, capital structure, quarterly data, growth rates, and ROIC.

**`/dd-1price-chart`** — Fetches price history, detects significant moves, researches what caused each one, fact-checks the headlines, and renders a publication-quality annotated price chart with an event reference table.

**`/dd-zettelfy`** — Scans `dd Due Diligence/` for prospect folders without zettel IDs, assigns sequential IDs, creates child zettels with PDF links, renames folders, and updates the parent index. Idempotent — safe to run repeatedly.

**`/dd-2dataroom`** — Creates a Dataroom zettel with child zettels linking to every SEC filing (10-K/20-F, 10-Q, DEF 14A), shareholder letter, investor presentation, and earnings call transcript. Uses edgartools for EDGAR filings and web search for transcripts and letters.

**`/dd-2financials`** — Extracts multi-year financial statements (IS, BS, CF) and computes operating metrics tailored to the company type (bank vs. corporate vs. software). Outputs a JSON data file and an IB-formatted Excel workbook. Supports both EDGAR/XBRL extraction (US stocks) and PDF harvesting (Canadian/international).

**`/dd-2super-commentaries`** — Identifies which superinvestors from the vault's master list own a stock, then collects every piece of public commentary they've produced about it — shareholder letters, quarterly commentaries, podcasts, interviews, conference presentations, and articles. Creates a structured zettel tree under the ticker's Data Room with one child zettel per investor containing clickable links to all their commentaries.

## License

MIT
