---
name: dd-phase1
description: Run Phase 1 of Due Diligence on a stock ticker — dispatches all five DD one-pager skills (Value Line, Industry Analysis, Management Honesty Check, Bear Case, Annotated Price Chart) in parallel and collects the results. Use this skill whenever the user says /dd-phase1, asks to "run phase 1 due diligence", "start DD on [ticker]", "run all the one-pagers for [ticker]", "kick off due diligence on [ticker]", or wants all five DD reports generated at once rather than invoking them individually. Also trigger when the user asks for a "full DD overview", "initial DD package", or "phase 1 on [ticker]".
---

# DD Phase 1: Parallel Due Diligence One-Pagers

Phase 1 due diligence generates five independent research reports on a single ticker. Because none of the five reports depend on each other, they all run simultaneously — cutting wall-clock time from ~25 minutes to ~8 minutes.

## What gets produced

| Report | Skill | Output |
|--------|-------|--------|
| Value Line one-pager | `/dd-1vl` | `{TICKER}_VL.pdf` — 15-year financials, price chart, capital structure |
| Industry analysis | `/dd-1ind` | `{TICKER}_Industry_Analysis.pdf` — market share, competitors, ecosystem |
| Management honesty check | `/dd-1honesty` | `{TICKER}_Honesty_Check.pdf` — projections vs. actuals |
| Bear case | `/dd-1bear` | `{TICKER}_Bear_Case_One_Pager.pdf` — strongest bearish arguments |
| Annotated price chart | `/dd-1price-chart` | `{TICKER}_annotated_price_chart.pdf` — price history with event annotations |

All outputs land in the same folder (typically `dd Due Diligence/<TICKER>/` or `$DD_OUTPUT_DIR/<TICKER>/`).

## How to execute

### 1. Extract the ticker

The user provides a ticker (e.g., `AAPL`, `CSU.TO`, `NVDA`). If no ticker is given, ask for one before proceeding.

### 2. Dispatch all five skills in parallel

Spawn **five subagents in a single message** — one per skill. Each subagent should invoke the corresponding skill via the Skill tool and pass the ticker. Use `run_in_background: true` so all five launch simultaneously.

Each subagent prompt should follow this pattern:

```
You are running a due diligence report for ticker: {TICKER}

Invoke the Skill tool with skill: "dd-1vl" (or the relevant skill name) and args: "{TICKER}".
Then follow the skill's instructions exactly to produce the output.

Why: This is one of five Phase 1 DD reports being generated in parallel. Your job is just this one report — other agents are handling the rest.
```

The five skill names to invoke are:
- `dd-1vl` with args: `"{TICKER}"`
- `dd-1ind` with args: `"{TICKER}"`
- `dd-1honesty` with args: `"{TICKER}"`
- `dd-1bear` with args: `"{TICKER}"`
- `dd-1price-chart` with args: `"{TICKER}"`

### 3. Monitor and report

As each subagent completes, note which report finished and whether it succeeded. When all five are done, give the user a summary:

```
Phase 1 DD complete for {TICKER}:
  [done] Value Line one-pager
  [done] Industry analysis
  [done] Management honesty check
  [done] Bear case
  [done] Annotated price chart

All reports saved to: dd Due Diligence/{TICKER}/
```

If any report fails, note the failure and offer to retry just that one.

## Notes

- The Value Line report (`dd-1vl`) uses a Python script and may need dependencies installed. If it fails on first run, check the error — it often just needs `pip install` for a missing package.
- For Canadian or international tickers (e.g., `CSU.TO`), all five skills support them, but data availability may vary.
- If the user wants to customize the price chart timeframe (e.g., 5Y instead of max), they should run `/dd-1price-chart` separately with the timeframe argument after Phase 1 completes.
