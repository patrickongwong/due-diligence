---
name: dd-1bear
description: Generate a Bear Case One-Pager PDF for any stock ticker — compiles the strongest bearish arguments from sell-side analysts, famous investors, and financial journalists with clickable source links. Use this skill whenever the user says /dd-1bear, asks for a "bear case", "bearish arguments", "bear one-pager", "devil's advocate on [ticker]", "what are the risks of [ticker]", "who's bearish on [ticker]", or wants to understand why smart people are betting against a stock. Also trigger when the user asks to "steelman the bear case" or "find the biggest critics" of a stock. Works for any publicly traded stock — US, international, any exchange.
---

# Bear Case One-Pager

Compile the strongest bearish arguments against a stock from the smartest bears — sell-side analysts, famous investors, and financial journalists — into a professional PDF with clickable source links and dates for every claim.

## Input

The user provides a **ticker symbol** (e.g., `AAPL`, `TSLA`, `2330.TW`, `BABA`). If the user gives a company name instead, resolve it to the ticker. If ambiguous, ask.

Optional: the user may specify an output folder. Default: `$DD_OUTPUT_DIR/<TICKER>/` (where DD_OUTPUT_DIR defaults to `./due-diligence` if not set).

## Workflow

### Step 1: Fetch valuation data

Use Python's `yfinance` library to get current market data for the ticker:
- Current price, market cap
- Trailing P/E, Forward P/E, Price/Sales, Price/Book
- Revenue growth (YoY), EPS growth (YoY)
- 52-week high/low, % below 52-week high
- YTD return, dividend yield
- RSI (14-day) approximation from price history

This step can run as a subagent in parallel with the research steps.

### Step 2: Research bearish arguments (parallel subagents)

Launch **three research subagents** simultaneously, plus a valuation data subagent. Each subagent must include the ticker AND company name in its search queries. Include "Why" context in each subagent prompt so it knows what signal to prioritize.

**Subagent A — Sell-side analysts:**
Search for analysts with Sell/Underweight/Underperform/Reduce ratings. For each, capture: analyst name, firm, date, rating, price target, specific bear thesis (2-3 sentences), and source URL.

**Subagent B — Famous investors/fund managers:**
Search for investors who have sold, shorted, or publicly criticized the stock. Check 13F filings for major position reductions. For each, capture: investor name, firm, date, action taken, thesis, and source URL.

**Subagent C — Financial journalists/commentators:**
Search for well-reasoned bear cases from Bloomberg, FT, WSJ, Barron's, Seeking Alpha, and independent analysts. Look for thematic risks: valuation, competitive threats, regulatory, macro, management, product cycle, geographic exposure. For each, capture: author, publication, date, thesis, key data points, and source URL.

### Step 3: Fact-check

Launch a **fact-checker subagent** that takes all claims from Steps 2A-C and verifies each one against web sources. For each claim, it returns VERIFIED, PARTIALLY CORRECT, or UNVERIFIED with the correction. Any claim marked UNVERIFIED should be dropped. PARTIALLY CORRECT claims should be amended.

### Step 4: Synthesize into thematic bear theses

Group the verified findings into **5-8 thematic bear theses**, ordered by severity. Common themes include (but adapt to the specific stock):
- Valuation premium vs. growth
- Competitive threats / market share loss
- Regulatory / antitrust risk
- Geographic concentration risk (e.g., China)
- Product cycle maturity / innovation concerns
- Supply chain / tariff exposure
- Management / leadership transitions
- Balance sheet / capital allocation concerns

Each thesis gets:
- A bold title (e.g., "VALUATION: PAYING A GROWTH MULTIPLE FOR A MATURE BUSINESS")
- One paragraph (3-5 sentences) with **bold inline dates** for every claim — e.g., "JPMorgan (**Jul 30, 2025**) estimated..."
- 2-3 clickable source links with descriptive labels

### Step 5: Generate the PDF

Run the bundled PDF generator script at `$CLAUDE_PLUGIN_ROOT/skills/dd-1bear/scripts/generate_bear_pdf.py`. Pass it a JSON file with all the structured data. The script produces a professional PDF with:

- **Dark header banner** spanning full page width: `{TICKER} BEAR CASE` with subtitle showing company name, date, price, market cap
- **Valuation metrics strip**: 8 key metrics, bearish values in red
- **Bearish sell-side analysts table**: Analyst, Firm, Date, Rating, PT, Implied Downside (6 columns, full width)
- **Bear theses by risk**: Each thesis with paragraph + clickable source links
- **Notable bears table**: Who, When, Action, Key Argument, Source (5 columns, full width)
- **Closing synthesis**: One italic paragraph summarizing the overall bear case
- **Footer**: "Compiled [date] by Januarius Holdings Inc." with disclaimer

The PDF must have:
- All source links clickable (blue, underlined)
- All dates bold and prominent
- No text overlap — adequate row heights
- All tables spanning full 7.5" available width
- Letter size, 0.5" margins

### Step 6: Save and open

Save the PDF to `$DD_OUTPUT_DIR/<TICKER>/<TICKER>_Bear_Case_One_Pager.pdf` (or user-specified path). Open it for the user.

## Writing Style

Write in the style of a sharp equity research analyst — concise, data-heavy, no fluff. Every sentence should contain either a number, a date, or a named source. The closing paragraph should be written in the style of Malcolm Gladwell — punchy, quotable, and memorable.

## Quality Checklist

Before delivering the PDF, verify:
- [ ] Every thesis paragraph has at least one bold date
- [ ] Every source link is clickable and has a descriptive label
- [ ] Analyst table has a Date column
- [ ] Notable bears table has a When column
- [ ] No text overlap in the PDF
- [ ] Header and all tables span full page width
- [ ] Fact-checker subagent ran and corrections were applied
- [ ] At least 5 distinct bear theses are included
- [ ] Valuation data is current (from yfinance)

## Example invocations

```
/dd-1bear TSLA
/dd-1bear NVDA
/dd-1bear 2330.TW
bear case for META
who's bearish on AMZN?
steelman the bear case for MSFT
```
