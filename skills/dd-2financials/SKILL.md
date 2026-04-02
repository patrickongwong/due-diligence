---
name: dd-2financials
description: Extract historical financial statements (Income Statement, Balance Sheet, Cash Flow) and operating metrics for any ticker — from SEC EDGAR XBRL for US stocks, or from company annual report PDFs for Canadian/international stocks. Saves to JSON and a professionally formatted Excel workbook with Wall Street IB conventions. Use this skill whenever the user says /dd-2financials, asks to "pull financials for [ticker]", "get financial statements for [ticker]", "extract 10-K data", "build a financial data file", "create financial statements Excel", or wants historical financial data compiled for due diligence. Also trigger when the user asks to "add financials to the dataroom" or "get IS/BS/CF for [ticker]".
---

# Financial Statements & Operating Metrics Extractor

Pull multi-year financial statements and operating metrics for any publicly traded company, then output a JSON database and a professionally formatted Excel workbook.

## Core Principle: Scout First, Harvest After

Every company reports differently. A bank's income statement looks nothing like a software company's. A Canadian IFRS filer structures things differently from a US GAAP SEC filer. The data source matters too — SEC EDGAR gives you XBRL with hundreds of structured line items; a PDF annual report gives you exactly the line items the company chose to disclose.

**Do NOT start from a rigid template and try to fill it in.** Instead:

1. **Scout** — Look at what data is actually available for this company. Read the source (EDGAR filing, PDF annual report, existing JSON). Understand the company's reporting structure, what line items exist, what's unique about this company.
2. **Harvest** — Extract every line item the company reports, preserving their labels and structure. Don't skip items that don't fit a generic template.
3. **Compute** — Calculate operating metrics from whatever data was harvested. Different companies yield different metrics — a bank gives you NIM and NCO ratios; a serial acquirer gives you acquisition spend as % of OCF; a SaaS company gives you recurring revenue %.
4. **Format** — Build the Excel using the harvested data, organizing into sections that match how this company actually reports.

## What This Skill Produces

1. **JSON data file** (`{zettel_prefix} {TICKER}.json`) — at `dd Due Diligence/` level per the DD CLAUDE.md convention. Contains all financial statement line items and computed operating metrics with source attribution.

2. **Excel workbook** (`{zettel_prefix} {TICKER} Financial Statements.xlsx`) — in the ticker's Dataroom folder. Contains 8 tabs:
   - Income Statement (with SUM formulas + "(reported)" verification rows)
   - Balance Sheet (with SUM formulas + "(reported)" verification rows)
   - Cash Flow Statement (with SUM formulas + "(reported)" verification rows)
   - Operating Metrics (includes Yahoo Finance market data section at the bottom, clearly labeled)
   - Vertical Common Size (each item as % of Revenue/Total Assets)
   - Horizontal Common Size (YoY % change)
   - DuPont Analysis (3-factor + 5-factor ROE decomposition)
   - QoE — Quality of Earnings (O'Glove framework, applied to available data)

3. **Dataroom link** — if the user has a Zettelkasten in Obsidian, append a wikilink to the Dataroom zettel.

## Workflow

### Step 1: Locate the DD folder and identify the data source

Parse the ticker. Find the DD folder (`dd Due Diligence/{zettel_prefix} {TICKER}/`). If none exists, ask the user or suggest `/dd-2dataroom` first.

Identify paths:
- Dataroom subfolder (the folder named `*Dataroom*`)
- Dataroom zettel (the `.md` file named `*Dataroom*`)
- JSON data file: `dd Due Diligence/{zettel_prefix} {TICKER}.json`

Check if we already have data in the JSON. If it contains `financial_statements` and `operating_metrics`, inform the user and ask whether to refresh.

### Step 2: Scout — determine what data is available

This is the critical step. Don't jump straight to extraction.

**For US-listed companies (SEC EDGAR filers):**
- Try edgartools: `Company(TICKER)` → check if 10-K (or 20-F) filings exist
- If XBRL data is available, proceed to the EDGAR extraction path (Step 3A)
- If not, check for annual report PDFs in the Dataroom folder

**For non-US companies (Canadian, international):**
- Check the Dataroom folder for existing annual report PDFs or financial JSON files
- Check the Dataroom zettel for links to annual reports on the company IR website
- If PDFs exist, proceed to the PDF harvesting path (Step 3B)

**For either path — scout the actual content first:**
- Read 1-2 pages of the financial statements from the most recent annual report
- Note exactly what line items the company discloses (revenue breakdown, expense categories, segment data, below-the-line items)
- Note anything company-specific (CSU's IRGA revaluation charges, ALLY's operating lease revenue, insurance segments, etc.)
- This scouting informs how you structure the extraction and what metrics to compute

### Step 3A: EDGAR Extraction Path (US companies)

Run the extraction script:
```bash
python3 {skill_path}/scripts/extract_financials.py {TICKER} {json_output_path}
```

This script iterates through 10-K filings, extracts IS/BS/CF via XBRL, merges multi-year data, and deduplicates. It processes enough filings to cover all XBRL-available years, stopping when XBRL parsing fails.

After extraction, run the metrics computation:
```bash
python3 {skill_path}/scripts/compute_metrics.py {json_path} {TICKER}
```

This computes whatever metrics are possible from the available data — bank metrics (NIM, NCO ratio, CET1) for financials, corporate metrics (operating margin, ROIC, FCF margin) for non-financials. It also tries to enrich with XBRL regulatory facts.

### Step 3B: PDF Harvesting Path (non-EDGAR companies)

This is the "scout first" path. Do NOT use the EDGAR scripts. Instead:

1. **Read the most recent annual report PDF** — find the financial statement pages (usually after the auditor's report). Note every line item in IS, BS, CF.

2. **Dispatch a subagent** to read through the annual report PDFs (every other PDF to avoid overlap, since each report has 2 years of data). The subagent should:
   - Extract EVERY line item the company reports, not just a predefined list
   - Preserve the company's own labels and groupings
   - Handle format changes across years (e.g., GAAP to IFRS transition, line items being added/removed/renamed)
   - Save to a structured JSON (dict-of-dicts: `{section: {line_item: {year: value}}}`)

3. **Convert to standard format** — transform the harvested data into the `financial_statements` format (list of `{line_item, year1, year2, ...}` dicts) and compute operating metrics tailored to the company.

4. If existing financial data already exists (e.g., a `*_financials.json` in the Dataroom), convert it using:
   ```bash
   python3 {skill_path}/scripts/convert_existing_json.py {existing_json} {output_json} {TICKER}
   ```

**Key principle for PDF harvesting:** The line items you extract should match what the company actually reports. A software company like CSU reports revenue by type (License, Professional Services, Hardware, Maintenance/Recurring) and expenses by nature (Staff, Hardware, Third-party, Occupancy, etc.). Don't try to force this into Revenue → COGS → Gross Profit format if that's not how they report.

### Step 4: Compute Operating Metrics

Metrics should be **tailored to the company type**, computed from whatever data was harvested:

**Universal metrics (all companies):**
- ROE, ROA, effective tax rate
- Revenue growth (YoY)
- Net margin
- EPS, BVPS, DPS, payout ratio

**Corporate / tech / software (like CSU):**
- Operating margin, net margin
- ROIC (NOPAT / invested capital)
- OCF margin, FCF margin (OCF - capex)
- Revenue composition (recurring %, by segment)
- Acquisition spend and acquisitions as % of OCF
- D&A breakdown
- Staff as % of revenue
- Debt-to-equity, current ratio
- Intangibles as % of assets

**Bank / financial (like ALLY):**
- NIM, efficiency ratio, PPNR
- Yields and spreads (yield on loans, cost of deposits, net interest spread)
- NCO ratio, provision/loans, allowance/loans, provision/NCO coverage
- Regulatory capital (CET1, Tier 1, Total Capital ratios)
- Loan-to-deposit ratio, deposits/liabilities
- Insurance loss ratio (if applicable)
- ROTCE, TBVPS

The point is: compute what makes sense for THIS company, not a fixed list.

### Step 5: Format the Excel Workbook

Build the Excel with sections that match how the company actually reports. Read `references/formatting.md` for the IB formatting conventions:

- **Font:** Arial 10pt, gridlines off
- **Section headers:** Light blue fill (`D9E1F2`), bold
- **Line items:** Indented, regular weight
- **Subtotals:** Bold, single top border
- **Grand totals:** Bold, thin top + double bottom border
- **Numbers:** `#,##0;(#,##0);"-"` — commas, parentheses for negatives
- **Per-share:** `$#,##0.00`, **Percentages:** `0.0%` or `0.00%`
- **Units** stated once in subtitle, landscape orientation, fit-to-width

For the IS structure, use whatever structure matches the company:
- Banks: Interest Income → Interest Expense → NII → Other Revenue → Provision → NIE → Net Income
- Software/corporate: Revenue (by type) → Expenses (by nature or function) → Other Items → Pre-tax → Tax → Net Income
- Don't force one structure onto the other

The Operating Metrics tab should also be organized into sections relevant to this company.

### Step 6: Audit summations and add formula verification

After the Excel is built, audit every summation row for correctness and replace hardcoded totals with live Excel formulas. This step catches missing line items and rounding discrepancies.

**Summation rows to audit (at minimum):**
- IS: Total revenue, Total expenses, Income before taxes, Total income tax, Net income
- BS: Total current assets, Total non-current assets, Total assets, Total current liabilities, Total non-current liabilities, Total liabilities, Total equity, Total L&E
- CF: Net cash from operating, Net cash from investing, Net cash from financing, Net change in cash, Cash end of period

**For each summation row:**
1. Replace the hardcoded value with an **Excel SUM or addition formula** referencing the component rows (e.g., `=SUM(C6:C9)` for Total revenue)
2. Compare what the formula produces against the PDF-reported total
3. If they differ by more than $0.5M, insert a **"(reported)"** row directly below the formula row containing the original PDF-stated value, formatted in **grey italic** font (color `808080`) — same subtle style as verification/sanity-check rows
4. The formula row is the "live" version; the "(reported)" row preserves the auditor-friendly PDF source value

**When discrepancies indicate missing line items** (e.g., Current Liabilities formula is $500M below the reported total), go back to the source PDFs and extract the missing items. Common culprits:
- **Balance Sheet Current Liabilities**: Often missing bank debt/credit facilities, dividends payable, provisions, acquisition holdback payables, lease obligations, income taxes payable, redeemable preferred securities, TSS/IRGA membership liabilities
- **Balance Sheet Non-Current Liabilities**: Often missing individual debt facilities, debentures, deferred income taxes, acquisition holdbacks, lease obligations, other liabilities
- **Cash Flow Financing Activities**: Often missing credit facility movements (CSI facility, revolving credit, term debt proceeds/repayments), debt transaction costs, lease payments, distributions to minority owners, bank indebtedness changes
- **Cash Flow Operating Activities**: May be missing non-cash adjustments like equity investee income, depreciation of third-party costs, finance income (in IFRS presentations where these are CF adjustments)

**Accounting standard transitions** (e.g., Canadian GAAP → IFRS) will naturally produce different line items across years. Handle this by:
- Showing IFRS nature-format expense lines (Staff, Hardware, Third party, etc.) for IFRS years
- Showing GAAP functional-format lines (COGS, R&D, S&M, G&A) for GAAP years
- Keeping both sets of rows in the same sheet — cells are simply blank for years where that format doesn't apply
- Reporting individual expense lines (Travel, Telecom, Supplies, Software & equipment) separately when the source reports them that way, rather than combining them

All summation formulas, "(reported)" verification rows, and analysis tabs are built directly into the single output workbook — there is no separate version.

### Step 7: Add analysis tabs to the v2 workbook

After the v2 is built with audited formulas, add three analysis sheets. All must use **Excel formulas referencing the source sheets** (e.g., `='Income Statement'!C6/'Income Statement'!C10`) so they auto-update.

#### Sheet 5: Vertical Common Size

Express every line item as a percentage of a base figure for the same year:
- **IS line items** → % of Total Revenue
- **BS line items** → % of Total Assets
- **CF line items** → % of Total Revenue (more meaningful than % of OCF)

Wrap all formulas in `IFERROR(...,"")` to handle blanks. Format: `0.0%`. Include all line items from IS, BS, and CF (skip "(reported)" rows). Use the same section headers as the source sheets.

#### Sheet 6: Horizontal Common Size (YoY % Change)

Express every line item as **year-over-year percentage change** from the prior year:
- Formula: `=IFERROR((CurrentYear - PriorYear) / ABS(PriorYear), "")`
- Years run left-to-right newest-to-oldest (C=most recent), so "prior year" = one column to the RIGHT
- The earliest year column is blank (no prior year available)

Format: `0.0%`. Same sections and line items as Vertical sheet.

#### Sheet 7: DuPont Analysis

Formula-based decomposition of ROE using source sheet references. Use **average balance sheet figures** (current + prior year / 2) for proper matching with income statement flows.

**3-Factor DuPont:**
- Net Profit Margin = Net Income / Revenue
- Asset Turnover = Revenue / Avg Total Assets
- Equity Multiplier = Avg Total Assets / Avg Total Equity
- **ROE (3-Factor)** = product of above three (bold, double bottom border)
- ROE (direct, verification) — grey italic sanity check row

**5-Factor DuPont:**
- Tax Burden = Net Income / Pre-tax Income
- Interest Burden = Pre-tax Income / EBIT
- EBIT Margin = EBIT / Revenue (where EBIT = Revenue - Total Expenses)
- Asset Turnover (same formula)
- Equity Multiplier (same formula)
- **ROE (5-Factor)** = product of all five (bold, double bottom border)
- ROE (direct, verification) — grey italic sanity check row

**Supporting Metrics:**
- EBIT ($mm), EBITDA ($mm), EBITDA Margin
- Net Debt ($mm) = Total Liabilities - Cash
- ROIC = NOPAT / Avg Invested Capital (where NOPAT = EBIT × (1 - effective tax rate), Invested Capital = Equity + Net Debt)

**Formatting for all analysis tabs:**
- Same IB standard: Arial 10pt, gridlines off, landscape, fit-to-width
- Section headers: light blue fill (`D9E1F2`), bold
- Subtotal rows: bold, thin top border
- Grand total rows: bold, thin top + double bottom border
- No green font on cross-sheet references — keep all text black
- Verification/sanity-check rows: grey italic (`808080`)

#### Sheet 8: Quality of Earnings (QoE)

Apply Thornton O'Glove's Quality of Earnings framework (from `ln99a How To Figure Out Quality Of Earnings`) to the financial data. This sheet uses **only Excel formulas referencing the source sheets** so it auto-updates.

**Core principle: work with what's available.** O'Glove's framework has 10 tests but not all apply to every company or every dataset. Scout the IS, BS, and CF tabs first to see which line items exist, then build only the tests that the data supports. Do NOT add blank sections for tests that can't be computed.

**The 5 tests that are typically computable from financial statement data:**

**Section 1: Strip Out Nonoperating & Nonrecurring Income (NO/NR)**

Scout the Income Statement "Other Items" section (below Total Expenses, above Pre-tax Income) for nonoperating/nonrecurring items. Common examples — but every company is different:
- Foreign exchange gains/losses
- Asset revaluations (IRGA/TSS, equity method, held-for-trading)
- Bargain purchase gains
- Impairment charges
- One-time securities expenses (redeemable preferred revaluation)
- Investment/finance income not from core operations
- Gains/losses on asset sales

For each item found, pull it via a cross-sheet reference. Then compute:
- **Adjusted operating pre-tax income** = Reported pre-tax + SUM(NO/NR items). The sign convention: in many IS layouts, these items are subtracted from operating income to arrive at pre-tax income, so adding them back removes their effect. Verify the sign logic against the specific IS structure — if `Pre-tax = Revenue - Expenses - Other Items`, then `Adjusted = Pre-tax + Other Items (NO/NR subset)`.
- **Total NO/NR items** and **NO/NR as % of reported pre-tax** — highlights how much of reported earnings is noise
- **Adjusted pre-tax YoY growth** — the true operating trajectory
- **Adjusted operating EPS (after-tax)** = Adjusted pre-tax × (1 - effective tax rate) / shares outstanding

**Section 2: Analyse Declining & Increasing Expenses**

Three sub-sections:

*Expenses as % of Revenue:* For each expense line item in the IS, compute `= expense / total revenue`. Format as `0.0%`.

*YoY Change in Expense %:* For each expense line, compute the change in its percentage from the prior year to the current year. Since columns run left-to-right newest-to-oldest (C=most recent), "prior year" = one column to the RIGHT. The **earliest year column is blank** (no prior year). Formula: `= current_year_pct - prior_year_pct` (positive = expense rose as % of revenue). Format as `0.0%`.

*Per-Share Impact of Expense Changes:* Quantify how much each expense shift contributed to or detracted from EPS. Formula: `(prior_year_pct - current_year_pct) × current_year_revenue / current_year_shares`. Positive = margin benefit (expense % fell). Format as `#,##0.00`. Earliest year column blank.

**Section 3: Watch Accounts Receivable & Inventories vs. Sales**

Three sub-sections:

*Absolute Values:* Pull total revenue, accounts receivable, unbilled revenue (if the company reports it), inventories, and deferred revenue from the source sheets.

*YoY Growth Rates:* Compute growth for each line. Column direction: current year (left) divided by prior year (right) minus 1. Earliest year blank.

*Divergence Analysis:* Compute `A/R growth - Revenue growth` and `Inventory growth - Revenue growth`. Format as `0.0%`. Positive = that balance grew faster than sales (O'Glove red flag).

*Efficiency Ratios:* DSO (`A/R / Revenue × 365`), DIO (`Inventory / Revenue × 365`), Deferred Revenue Days (`Deferred Revenue / Revenue × 365`). Format as `0.0`.

**Section 4: Analyse Debt & Cash Flow**

*Income vs. Cash Flow:* Pull net income (reported) and operating cash flow. Compute `OCF - Net Income` (the gap) and `OCF / Net Income` ratio (format `0.0x`). Ratio > 1.0x is a green flag; persistently < 1.0x is O'Glove's primary red flag.

*Cash Flow Bridge:* Pull every line item from the CF Operating Activities section (net income, D&A, non-cash adjustments, working capital changes, taxes paid) to show exactly how net income converts to OCF.

*Cash Flow Adequacy:* Pull FCF, capex, acquisition spend, interest paid, dividends paid. Compute:
- `OCF coverage of interest + dividends` (format `0.0x`)
- `FCF after acquisitions` (= FCF - acquisition spend)
- OCF margin and FCF margin from Operating Metrics

**Section 5: Evaluate Dividend Policy**

*Dividend Analysis:* Pull EPS, DPS, OCF per share. Compute:
- `Payout ratio (DPS / EPS)` — format `0.0%`
- `DPS as % of OCF per share` — format `0.0%`. This is the cash-based payout ratio.

*Debt Trajectory:* Compute total debt by summing all borrowing line items from the BS (scout for what exists — bank debt, credit facilities, senior notes, debentures, IRGA liabilities, etc.). Then:
- Cash and equivalents (from BS)
- Net debt (= total debt - cash)
- `Net debt / OCF` ratio (format `0.0x`)

**Formatting specifics for QoE tab:**
- Each test section gets a **dark blue banner row** (fill `1F4E79`, white bold text) spanning all columns as a visual separator
- Below each banner, a grey italic note row explaining the purpose of the test
- **Signal rows** (the key diagnostic ratios) get a light yellow fill (`FFF2CC`) so they stand out
- Subtotal/adjusted rows get a light green fill (`E2EFDA`) with bold + double bottom border
- Column B width ~45 for labels, data columns ~13 each
- Freeze panes at C5 so headers stay visible while scrolling

**Column direction reminder (critical):** Years run left-to-right newest-to-oldest. All YoY formulas must compare current (left) to prior (right). The blank/empty cell goes in the **rightmost data column** (earliest year), NOT the leftmost.

### Step 8: Append Yahoo Finance market data to Operating Metrics

After the analysis tabs are complete, fetch market data from Yahoo Finance using Python's `yfinance` library and append it as a clearly separated section at the bottom of the Operating Metrics tab. This data supplements the annual-report-derived metrics above with market pricing and valuation context.

**Why this step is separate and labeled:** The financial statement data (Steps 1–7) comes directly from audited filings — it's primary source data. The yfinance data is secondary market data that can change, may have gaps, and uses a different currency for some tickers. Keeping them visually distinct helps the user know exactly which numbers came from the company's own filings and which came from Yahoo Finance.

#### 8a. Fetch year-end closing prices

```python
import yfinance as yf
ticker = yf.Ticker(TICKER_SYMBOL)  # e.g., 'TOI.V', 'CSU.TO', 'ALLY'
hist = ticker.history(period='max')
```

For each year covered by the financial statements, extract the **last trading day's closing price**:
```python
for year in years:
    year_data = hist[hist.index.year == year]
    if len(year_data) > 0:
        price = year_data.iloc[-1]['Close']
```

Some tickers won't have data for all years (e.g., TOI.V only started trading in 2021 after the CSI spin-off). Leave those years blank — don't interpolate or estimate.

#### 8b. Fetch current snapshot metrics from `ticker.info`

The `ticker.info` dictionary contains a rich set of current market data. Extract whatever is available — the exact fields vary by ticker and exchange. Common useful fields:

| Field | Description |
|-------|-------------|
| `marketCap` | Current market cap (in trading currency) |
| `enterpriseValue` | Current EV |
| `trailingPE` | Trailing P/E |
| `forwardPE` | Forward P/E (analyst consensus) |
| `priceToBook` | Price / Book |
| `enterpriseToEbitda` | EV / EBITDA |
| `enterpriseToRevenue` | EV / Revenue |
| `profitMargins` | Net margin |
| `dividendYield` | Current dividend yield |
| `payoutRatio` | Dividend payout ratio |
| `beta` | Beta (vs market) |
| `fiftyTwoWeekHigh` | 52-week high |
| `fiftyTwoWeekLow` | 52-week low |
| `shortPercentOfFloat` | Short interest (% of float) |
| `heldPercentInsiders` | Insider ownership % |
| `heldPercentInstitutions` | Institutional ownership % |
| `currency` | Trading currency (e.g., CAD, USD, EUR) |

Not all fields exist for every ticker. Use `.get()` with `None` defaults and skip any that return `None`.

#### 8c. Write to the Operating Metrics tab

Add a **section header row** with a distinct label so the user immediately knows the data source:

```
Market Data (source: Yahoo Finance via yfinance)
```

Use the same IB formatting (light blue fill, bold) as other section headers, but append ` — source: Yahoo Finance` in the header text.

**Historical valuation rows** (one value per year, like the rest of the Operating Metrics tab):

| Row | Formula | Format |
|-----|---------|--------|
| Year-end Share Price | From yfinance history | `$#,##0.00` |
| Market Cap (diluted) | Price × diluted shares outstanding | `#,##0` (in millions of trading currency) |
| P/E (trailing) | Price / EPS diluted | `0.0x` |
| Price / OCF per share | (Price × diluted shares) / OCF | `0.0x` |
| Price / EBITDA | (Price × diluted shares) / EBITDA | `0.0x` |
| Price / Book Value | (Price × diluted shares) / Total Equity | `0.0x` |
| FCF Yield | FCF / (Price × diluted shares) | `0.0%` |

**Cross-currency note:** When the trading currency (from `ticker.info['currency']`) differs from the reporting currency (from the financial statements), add a grey italic note row below the section header:

```
Note: Valuation multiples are cross-currency ({trading_ccy} price / {reporting_ccy} fundamentals). [Ticker] began trading [date].
```

This is important because many Canadian-listed companies (CSU.TO, TOI.V) trade in CAD but report in EUR or USD. The multiples are still directionally useful for tracking trends over time, but the user should know they aren't pure same-currency ratios.

**Current snapshot rows** (single value in the most recent year's column, or a separate mini-section):

Add a second sub-header: `Current Snapshot (as of {today's date})`

Include whatever `ticker.info` fields are available:
- Current Price, Market Cap, Enterprise Value
- Trailing P/E, Forward P/E, EV/EBITDA, EV/Revenue, Price/Book
- Dividend Yield, Payout Ratio
- Beta, 52-Week High, 52-Week Low
- Short % of Float, Insider Ownership %, Institutional Ownership %

Format the current snapshot as a two-column layout (label in column A, value in column B) below the historical valuation rows, since these are point-in-time values that don't map to specific fiscal years.

#### 8d. Save to JSON

Also add the yfinance data to the JSON data file under a `market_data` key:

```json
{
  "market_data": {
    "source": "Yahoo Finance (yfinance)",
    "trading_currency": "CAD",
    "year_end_prices": {"2021": 113.87, "2022": 69.72, ...},
    "current_snapshot": {
      "date": "2026-03-31",
      "price": 93.85,
      "market_cap": 12183000000,
      "beta": 0.85,
      ...
    }
  }
}
```

#### 8e. Dependencies

Add `yfinance` (`pip install yfinance`) to the dependencies list. It's a lightweight library that wraps Yahoo Finance's public API — no API key needed.

### Step 9: Link in the Dataroom zettel

If the user's vault uses Zettelkasten with Obsidian:

1. Determine the next available child zettel ID under the Dataroom zettel
2. Create a new zettel with YAML frontmatter, an embed link to the Excel file, and source/date notes
3. Add a wikilink in the Dataroom zettel

### Step 10: Report to the user

Summarize: JSON path, Excel path (8 tabs) with period coverage, any data gaps or discrepancies found during audit, Dataroom link, and which years had yfinance market data available.

## Dependencies

- **edgartools** (`pip install edgartools`) — for EDGAR path only
- **openpyxl** — for Excel creation
- **pandas** — for data manipulation
- **yfinance** (`pip install yfinance`) — for market data (year-end prices, current snapshot)

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/extract_financials.py` | EDGAR/XBRL extraction for US stocks |
| `scripts/compute_metrics.py` | Compute metrics from standard JSON (primarily for EDGAR data) |
| `scripts/convert_existing_json.py` | Convert flat financial JSON to standard format |
| `scripts/format_excel.py` | Create IB-formatted Excel (works with EDGAR-extracted data) |

For PDF-harvested data, the formatting is typically done inline (as a Python script written during the session) because each company's line items are unique. The bundled `format_excel.py` handles the EDGAR path where line items follow XBRL taxonomy labels.

## Edge Cases

- **Non-US 20-F filers**: EDGAR script tries 20-F as fallback
- **Canadian/international companies**: Use PDF harvesting path. Per user preference, scrape from company IR website rather than Yahoo Finance
- **Pre-XBRL filings**: Only XBRL-enabled filings can be parsed via EDGAR. Script stops after 3 consecutive failures
- **Accounting standard transitions**: Some companies switched from Canadian GAAP to IFRS (CSU in 2010) or US GAAP to IFRS. Line items change. The harvesting approach handles this naturally — just capture what's there each year
- **Financial vs. non-financial**: Detected automatically from line items. Don't force bank metrics on a tech company or vice versa
