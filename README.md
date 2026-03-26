# Due Diligence

Equity research due diligence toolkit for [Claude Code](https://claude.ai/code). Generates professional PDF reports for any stock ticker.

## Skills

| Command | What It Does |
|---------|-------------|
| `/dd-1bear TICKER` | Bear Case One-Pager — bearish theses from analysts, investors, journalists |
| `/dd-1honesty TICKER` | Management Honesty Check — did management deliver on projections? |
| `/dd-1ind TICKER` | Industry Analysis — market share, competitors, ecosystem |
| `/dd-1vl TICKER` | Value Line One-Pager — 15 years of financials on one page |
| `/dd-price-chart TICKER` | Annotated Price Chart — price history with event annotations |

## Installation

```bash
claude plugin install patrickwong/due-diligence
```

### Python Dependencies

```bash
pip install -r requirements.txt
```

Or let the scripts auto-install missing dependencies at runtime.

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DD_OUTPUT_DIR` | No | `./due-diligence` | Directory where PDF reports are saved |
| `EDGAR_IDENTITY` | No | — | Your name and email for SEC EDGAR access (e.g., `"Jane Doe jane@example.com"`). Required for `dd-1vl` to fetch 15 years of SEC filing data. Falls back to Yahoo Finance if not set. |

## Usage

Each skill is invoked as a slash command in Claude Code:

```
> /dd-1bear AAPL
> /dd-1honesty TSLA
> /dd-1ind MSFT
> /dd-1vl GOOG
> /dd-price-chart AMZN 2015-2025
```

Reports are saved to `$DD_OUTPUT_DIR/<TICKER>/`.

## License

MIT
