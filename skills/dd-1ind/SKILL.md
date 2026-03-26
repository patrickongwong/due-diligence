---
name: dd-1ind
description: Generate an Industry Analysis One-Pager PDF for any stock ticker — covers market share trends, key competitors and their performance, "silver bullet" competitive threat analysis, and industry ecosystem (suppliers, customers, regulations) with clickable source links. Use this skill whenever the user says /dd-1ind, asks for "industry analysis", "industry overview", "competitive landscape for [ticker]", "market share analysis", "who are the competitors of [ticker]", "industry report", or wants to understand the competitive dynamics and industry structure around a stock. Also trigger when the user asks "what industry is [ticker] in", "how does [ticker] compare to competitors", or "show me the industry for [ticker]". Works for any publicly traded stock.
---

# Industry Analysis One-Pager

Produce a concise (3-5 page) PDF that gives an investor a rapid but rigorous understanding of the industry a stock operates in — what the industry actually is, how it came to exist, who the players are (public AND private), how the competitive dynamics work, and what structural forces shape the industry.

The goal is to answer: "If I'm investing in this company, what do I need to know about its industry?"

## Input

The user provides a **ticker symbol** (e.g., `AAPL`, `TSLA`, `2330.TW`). If the user gives a company name instead, resolve it to the ticker. If ambiguous, ask.

Optional: the user may specify an output folder. Default: `$DD_OUTPUT_DIR/<TICKER>/` (where DD_OUTPUT_DIR defaults to `./due-diligence`).

## Workflow

### Step 1: Identify the company and its industry

Use Python's `yfinance` library to get:
- Company name, sector, industry classification
- Current price, market cap
- Revenue (TTM)

This tells you which industry to research. If the company operates across multiple segments (e.g., Amazon = e-commerce + cloud + advertising), focus on the **primary revenue segment** but note the others.

### Step 2: Research in parallel (6 subagents)

Launch six research subagents simultaneously. Each must include the company name, ticker, AND industry in search queries. Include "Why" context in each subagent prompt.

**Subagent E — Industry Explanation & History:**
Write a detailed explanation of what this industry actually is — assume the reader knows nothing. Then write a narrative history of the industry with a timeline of key events. Cover:
- What the industry is, in detail, with specific examples of products/services
- Why this industry exists (what problem does it solve?)
- How it differs from adjacent industries
- Origins and evolution of the industry (key eras, inflection points)
- Timeline of 10-15 milestone events with dates
- How the competitive model works (do companies compete for customers? acquisitions? something else?)

Write in Malcolm Gladwell style. Every claim needs a source URL.

**Subagent F — Private/Non-Public Competitors:**
Research major NON-PUBLIC competitors — private equity firms, private companies, and any other entities that compete in this industry but are not publicly listed. These are often the most important competitors and should not be overlooked. For each, find: estimated AUM or revenue, number of acquisitions/portfolio companies, strategy, and how they compete with the target company. Write narrative profiles with source URLs.

**Subagent A — Market Share & Competitors:**
Research the market share of the target company and its top 5-8 competitors (public AND private). Search for:
- Current market share estimates from analyst reports, industry publications, Statista, IBISWorld
- Historical market share data (at least 3-5 years of trends if available)
- Revenue or unit-based share depending on what's standard for the industry
- Which competitors are gaining/losing share and why

For each data point, capture: source name, date, the specific figures, and source URL.

Return structured data:
```json
{
  "industry_name": "...",
  "market_size": "$XXB (year)",
  "market_size_source": {"label": "...", "url": "..."},
  "players": [
    {
      "company": "...",
      "ticker": "...",
      "market_share_current": "XX%",
      "market_share_history": [
        {"year": "2021", "share": "XX%"},
        {"year": "2022", "share": "XX%"},
        ...
      ],
      "trend": "gaining/losing/stable",
      "revenue_ttm": "$XXB"
    }
  ],
  "sources": [{"label": "...", "url": "..."}]
}
```

**Subagent B — Competitor Performance & Who's Winning:**
For each of the top 5-8 competitors, research:
- Recent revenue growth (1-year, 3-year CAGR)
- Margin trends (gross, operating)
- Strategic moves (acquisitions, product launches, geographic expansion)
- What's working for the winners and what's failing for the losers
- Any recent analyst upgrades/downgrades with reasoning

Return a narrative assessment for each competitor with source URLs.

**Subagent C — Silver Bullet Analysis:**
This is the most creative section. Research competitive dynamics to answer: "If each major player in this industry had one silver bullet — one competitor they could eliminate — who would they aim it at, and why?"

Think about it from each player's perspective:
- Who is eating into their market share?
- Who is the most disruptive threat?
- Who competes most directly on their core product?
- Are there asymmetric threats (a smaller player threatening a larger one)?

Use web searches for competitive dynamics, analyst commentary on competitive threats, and management commentary from earnings calls about competitors. The answer should reveal who the real competitive tensions are between — not just who is biggest.

Return structured analysis with reasoning and sources for each "bullet" relationship.

**Subagent D — Industry Ecosystem:**
Research the broader industry structure:
- **Key Suppliers** (top 3-5): Who supplies critical inputs? Is there supplier concentration risk? Any supply chain disruptions?
- **Key Customers** (top 3-5 customer segments or specific customers if B2B): Who buys? Customer concentration risk?
- **Key Regulations**: What regulations shape the industry? Any pending regulatory changes? Recent enforcement actions?
- **Industry Tailwinds/Headwinds**: What macro forces are helping or hurting the industry? (Technology shifts, demographic changes, policy changes)

Return structured data with source URLs for each claim.

### Step 3: Fact-check

Launch a **fact-checker subagent** that takes all claims from Steps 2A-D and verifies each one against web sources. For each claim, it returns VERIFIED, PARTIALLY CORRECT, or UNVERIFIED with the correction. Drop UNVERIFIED claims. Amend PARTIALLY CORRECT claims.

After fact-checking, if any section had significant removals, launch a **rewrite subagent** that rewrites the affected section in the original Gladwell/Feynman narrative style so the flow reads naturally despite the cuts.

### Step 4: Synthesize and structure

Organize the verified findings into the PDF structure below. Write in the style of Malcolm Gladwell — vivid, narrative-driven, making dry industry data come alive — but keep it concise. Every factual claim must have a bold date and a source.

### Step 5: Generate the PDF

Run the bundled PDF generator script at `$CLAUDE_PLUGIN_ROOT/skills/dd-1ind/scripts/generate_industry_pdf.py`. Pass it a JSON file with all the structured data.

**CRITICAL: Do NOT truncate or shorten any research data when assembling the JSON.** Pass the FULL text of `industry_explanation`, `history_narrative`, and all `timeline` entries from the research subagent into the JSON file. The PDF script handles layout and pagination automatically — there is no need to cut content to fit a page target. Also ensure all text values in the JSON are plain text (no HTML tags like `<b>`) — the PDF script handles formatting. The `industry_explanation` and `history_narrative` fields in particular can be thousands of characters long; this is expected and correct.

The script produces a professional PDF with:

1. **Dark header banner**: `{TICKER} INDUSTRY ANALYSIS` with company name, industry, date, price, market cap
2. **Industry Overview strip**: Total market size, growth rate, number of major players
3. **What Is This Industry?** section: Detailed explanation of what the industry is, with specific examples. Written for a reader who knows nothing about this space.
4. **Industry History & Timeline** section: Narrative history of the industry with a timeline table of 10-15 key milestone events (year, event, significance).
5. **Market Share section** (includes BOTH public and private competitors): Table showing each player's current share plus a text description of how shares have shifted over 3-5 years. Include a simple ASCII-style bar for each player's share so the visual is immediate.
4. **Who's Winning section**: A narrative paragraph per competitor (top 5) with bold performance metrics and what's driving their trajectory. Written in engaging Gladwell style.
5. **Silver Bullet section**: A table or structured list: "If [Player A] had a silver bullet, they'd aim it at [Player B] because..." — one row per major player. This section should read like a strategic thriller.
6. **Industry Ecosystem section**: Three sub-sections with compact tables/lists:
   - Key Suppliers (name, what they supply, concentration risk)
   - Key Customers (segment/name, % of industry revenue, trends)
   - Key Regulations (regulation name, impact, status)
7. **Tailwinds & Headwinds**: Brief bullet points of macro forces
8. **Footer**: "Compiled [date] by Januarius Holdings Inc." with disclaimer

The PDF must have:
- All source links clickable (blue, underlined)
- All dates bold
- Letter size, 0.5" margins
- Clean, professional layout — no text overlap
- Let the content determine the length — typically 5-10 pages. Do NOT truncate research to fit a page target

### Step 6: Save and open

Save the PDF to `$DD_OUTPUT_DIR/<TICKER>/<TICKER>_Industry_Analysis.pdf` (or user-specified path). Open it for the user.

## Writing Style

Write in the style of Malcolm Gladwell — make industry data tell a story. Every section should have a narrative thread, not just bullet points of facts. Data-heavy where it matters, narrative where it helps comprehension. Let the story breathe — if the industry history is rich, give it the space it deserves.

## Quality Checklist

Before delivering the PDF, verify:
- [ ] Market share data has at least 3 years of history where available
- [ ] At least 5 competitors are profiled
- [ ] Every factual claim has a clickable source link
- [ ] Silver bullet section covers at least 4 major players
- [ ] Suppliers, customers, and regulations sections are all present
- [ ] Fact-checker subagent ran and corrections were applied
- [ ] No text overlap in the PDF
- [ ] Industry explanation and history narrative are NOT truncated — full research content is in the JSON
- [ ] All timeline entries from research are included (not filtered to fit a page limit)

## Example invocations

```
/dd-1ind NVDA
/dd-1ind TSLA
industry analysis for AAPL
who are MSFT's competitors?
show me the competitive landscape for META
```
