---
name: dd-price-chart
description: Generate an annotated historical stock price chart for any ticker as part of Due Diligence. Fetches price data from Yahoo Finance, identifies significant price movements, web-searches for headlines explaining each move, fact-checks with a subagent, and renders a publication-quality PNG. Use when the user says /dd-price-chart, asks for an "annotated price chart", "historical price chart for DD", "price chart with events", or wants a visual price history for a stock they're researching. Also trigger when the user says "chart this stock" or "show me the price history of X with annotations".
---

# DD Price Chart

Generates a publication-quality annotated stock price chart for any Yahoo Finance ticker. Annotations are driven by significant price movements (drawdowns and rallies) plus key company milestones.

## Input Parsing

Parse the user's input for:
- **TICKER** (required): First argument, e.g., `AAPL`
- **TIMEFRAME** (optional): Either `YYYY-YYYY` range or `NY` lookback (e.g., `5Y`, `10Y`). Default: `max`
- **--log** (optional flag): If present, use logarithmic y-axis. Default: linear.
- **Custom events** (optional): If the user provides lines like `- 2007-06: iPhone launched`, use those instead of auto-research.

## Phase 1: Fetch Price Data

1. Use Python with `urllib` to hit Yahoo Finance:
   ```
   https://query1.finance.yahoo.com/v8/finance/chart/{TICKER}?range={range}&interval=1mo
   ```
   - `range` = `max` (default), or `5y`, `10y`, etc. For `YYYY-YYYY` ranges, fetch `max` and slice.
   - Set `User-Agent: Mozilla/5.0` header.
2. Parse `timestamps` and `indicators.quote[0].close`. Filter null values.
3. If fewer than 12 data points, warn the user and proceed.
4. Get the company's long name from `chart.result[0].meta.longName` for the title.

## Phase 2: Research Events

Skip this phase entirely if the user supplied custom events.

### Step 2a: Detect significant price movements

Run Python to analyze the price data:
1. Walk through monthly prices tracking running max and running min.
2. When price drops more than the threshold from a running max, record the trough date as a drawdown event.
3. When price rises more than the threshold from a running min, record the peak date as a rally event.
4. Dynamic thresholds based on total timeframe:
   - Over 20 years of data: 25%
   - 5-20 years: 20%
   - Under 5 years: 15%
5. Output a list of (date, direction) tuples.

### Step 2b: Research headlines for each movement

For each detected movement, use WebSearch:
- Query: `{TICKER} stock {month_name} {year} why {rose/fell}`
- Extract a concise 2-4 word label (e.g., "GFC crash", "iPhone launched")
- Also capture: a 1-2 sentence description, the source name, and the source URL
- Record: `{date, label, description, source_name, source_url}`

### Step 2c: Research key milestones

Use WebSearch:
- Query: `{company_long_name} key milestones history timeline`
- Extract structural events: IPO, product launches, CEO changes, major acquisitions, regulatory actions.
- Include milestones not already covered by price-movement events.

### Step 2d: Merge, de-duplicate, and cap

1. Combine movement events and milestone events.
2. If a milestone falls within 2 months of a movement event, keep whichever has the better label.
3. Ensure no two events are within 2 quarters of each other — drop the less significant one.
4. Cap at ~25 total. Priority: largest price moves first, then milestones.

### Step 2e: Fact-check with subagent

Spawn a **haiku** subagent with this prompt:
```
You are a fact-checker. For each event below, verify:
1. Did this event actually happen to {TICKER}/{company}?
2. Is the date approximately correct (within 1-2 months)?
3. Is the label accurate?

Reply with ONLY the events that PASS all checks. Drop any that fail.

Events:
{list of events}
```

Use the validated list going forward.

## Phase 3: Generate PDF

Run the PDF generation script: `python3 $CLAUDE_PLUGIN_ROOT/skills/dd-price-chart/scripts/generate_pdf.py`

Pass data via a temporary JSON file written by the skill before calling the script. The JSON contains:
```json
{
  "ticker": "AAPL",
  "company_name": "Apple Inc.",
  "dates_iso": ["1984-09-01", ...],
  "prices": [0.11, ...],
  "events": [
    {
      "date": "2007-06-01",
      "label": "iPhone\nlaunched",
      "description": "Apple unveiled the first iPhone, combining a phone, iPod, and internet device into one product that would redefine the smartphone industry.",
      "source_name": "Reuters",
      "source_url": "https://www.reuters.com/article/..."
    }
  ],
  "log_scale": false,
  "output_path": "/path/to/output.pdf"
}
```

The script:
1. Calls `generate_chart.py` internally to produce an intermediate PNG
2. Assembles a PDF with the chart on the top half
3. Adds an event reference table below with: Date, Event, Details, and Source (clickable link)
4. Cleans up the intermediate PNG

## Output Location

1. Search for a folder matching `$DD_OUTPUT_DIR/{TICKER}/` (where DD_OUTPUT_DIR defaults to `./due-diligence`)
2. If found, save there.
3. If not found, save to `$DD_OUTPUT_DIR/`
4. Filename: `{TICKER}_annotated_price_chart.pdf`

## Final Step

1. Read the generated PDF to display it to the user.
2. Report: file path, number of annotations, timeframe covered.
