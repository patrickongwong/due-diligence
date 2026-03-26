---
name: dd-1vl
description: Generate a Value Line-style one-page PDF stock report for any US-listed company. Fetches 15 years of financial data from SEC EDGAR and Yahoo Finance, renders a dense single-page PDF with historical financials, price chart, capital structure, quarterly data, growth rates, ROIC, leverage ratios, and company-specific segment data. Use when the user asks for a "Value Line", "one-pager", "stock report", "stock summary", "/dd-vl", or "/dd-1vl" for a ticker.
---

# Value Line One-Pager Generator

## Usage

The user provides a stock ticker (via args or in their message). Optionally, provide the output name as a second argument for proper naming.

```bash
python3 $CLAUDE_PLUGIN_ROOT/skills/dd-1vl/scripts/value_line_onepager.py <TICKER> ["output name"]
```

**Examples:**
- `... value_line_onepager.py AAPL` → auto-detects DD folder, outputs to `due-diligence/{folder}/AAPL VL One Pager.pdf`
- `... value_line_onepager.py CSU.TO "dd1 CSU"` → outputs to `due-diligence/dd1 CSU/dd1 CSU VL One Pager.pdf`

## Before Running

1. Check that `EDGAR_IDENTITY` env var is set. If not, ask the user for their name and email, then set it:
   `export EDGAR_IDENTITY="Name email@example.com"`
   Set EDGAR_IDENTITY environment variable for SEC EDGAR access (e.g., "Your Name your@email.com"). If not set, falls back to Yahoo Finance data only.
2. Look up the output name for this stock in the DD folder structure (e.g., `dd1 CSU` for CSU.TO) and pass it as the second argument
3. The script auto-detects DD folders by matching the ticker to folder names

## Environment Variables

- `DD_OUTPUT_DIR` — Base directory for due diligence output (default: `./due-diligence`)
- `EDGAR_IDENTITY` — Required for SEC EDGAR access. Format: `"Your Name your@email.com"`. Falls back to Yahoo Finance if not set.

Note: On macOS with Homebrew-installed weasyprint, you may need to prefix the command with:
`DYLD_LIBRARY_PATH="/opt/homebrew/lib"` — this is only needed on macOS/Homebrew, not in other environments. Dependencies auto-install via the shared auto-install helper.

## Output Naming Convention

- With output name: `{folder_prefix} {date} {ticker} VL.pdf` (e.g., `dd1 2026-03-26 CSU VL.pdf`)
- Auto-detected: saves to the matching DD folder as `{folder_prefix} {date} {ticker} VL.pdf`
- Fallback (no DD folder found): `{TICKER}_value_line_{date}.pdf` in current directory

## Data Sources (in priority order)

1. **Local JSON** — checks `DD_OUTPUT_DIR/{folder}/financials/*_financials.json` first (richest data, any country)
2. **SEC EDGAR** — automatic for US-listed stocks via edgartools
3. **yfinance fallback** — basic data for anything else (~4-5 years)

## After Running

1. Report the output file path to the user
2. If any errors occurred, share the error output and suggest fixes
