# Wall Street Financial Statement Formatting Conventions

## Typography
- **Font:** Arial 10pt throughout the workbook
- **Bold:** Section headers, subtotals, totals, grand totals
- **Regular:** Individual line items
- **Italic:** Percentage/memo rows (optional)

## Color Coding
- **Black text:** All data (these are historical actuals, not formulas)
- **Light blue fill (`D9E1F2`):** Section header rows
- **White background:** Everything else — gridlines OFF

## Number Formats
| Item Type | Excel Format Code | Example |
|-----------|-------------------|---------|
| Dollar amounts (millions) | `#,##0;(#,##0);"-"` | `4,523` or `(1,200)` or `-` |
| Per-share data | `$#,##0.00;($#,##0.00);"-"` | `$3.45` or `($0.12)` |
| Percentages (1 decimal) | `0.0%;(0.0%);"-"` | `23.5%` |
| Percentages (2 decimal) | `0.00%;(0.00%);"-"` | `3.18%` |
| Multiples | `0.00"x";(0.00"x");"-"` | `1.04x` |
| Shares (millions) | `#,##0.0` | `313.0` |

## Borders
| Location | Border Style |
|----------|--------------|
| Below column headers | Medium bottom |
| Above subtotals | Thin top |
| Above totals | Thin top |
| Grand totals | Thin top + double bottom |
| No other borders | Gridlines OFF |

## Indentation
- **Level 0:** Section headers and totals (left-aligned)
- **Level 2:** Subtotals and line items (indented)
- **Level 3:** Sub-line items

## Layout
- **Column A:** Narrow spacer (~2 chars)
- **Column B:** Row labels (~42-50 chars wide)
- **Columns C+:** One per period, uniform width (~14-16 chars)
- **Column headers:** "FY2025", "FY2024", etc. — centered, bold, medium bottom border

## Sign Convention
- Revenue items: positive
- Expense items (within their section): positive
- Expense subtotals: positive (absolute value)
- Deductions from revenue (provision, tax): shown as negative
- Losses: negative (displayed with parentheses via number format)

## Bank vs. Corporate IS Structure

### Bank / Financial Company
```
Interest Income
  Interest on loans
  Interest on securities
  Total interest income
Interest Expense
  Interest on deposits
  Interest on borrowings
  Total interest expense
Net Interest Income
Other Revenue / Noninterest Income
  Fee income
  Insurance revenue
  Total other revenue
Total Net Revenue
Provision for Credit Losses (negative deduction)
Noninterest Expense
  Compensation
  Other operating expenses
  Total noninterest expense
Pre-Tax Income
Income Tax Expense
Net Income
Per Share Data
```

### Standard Corporate Company
```
Revenue
Cost of Revenue
Gross Profit
Operating Expenses
  R&D
  SG&A
  Total operating expenses
Operating Income
Other Income / (Expense)
Pre-Tax Income
Income Tax Expense
Net Income
Per Share Data
```

## Detection Logic
To determine if a company is a bank/financial: check if the income statement contains "Interest and fees on finance receivables" or "Interest on deposits" or "Net interest income". If yes, use bank format.
