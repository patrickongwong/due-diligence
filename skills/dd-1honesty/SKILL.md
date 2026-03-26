---
name: dd-1honesty
description: Generate a Management Honesty Check PDF (2-3 pages) for any stock ticker — finds what current management publicly projected (revenue targets, margin goals, store openings, product launches, strategic milestones) and checks whether they delivered. Use this skill whenever the user says /dd-1honesty, asks for a "management honesty check", "projection accuracy", "did management deliver", "guidance track record", "are they honest", "do they keep promises", "management credibility", or wants to evaluate whether a company's leadership follows through on what they say. Also trigger when the user asks "can I trust this management team" or "how accurate is their guidance". Works for any publicly traded stock.
---

# Management Honesty Check

Find what current management publicly projected — financial targets, operational milestones, strategic promises — and check whether they actually delivered. The output is a 2-3 page PDF that lays out projections vs. actuals without scoring or grading, letting the reader draw their own conclusions.

## Input

The user provides a **ticker symbol** (e.g., `AAPL`, `TSLA`, `CSU.TO`). If the user gives a company name instead, resolve it to the ticker. If ambiguous, ask.

Optional: the user may specify an output folder. Default: `$DD_OUTPUT_DIR/<TICKER>/` (where `DD_OUTPUT_DIR` defaults to `./due-diligence` if not set).

## Workflow

### Step 1: Identify current management and set the time window

Use a subagent to research:
- Who is the **current CEO** (and CFO if prominent)?
- **When did they take the role?** This sets the lookback window — the analysis covers projections made from the start of their tenure to present.
- If the CEO has been in the role for less than 2 years, also include the **previous CEO's last 3 years** so there's enough data to evaluate.

Report the time window and the reasoning to the user before proceeding. For example: "Analyzing projections from 2014-present because CEO Mark Leonard has led Constellation Software since founding. Focusing on the last 10 years for practical relevance since earlier projections are harder to verify."

For very long-tenured leaders (10+ years), focus on the most recent 10 years to keep the analysis practical while noting the full tenure length.

### Step 2: Research projections (parallel subagents)

Launch **three research subagents** simultaneously. Each must search for specific, verifiable projections — not vague aspirational language. A projection must have a target and an implied or explicit timeline to count.

**Subagent A — Financial projections:**
Search earnings calls, investor days, annual letters, and press releases for management's stated financial targets. Look for:
- Revenue targets or growth rate guidance (e.g., "we expect to reach $10B in revenue by 2025")
- Margin targets (e.g., "targeting 25% operating margins within 3 years")
- EPS or earnings growth guidance
- Capital allocation commitments (e.g., "we'll return $5B to shareholders over the next 3 years")
- Debt reduction or leverage targets
- Same-store sales or organic growth targets

For each projection, capture: **exact quote** (or close paraphrase), **date made**, **source** (earnings call Q2 2022, investor day, annual letter), **target date** (explicit or implied), and **source URL** if available.

**Subagent B — Operational and strategic projections:**
Search for non-financial commitments:
- Store/location openings or closures (e.g., "we plan to open 500 stores this year")
- Product launches or pipeline milestones (e.g., "we'll launch product X by Q3")
- Market entry plans (e.g., "expanding into Southeast Asia in 2024")
- Hiring or headcount targets
- Technology or infrastructure milestones (e.g., "our new factory will be online by mid-2025")
- Acquisition targets (e.g., "we aim to deploy $1B in acquisitions annually")

Same capture format as Subagent A.

**Subagent C — Verify actuals:**
Using SEC filings (10-K, 10-Q via edgartools), yfinance, and web research, compile the **actual results** corresponding to the time periods covered by the projections found by Subagents A and B. This subagent should build a reference table of key financial and operational metrics by year so the synthesis step can compare projections to reality.

### Step 3: Fact-check

Launch a **fact-checker subagent** that cross-references every projection-actual pair. For each:
- Verify the projection was actually made (not misquoted or taken out of context)
- Verify the actual result is correctly stated
- Flag any projections where the comparison is ambiguous (e.g., management changed the metric definition mid-stream, or external events like COVID made the projection moot)
- Drop anything that can't be verified from at least one reliable source

### Step 4: Organize into a projection timeline

Group the verified projection-actual pairs into categories:

1. **Financial Projections** — revenue, margins, earnings, capital returns
2. **Operational Projections** — stores, products, markets, infrastructure
3. **Strategic Projections** — M&A, partnerships, long-term vision

Within each category, present chronologically. For each projection:

| When Projected | What They Said | Target Date | What Actually Happened | Source |
|---|---|---|---|---|

Use plain language. If they said "we'll hit $5B revenue by 2025" and actual 2025 revenue was $4.2B, just state both numbers. No judgment language — no "failed" or "succeeded." Let the numbers speak.

### Step 5: Write the narrative context

Add a brief narrative section (2-3 paragraphs) covering:
- **Management tenure context**: How long in the role, what they inherited, any major external disruptions (COVID, commodity shocks, regulatory changes) during the period
- **Patterns worth noting**: Without judging, flag observable patterns — for example, "management has revised guidance downward in 3 of the last 5 years" or "operational milestones have generally been met within one quarter of the stated target" or "financial projections have consistently been exceeded by 5-15%"
- **What they stopped talking about**: Sometimes the most telling signal is what management projected once and never mentioned again. Note any abandoned targets or quietly dropped initiatives.

Write in the style of Malcolm Gladwell — observational, narrative, drawing attention to interesting patterns without editorializing.

### Step 6: Generate the PDF

Create a professional PDF using Python (reportlab or fpdf2). The PDF should contain:

- **Header banner** (full width, dark background): `{TICKER} MANAGEMENT HONESTY CHECK` with subtitle showing company name, CEO name, tenure period, and report date
- **Management context section**: 2-3 paragraphs from Step 5
- **Financial Projections table**: Full-width table with columns: When Projected | What They Said | Target Date | What Actually Happened | Source
- **Operational Projections table**: Same format
- **Strategic Projections table**: Same format (if applicable — omit if no strategic projections found)
- **Patterns section**: The observational notes from Step 5
- **Footer**: "Compiled [date] by Januarius Holdings Inc." with disclaimer: "This document presents publicly available information for research purposes. No investment recommendation is implied."

PDF requirements:
- Letter size, 0.5" margins
- All source links clickable (blue, underlined)
- All dates bold
- Tables spanning full available width
- No text overlap — adequate row heights for multi-line cells
- 2-3 pages maximum — if there are too many projections, prioritize the most material ones and note how many were omitted

### Step 7: Save and open

Save the PDF to `$DD_OUTPUT_DIR/<TICKER>/<TICKER>_Honesty_Check.pdf` (where `DD_OUTPUT_DIR` defaults to `./due-diligence` if not set), or to a user-specified path. Open it for the user.

## Important Principles

**No scoring, no grades.** The point is to lay out the record and let the reader decide. Avoid words like "failed," "dishonest," "missed," or "beat." Use neutral language: "projected X, actual was Y."

**Only verifiable projections.** Exclude vague statements like "we're excited about our pipeline" or "we see a lot of opportunity." A projection needs a number, a milestone, or a concrete deliverable with a timeline.

**Context matters.** A company that projected 20% growth and delivered 18% during a recession is different from one that projected 20% and delivered 12% in a boom. The narrative section should provide this context without drawing conclusions.

**Cite everything.** Every projection and every actual result needs a source. Earnings call dates, filing dates, press release dates — the reader should be able to verify independently.

## Quality Checklist

Before delivering the PDF:
- [ ] Time window and reasoning were explained to the user
- [ ] At least 5 projection-actual pairs are included
- [ ] Every projection has a date, source, and target
- [ ] Every actual result has a source
- [ ] Fact-checker subagent ran and corrections were applied
- [ ] No judgment language — neutral presentation throughout
- [ ] Narrative section provides context without editorializing
- [ ] All source links are clickable
- [ ] PDF is 2-3 pages, no text overlap
- [ ] Saved to correct $DD_OUTPUT_DIR/<TICKER>/ folder

## Example invocations

```
/dd-1honesty TSLA
/dd-1honesty CSU.TO
management honesty check for AAPL
did NVDA management deliver on their promises?
how accurate is META's guidance?
can I trust AMZN's management projections?
```
