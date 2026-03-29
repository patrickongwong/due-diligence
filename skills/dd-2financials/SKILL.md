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

2. **Excel workbook** (`{zettel_prefix} {TICKER} Financial Statements.xlsx`) — in the ticker's Dataroom folder. Contains 4 tabs:
   - Income Statement
   - Balance Sheet
   - Cash Flow Statement
   - Operating Metrics

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

### Step 6: Link in the Dataroom zettel

If the user's vault uses Zettelkasten with Obsidian:

1. Determine the next available child zettel ID under the Dataroom zettel
2. Create a new zettel with YAML frontmatter, an embed link to the Excel file, and source/date notes
3. Add a wikilink in the Dataroom zettel

### Step 7: Report to the user

Summarize: JSON path, Excel path with sheet names and period coverage, any data gaps, Dataroom link.

## Dependencies

- **edgartools** (`pip install edgartools`) — for EDGAR path only
- **openpyxl** — for Excel creation
- **pandas** — for data manipulation

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
