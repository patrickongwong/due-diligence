---
name: dd-2dataroom
description: Build a Due Diligence Dataroom for a stock ticker — indexes all SEC filings, shareholder letters, investor presentations, and earnings transcripts as zettels. Use when the user asks to build a dataroom, gather filings, or collect documents for DD.
---

# DD Phase 2: Dataroom

The Dataroom is where all source documents for due diligence live — annual reports, quarterly filings, proxy statements, shareholder letters, and earnings transcripts. This skill creates a structured index of clickable links to every important document, organized as child zettels under a Dataroom parent.

The goal is simple: after running this skill, the investor has one place to find every document they need to read before making an investment decision.

## Prerequisites

The ticker must already have a zettel under `dd Due Diligence/`. If it doesn't, tell the user to run `/dd-zettelfy` first or manually create the prospect folder.

## Execution

### Step 1: Locate the existing prospect

Search the `dd Due Diligence/` folder for a directory matching the ticker. The naming convention is `dd{N} TICKER` (e.g., `dd4 ALLY`, `dd1 CSU`).

- Extract the zettel prefix (e.g., `dd4`) and the ticker (e.g., `ALLY`)
- Read the root zettel (e.g., `dd4 ALLY.md`) to see what child zettels already exist
- If a Dataroom zettel already exists (e.g., `dd4b ALLY Dataroom`), inform the user and ask whether to overwrite or skip

### Step 2: Determine the Dataroom zettel ID

Look at the existing children of the root zettel to find the next available letter. The convention is:

- `dd{N}a` = Background (from Phase 1)
- `dd{N}b` = Dataroom (this skill)

If `b` is already taken by something other than a Dataroom, use the next available letter. But in the standard flow, the Dataroom gets `b`.

Set these variables for the rest of the process:
- `ZETTEL_PREFIX` = e.g., `dd4`
- `DATAROOM_ID` = e.g., `dd4b`
- `TICKER` = e.g., `ALLY`
- `COMPANY_NAME` = full company name (look it up via edgartools or web search)
- `PROSPECT_DIR` = e.g., `dd Due Diligence/dd4 ALLY`

### Step 3: Create the Dataroom folder

Create the physical folder for storing any downloaded documents later:

```
dd Due Diligence/dd{N} TICKER/dd{N} TICKER Dataroom/
```

This folder already exists for some prospects. If it does, skip creation.

### Step 4: Gather all filing links

This is the core of the skill. Dispatch **five subagents in parallel** — one for each document category. Each subagent gathers links and returns a markdown table.

All five subagents should use the `/edgartools` skill for US-listed companies to pull filing data from SEC EDGAR. For non-US companies or documents not on EDGAR (shareholder letters, earnings transcripts), fall back to web search targeting the company's investor relations website.

#### Subagent 1: Annual Reports (10-K / 20-F)

```
You are gathering Annual Report links for {TICKER} ({COMPANY_NAME}).

Why: This is part of building a Due Diligence Dataroom — we need every annual filing to study the company's long-term trajectory.

Use the /edgartools skill. Get ALL 10-K filings (or 20-F if the company is a foreign private issuer). For each filing, extract:
- Fiscal year
- Filing date
- Direct link to the filing (use filing.homepage_url for the SEC index page)

Example edgartools approach:
  from edgar import Company
  company = Company("{TICKER}")
  filings_10k = company.get_filings(form="10-K")  # or form="20-F"
  # Iterate through ALL filings, not just latest

Return a markdown table with columns: | Fiscal Year | Filing Date | Link |
Sort by fiscal year descending (most recent first).

If the company is not US-listed (e.g., Canadian .TO/.V suffix), instead search the company's investor relations website for annual reports and provide direct links.
```

#### Subagent 2: Quarterly Reports (10-Q / 6-K)

```
You are gathering Quarterly Report links for {TICKER} ({COMPANY_NAME}).

Why: Quarterly filings show the company's recent trajectory and are essential reading for due diligence.

Use the /edgartools skill. For domestic US filers, get ALL 10-Q filings. For foreign private issuers (companies that file 20-F instead of 10-K), get 6-K filings instead — but ONLY the earnings-related 6-Ks, not every 6-K. Foreign issuers file 6-Ks for many purposes (share repurchases, leadership changes, regulatory notices); filter to only those that contain quarterly or interim financial results by checking the filing description or exhibit content for keywords like "earnings", "financial results", "operating results", or "interim report".

For each filing, extract:
- Period (e.g., Q1 2024)
- Filing date
- Direct link to the filing (use filing.homepage_url)

Example edgartools approach:
  from edgar import Company
  company = Company("{TICKER}")
  filings_10q = company.get_filings(form="10-Q")  # or form="6-K" for foreign issuers
  # Iterate through ALL filings
  # For 6-K: filter to earnings-related filings only

Return a markdown table with columns: | Period | Filing Date | Link |
Sort by period descending (most recent first).

If the company is not US-listed, search the investor relations website for quarterly reports.
```

#### Subagent 3: Proxy Statements (DEF 14A)

```
You are gathering Proxy Statement links for {TICKER} ({COMPANY_NAME}).

Why: Proxy statements reveal executive compensation, board composition, related-party transactions, and governance — critical for assessing management alignment with shareholders.

Use the /edgartools skill. Get ALL DEF 14A filings. For each filing, extract:
- Year
- Filing date
- Direct link to the filing (use filing.homepage_url)

Example edgartools approach:
  from edgar import Company
  company = Company("{TICKER}")
  filings_proxy = company.get_filings(form="DEF 14A")
  # Iterate through ALL filings

Return a markdown table with columns: | Year | Filing Date | Link |
Sort by year descending.

**Foreign private issuers:** Companies that file 20-F (instead of 10-K) typically do not file DEF 14A proxy statements with the SEC. If no DEF 14A filings are found, note this at the top of the zettel: "As a foreign private issuer, {COMPANY_NAME} does not file DEF 14A proxy statements with the SEC." Then search the company's investor relations website for equivalent governance documents — these are often called "Notice of Annual General Meeting", "AGM Circular", or "Corporate Governance Report" — and list whatever you find.

If the company is not US-listed, search for "management information circular" or "proxy circular" on the investor relations website.
```

#### Subagent 4: Shareholder Letters & Investor Presentations

```
You are gathering Shareholder Letters and Investor Presentations for {TICKER} ({COMPANY_NAME}).

Why: Shareholder letters and investor presentations reveal management's own framing of the business — their priorities, how they think about capital allocation, and what they're proud of vs. what they gloss over.

Search for these documents using web search. Target:
1. The company's investor relations page (usually at {company_website}/investors or /investor-relations)
2. SEC EDGAR for any 8-K filings tagged with investor presentations (Item 7.01 or 8.01)
3. Annual report letters to shareholders (often embedded in the 10-K but sometimes published separately)

For EDGAR 8-K filings with presentations, use edgartools:
  from edgar import Company
  company = Company("{TICKER}")
  filings_8k = company.get_filings(form="8-K")
  # Filter for those with investor presentation exhibits

Return a markdown table with columns: | Date | Title | Link |
Sort by date descending.

Include whatever you can find — annual shareholder letters, investor day presentations, conference presentations, capital markets day slides. Cast a wide net.
```

#### Subagent 5: Earnings Call Transcripts

```
You are gathering Earnings Call Transcript links for {TICKER} ({COMPANY_NAME}).

Why: Earnings calls are where management faces analyst questions — the Q&A sections are especially valuable for understanding what the market is focused on and how management handles tough questions.

Search the web for earnings call transcripts. The links must point to pages where the full transcript is freely readable — no paywalls, no login walls, no "subscribe to read more" truncation. Before including a link, verify the source is accessible by actually fetching the page content to confirm the transcript text is there.

**Preferred sources (free, full-text):**
- The Motley Fool (fool.com/earnings/call-transcripts/) — free, full transcripts
- The company's own investor relations page (some companies post PDFs or HTML transcripts)
- Company-hosted PDF transcripts on Q4 CDN or similar hosting
- BamSEC (bamsec.com) — free access to SEC filings and some transcripts
- AlphaStreet (alphastreet.com) — free earnings call transcripts

**Avoid or use only as last resort:**
- Seeking Alpha — most transcripts are paywalled; only include if you can confirm the specific URL is freely accessible
- Any source that requires a paid subscription to read the full text

Return a markdown table with columns: | Quarter | Date | Source | Link |
Sort by quarter descending (most recent first).

Try to find at least the last 3-5 years of quarterly earnings calls. More is better. At the bottom, include links to aggregator pages where the user can find additional transcripts (e.g., the company's IR page, BamSEC company page).
```

### Step 5: Assemble the Dataroom zettels

Once all five subagents return, create the zettel files. Every zettel uses this frontmatter:

```yaml
---
aliases: []
tags:
---
```

**Dataroom parent zettel** (`{DATAROOM_ID} {TICKER} Dataroom.md`):

```markdown
---
aliases: []
tags:
---
- [[{DATAROOM_ID}1 {TICKER} Annual Reports]]
- [[{DATAROOM_ID}2 {TICKER} Quarterly Reports]]
- [[{DATAROOM_ID}3 {TICKER} Proxy Statements]]
- [[{DATAROOM_ID}4 {TICKER} Shareholder Letters]]
- [[{DATAROOM_ID}5 {TICKER} Earnings Transcripts]]
```

**Each child zettel** (`{DATAROOM_ID}1 {TICKER} Annual Reports.md`, etc.):

```markdown
---
aliases: []
tags:
---
{Brief one-line description of what these documents are and where they're sourced from.}

| Column1 | Column2 | Link |
|---------|---------|------|
| ...     | ...     | ...  |
```

All zettel files go in the prospect folder (e.g., `dd Due Diligence/dd4 ALLY/`), alongside the root zettel — NOT inside the Dataroom subfolder. This matches the existing convention where zettels live at the prospect folder level and only raw files go in subfolders.

### Step 6: Update the parent zettel

Add a wikilink to the Dataroom in the root zettel (e.g., `dd4 ALLY.md`). Place it after any existing children:

```markdown
- [[{DATAROOM_ID} {TICKER} Dataroom]]
```

### Step 7: Report to the user

Summarize what was created:

```
Dataroom complete for {TICKER}:
  [done] Annual Reports — {count} filings found
  [done] Quarterly Reports — {count} filings found
  [done] Proxy Statements — {count} filings found
  [done] Shareholder Letters — {count} documents found
  [done] Earnings Transcripts — {count} transcripts found

All zettels saved to: dd Due Diligence/dd{N} {TICKER}/
```

Do NOT automatically open any files — the user will check them in the folder.

## Notes

- For US-listed companies, edgartools should be the primary source for SEC filings (10-K, 10-Q, DEF 14A). It gives clean, reliable EDGAR links.
- For Canadian stocks (`.TO`, `.V` suffix), scrape financials from the company's IR website instead of Yahoo Finance or EDGAR.
- Shareholder letters and earnings transcripts typically require web search since they're not always structured on EDGAR.
- If edgartools fails or the company has no EDGAR filings, fall back entirely to web search against the company's investor relations website.
- The `filing.homepage_url` property gives the SEC EDGAR index page for a filing, which is the most stable link format.
- When a subagent encounters errors, it should return whatever it found with a note about what failed — partial results are better than no results.
