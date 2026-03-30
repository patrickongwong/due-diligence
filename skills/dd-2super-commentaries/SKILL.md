---
name: dd-2super-commentaries
description: Find superinvestors who own a stock and collect all their public commentaries, shareholder letters, videos, interviews, and podcasts about it — creating a structured zettel index under the ticker's Data Room. Use this skill whenever the user says /dd-2super-commentaries, asks to "find superinvestor commentary on [ticker]", "who among the superinvestors owns [ticker]", "collect investor letters about [ticker]", "what have famous investors said about [ticker]", or wants to build a research collection of what prominent fund managers have publicly said about a specific stock. Also trigger when the user asks "which superinvestors hold [ticker]" or "gather investor commentary for DD".
---

# DD Phase 2: Superinvestor Commentaries

This skill identifies which superinvestors from the vault's master list own a given stock, then systematically collects every piece of public commentary they've produced about it — shareholder letters, quarterly commentaries, podcasts, interviews, conference presentations, white papers, and articles. The result is a structured zettel tree under the ticker's Data Room, with one child zettel per superinvestor containing clickable links to all their commentaries.

The point is to let the investor quickly read what the smartest money in the room thinks about a stock before forming their own thesis.

## Prerequisites

- The ticker must already have a zettel and Data Room under `dd Due Diligence/`. If not, tell the user to run `/dd-2dataroom` first.
- The vault must contain `sup1 List Of Dataroma Superinvestors.md` — this is the master list of superinvestors to cross-reference.

## Execution

### Step 1: Locate the existing prospect and Data Room

Search `dd Due Diligence/` for the ticker's folder (e.g., `dd1 CSU`, `dd4 ALLY`).

- Extract `ZETTEL_PREFIX` (e.g., `dd1`), `TICKER` (e.g., `CSU`), and `PROSPECT_DIR`
- Read the Data Room zettel (typically `{ZETTEL_PREFIX}b {TICKER} Data Room.md`) to see existing children
- Determine the next available child number (e.g., if dd1b5 is the last child, the new parent will be dd1b6)

Set these variables:
- `DATAROOM_ID` = e.g., `dd1b`
- `COMMENTARY_ID` = e.g., `dd1b6` (next available child under the Data Room)
- `TICKER` = e.g., `CSU`

### Step 2: Read the superinvestor list

Read `sup1 List Of Dataroma Superinvestors.md` and extract the full list of superinvestor names and fund names.

### Step 3: Find which superinvestors own the stock

Dispatch a subagent to identify owners:

```
You are researching which superinvestors own {TICKER} ({COMPANY_NAME}).

Why: We need to know exactly which investors from a master list hold this stock, so we can then collect their public commentary about it.

Step 1: Check Dataroma for the stock. For US-listed stocks, search directly by ticker. For non-US stocks (e.g., Canadian .TO tickers), search by the US OTC equivalent ticker (e.g., CSU.TO → CNSWF). Try fetching: https://www.dataroma.com/m/stock.php?sym={OTC_TICKER}

Step 2: Cross-reference the Dataroma results with this master list of superinvestors:
{FULL_SUPERINVESTOR_LIST}

Step 3: Because Dataroma only tracks US 13F filers, also do broader web research to find well-known holders who may hold the stock through non-US vehicles (e.g., UK/Canadian/European funds that don't file 13F). Search for "{TICKER} superinvestor holders", "{COMPANY_NAME} famous investors", and similar queries. Only include investors that appear on the master list above.

Return a clean list of confirmed or strongly evidenced holders from the master list, with their fund names and any position details you found.
```

### Step 4: Research commentaries in parallel

For each confirmed superinvestor (or batch of 5-8), dispatch research subagents in parallel. Each subagent searches for all public commentary about the stock from their assigned investors.

The subagent prompt should follow this pattern:

```
You are collecting all public commentaries about {TICKER} ({COMPANY_NAME}) from the following investors:
{LIST_OF_INVESTORS_FOR_THIS_BATCH}

Why: We're building a comprehensive research library of what these investors have publicly said about this stock — every shareholder letter mention, every podcast appearance, every interview or article. This will help an investor understand the bull case from the smartest money's perspective.

For EACH investor, search thoroughly across these source types:
1. **Shareholder/quarterly letters** — Check the fund's website, Seeking Alpha, GuruFocus, MOI Global, and PDF archives
2. **Podcasts & interviews** — Check YouTube, The Investor's Podcast, Spotify, Apple Podcasts, value investing podcast networks
3. **Conference presentations** — Check VALUEx, Ira Sohn, MOI Global, fund annual meetings
4. **Articles & white papers** — Check fund websites, Substack, personal blogs
5. **Third-party coverage** — Check GuruFocus, Yahoo Finance, Acquirer's Multiple for summaries of their commentary

For each commentary found, provide:
- Title or description
- Date (as specific as possible)
- Direct URL (must be clickable)
- Brief note on what aspect of {TICKER} they discuss

Only include commentaries where the investor substantively discusses {TICKER} — not just portfolio tables listing it as a holding.

If an investor is a confirmed holder but you find NO public commentary about {TICKER}, note that explicitly.
```

### Step 5: Fact-check with a validation subagent

Per vault conventions, dispatch a validation subagent to verify the research:

```
You are a fact-checker validating superinvestor commentary links for {TICKER}.

Why: Research subagents sometimes hallucinate URLs or misattribute commentary. Your job is to verify that the links are real and the descriptions are accurate.

For each URL provided, attempt to fetch or verify it exists. Flag any that:
- Return 404 or are clearly broken
- Are behind paywalls that make the content inaccessible
- Misattribute commentary (e.g., the letter doesn't actually mention {TICKER})
- Confuse {COMPANY_NAME} with a similarly-named company (e.g., Constellation Software vs. Constellation Energy)

Remove anything that fails verification. If anything is removed, note what was removed and why.
```

### Step 6: Assemble the zettels

Create the zettel files. Every zettel uses the standard frontmatter:

```yaml
---
aliases: []
tags:
---
```

**Parent zettel** (`{COMMENTARY_ID} {TICKER} Superinvestor Commentary.md`):

```markdown
---
aliases: []
tags:
---
- [[{COMMENTARY_ID}a {Investor1 Name}]]
- [[{COMMENTARY_ID}b {Investor2 Name}]]
- [[{COMMENTARY_ID}c {Investor3 Name}]]
...

Note: Dataroma tracks only US 13F filers. Some superinvestors may hold {TICKER} through non-US vehicles not captured in 13F disclosures. The investors above are those from [[sup1 List Of Dataroma Superinvestors]] confirmed to own or have substantively commented on {COMPANY_NAME}.
```

Use Luhman ID lettering for children: a, b, c, ... z, then aa, ab, etc.

**Each child zettel** (`{COMMENTARY_ID}a {Investor Name - Fund Name}.md`):

```markdown
---
aliases: []
tags:
---
**Position:** {Position details — shares held, % of portfolio, when first purchased, any trimming history. If no confirmed equity position, note that clearly.}

## Commentaries

### {Category 1 — e.g., "Dedicated Letters" or "Quarterly Commentaries"}
- [{Title} ({Date})]({URL}) — {Brief description of what they discuss about TICKER.}
- ...

### {Category 2 — e.g., "Podcasts & Interviews"}
- ...

### Archive
- [{Fund name} letters archive]({URL})
```

Organize commentaries into logical categories (letters, podcasts, articles, etc.) and sort within each category by date descending. Include archive links at the bottom where the user can find future commentaries.

All zettel files go in the prospect folder (e.g., `dd Due Diligence/dd1 CSU/`), NOT inside any subfolder.

### Step 7: Update the Data Room zettel

Add a wikilink to the new Superinvestor Commentary zettel in the Data Room parent:

```markdown
- [[{COMMENTARY_ID} {TICKER} Superinvestor Commentary]]
```

### Step 8: Report to the user

Summarize what was created:

```
Superinvestor Commentary complete for {TICKER}:

| Investor | Position | Commentaries Found |
|----------|----------|--------------------|
| {Name}   | {Brief}  | {count}            |
| ...      | ...      | ...                |

All zettels saved to: dd Due Diligence/{PROSPECT_DIR}/
```

Do NOT automatically open any files — the user will check them in the folder.

## Notes

- The 13F blind spot is real and important. Many quality-focused global investors (UK, Canadian, European funds) hold stocks on non-US exchanges without any SEC filing obligation. The broader web research step in Step 3 partially addresses this, but some holders will inevitably be missed.
- Some superinvestors write extensively about their holdings (e.g., Akre, Giverny, Sequoia) while others barely mention individual positions. A zettel with "no public commentary found" is still valuable — it confirms the investor holds the stock even if they haven't discussed it publicly.
- Watch out for company name confusion. "Constellation Software" vs. "Constellation Energy" and "Constellation Brands" are three completely different companies that share a word. The fact-checking subagent should catch these, but be vigilant.
- Private LP letters are not publicly accessible. Only include links to freely available or commonly archived materials.
