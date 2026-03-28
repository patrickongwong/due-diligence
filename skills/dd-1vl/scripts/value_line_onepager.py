#!/usr/bin/env python3
"""Value Line-style one-pager PDF generator."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '_shared'))
from auto_install import ensure_installed
ensure_installed('edgartools', 'yfinance', 'matplotlib', 'weasyprint')

import base64
import io
from datetime import datetime, date
from dataclasses import dataclass, field


@dataclass
class AnnualData:
    year: int
    revenue: float | None = None          # total revenue in millions
    net_income: float | None = None       # net income in millions
    eps: float | None = None              # diluted EPS
    dividends_per_share: float | None = None
    book_value_per_share: float | None = None
    cash_flow_per_share: float | None = None  # operating CF / shares
    shares_outstanding: float | None = None   # diluted, in millions
    total_debt: float | None = None       # in millions
    long_term_debt: float | None = None   # in millions
    interest_expense: float | None = None # in millions
    current_assets: float | None = None   # in millions
    current_liabilities: float | None = None  # in millions
    cash: float | None = None             # in millions
    receivables: float | None = None      # in millions
    inventory: float | None = None        # in millions
    net_margin: float | None = None       # percentage
    roe: float | None = None              # percentage
    revenue_per_share: float | None = None
    operating_income: float | None = None  # EBIT, in millions
    operating_cashflow: float | None = None  # in millions
    income_tax_expense: float | None = None  # in millions
    pretax_income: float | None = None       # in millions
    roic: float | None = None                # percentage
    debt_to_equity: float | None = None      # ratio (e.g. 2.3)
    debt_to_ebitda: float | None = None      # ratio
    net_debt_to_ebitda: float | None = None  # ratio
    ebitda: float | None = None              # in millions
    depreciation: float | None = None        # in millions


@dataclass
class SegmentData:
    year: int
    product_segments: dict[str, float] = field(default_factory=dict)  # name -> revenue $M
    geo_segments: dict[str, float] = field(default_factory=dict)      # name -> revenue $M


@dataclass
class QuarterlyData:
    year: int
    quarter: int  # 1-4
    revenue: float | None = None  # in millions
    eps: float | None = None


@dataclass
class MarketData:
    price: float | None = None
    pe_ratio: float | None = None
    dividend_yield: float | None = None
    beta: float | None = None
    market_cap: float | None = None       # in billions
    week_52_high: float | None = None
    week_52_low: float | None = None
    company_name: str = ""
    exchange: str = ""
    sector: str = ""
    industry: str = ""
    description: str = ""


@dataclass
class StockData:
    ticker: str
    market: MarketData = field(default_factory=MarketData)
    annual: list[AnnualData] = field(default_factory=list)
    quarterly: list[QuarterlyData] = field(default_factory=list)
    segments: list[SegmentData] = field(default_factory=list)
    price_history: object = None  # pandas DataFrame


def fetch_edgar_annual(ticker: str) -> list[AnnualData]:
    """Fetch up to 15 years of annual financial data from SEC EDGAR.

    Uses the edgartools library to pull income statement, balance sheet,
    and cash flow statement data from 10-K filings. Falls back to 20-F
    filings for foreign private issuers (e.g., PDD, BABA, TSM).
    """
    from edgar import Company, set_identity
    from edgar.financials import Financials
    import pandas as pd

    identity = os.environ.get("EDGAR_IDENTITY", "Value Line Skill user@example.com")
    set_identity(identity)

    current_year = datetime.now().year
    min_year = current_year - 15

    try:
        company = Company(ticker)
        filings_10k = company.get_filings(form="10-K")
        if not filings_10k or len(filings_10k) == 0:
            print(f"[EDGAR] No 10-K filings found for {ticker}, trying 20-F...")
            filings_10k = company.get_filings(form="20-F")
    except Exception as e:
        print(f"[EDGAR] Could not find company '{ticker}': {e}")
        return []

    if not filings_10k or len(filings_10k) == 0:
        print(f"[EDGAR] No 10-K or 20-F filings found for {ticker}")
        return []

    # Collect data from multiple filings to cover up to 15 years.
    # Each 10-K typically has 3 years of income/CF and 2 years of BS data.
    # We process ~6 filings to get ~15 years, taking the earliest filing's
    # value when there's overlap (later filings may have restated numbers,
    # but the most-recent filing's version is preferred).
    year_data: dict[int, AnnualData] = {}

    # Metadata columns that are NOT date columns
    META_COLS = {
        "concept", "label", "standard_concept", "level", "abstract",
        "dimension", "is_breakdown", "dimension_axis", "dimension_member",
        "dimension_member_label", "dimension_label", "balance", "weight",
        "preferred_sign", "parent_concept", "parent_abstract_concept",
    }

    def get_date_columns(df: pd.DataFrame) -> list[str]:
        """Return column names that look like fiscal-year-end dates."""
        return [c for c in df.columns if c not in META_COLS and c[:2] == "20"]

    def non_dimensional(df: pd.DataFrame) -> pd.DataFrame:
        """Keep only rows that are not segment/dimension breakdowns."""
        mask = (df["dimension"] == False) | (df["dimension"].isna())
        return df[mask].copy()

    def safe_get(df: pd.DataFrame, col: str, *, concept: str | None = None,
                 standard: str | None = None, concepts: list[str] | None = None,
                 standards: list[str] | None = None) -> float | None:
        """Extract a single numeric value from a dataframe.

        Tries standard_concept first, then concept. Returns None if not found.
        Handles the case where multiple rows match by taking the first non-NaN
        row that is not an abstract/header row.
        """
        candidates = []

        # Build list of (priority, standard_or_concept_name) to try
        all_standards = []
        if standard:
            all_standards.append(standard)
        if standards:
            all_standards.extend(standards)

        all_concepts = []
        if concept:
            all_concepts.append(concept)
        if concepts:
            all_concepts.extend(concepts)

        # Try standard_concept matches first (higher priority)
        for sc in all_standards:
            matches = df[df["standard_concept"] == sc]
            for _, row in matches.iterrows():
                if row.get("abstract", False):
                    continue
                val = row.get(col)
                if val is not None and pd.notna(val):
                    return float(val)

        # Then try concept matches
        for cn in all_concepts:
            if cn.startswith("us-gaap_"):
                matches = df[df["concept"] == cn]
            else:
                matches = df[df["concept"].str.contains(cn, na=False, regex=False)]
            for _, row in matches.iterrows():
                if row.get("abstract", False):
                    continue
                val = row.get(col)
                if val is not None and pd.notna(val):
                    return float(val)

        return None

    def to_millions(val: float | None) -> float | None:
        """Convert raw dollar value to millions."""
        if val is None:
            return None
        return round(val / 1e6, 2)

    # Process up to 16 filings (covers ~15+ years with overlap)
    num_filings = min(len(filings_10k), 16)

    for i in range(num_filings):
        try:
            filing = filings_10k[i]
            xbrl_data = filing.xbrl()
            if xbrl_data is None:
                continue

            fins = Financials(xbrl_data)

            # Get statements - these are methods that return Statement objects
            try:
                inc_stmt = fins.income_statement()
                inc_df = non_dimensional(inc_stmt.to_dataframe())
            except Exception:
                inc_df = pd.DataFrame()

            try:
                bs_stmt = fins.balance_sheet()
                bs_df = non_dimensional(bs_stmt.to_dataframe())
            except Exception:
                bs_df = pd.DataFrame()

            try:
                cf_stmt = fins.cash_flow_statement()
                cf_df = non_dimensional(cf_stmt.to_dataframe())
            except Exception:
                cf_df = pd.DataFrame()

            # Determine which date columns (fiscal years) are available
            all_date_cols = set()
            for df in [inc_df, bs_df, cf_df]:
                if not df.empty:
                    all_date_cols.update(get_date_columns(df))

            for date_col in sorted(all_date_cols):
                # Parse the year from the date column (e.g. "2024-09-28" -> 2024)
                try:
                    fiscal_year = int(date_col[:4])
                except (ValueError, IndexError):
                    continue

                if fiscal_year < min_year:
                    continue

                # If we already have data for this year, we may still need to
                # fill in missing fields (e.g., BS data that wasn't in the
                # newer filing's date range). Use existing object or create new.
                is_existing = fiscal_year in year_data
                ad = year_data.get(fiscal_year, AnnualData(year=fiscal_year))
                equity_raw = None
                opcf_raw = None

                # === INCOME STATEMENT ===
                # Fill fields that are still None (prefer newer filing data).
                # Newer filings may include phantom date columns with all-NaN values,
                # so we use field-level None checks (same pattern as balance sheet).
                if not inc_df.empty and date_col in inc_df.columns:
                    if ad.revenue is None:
                        revenue_raw = safe_get(inc_df, date_col,
                                               standards=["Revenue"],
                                               concepts=["us-gaap_Revenues",
                                                         "us-gaap_RevenueFromContractWithCustomerExcludingAssessedTax"])
                        ad.revenue = to_millions(revenue_raw)

                    if ad.net_income is None:
                        net_income_raw = safe_get(inc_df, date_col,
                                                  standards=["NetIncome", "NetIncomeToCommonShareholders"],
                                                  concepts=["us-gaap_NetIncomeLoss"])
                        ad.net_income = to_millions(net_income_raw)

                    if ad.eps is None:
                        ad.eps = safe_get(inc_df, date_col,
                                          concepts=["us-gaap_EarningsPerShareDiluted"])

                    if ad.interest_expense is None:
                        interest_raw = safe_get(inc_df, date_col,
                                                standards=["InterestExpense"],
                                                concepts=["us-gaap_InterestExpense",
                                                          "us-gaap_InterestExpenseNonoperating",
                                                          "us-gaap_InterestExpenseDebt"])
                        ad.interest_expense = to_millions(interest_raw)
                        # Interest expense is often reported as negative; store as positive
                        if ad.interest_expense is not None and ad.interest_expense < 0:
                            ad.interest_expense = abs(ad.interest_expense)

                    if ad.operating_income is None:
                        op_income_raw = safe_get(inc_df, date_col,
                                                  standards=["OperatingIncome"],
                                                  concepts=["us-gaap_OperatingIncomeLoss"])
                        ad.operating_income = to_millions(op_income_raw)

                    if ad.income_tax_expense is None:
                        tax_raw = safe_get(inc_df, date_col,
                                           concepts=["us-gaap_IncomeTaxExpenseBenefit"])
                        ad.income_tax_expense = to_millions(tax_raw)

                    if ad.pretax_income is None:
                        pretax_raw = safe_get(inc_df, date_col,
                                              concepts=["us-gaap_IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
                                                        "us-gaap_IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments"])
                        ad.pretax_income = to_millions(pretax_raw)

                    if ad.shares_outstanding is None:
                        shares_diluted_raw = safe_get(inc_df, date_col,
                                                       standards=["SharesFullyDilutedAverage"],
                                                       concepts=["us-gaap_WeightedAverageNumberOfDilutedSharesOutstanding"])
                        if shares_diluted_raw:
                            ad.shares_outstanding = to_millions(shares_diluted_raw)

                # === BALANCE SHEET ===
                # BS has fewer date columns than IS/CF, so fill missing fields
                if not bs_df.empty and date_col in bs_df.columns:
                    if ad.current_assets is None:
                        current_assets_raw = safe_get(bs_df, date_col,
                                                       standards=["CurrentAssetsTotal"],
                                                       concepts=["us-gaap_AssetsCurrent"])
                        ad.current_assets = to_millions(current_assets_raw)

                    if ad.current_liabilities is None:
                        current_liab_raw = safe_get(bs_df, date_col,
                                                     standards=["CurrentLiabilitiesTotal"],
                                                     concepts=["us-gaap_LiabilitiesCurrent"])
                        ad.current_liabilities = to_millions(current_liab_raw)

                    if ad.cash is None:
                        cash_raw = safe_get(bs_df, date_col,
                                            standards=["CashAndMarketableSecurities"],
                                            concepts=["us-gaap_CashAndCashEquivalentsAtCarryingValue"])
                        ad.cash = to_millions(cash_raw)

                    if ad.receivables is None:
                        recv_raw = safe_get(bs_df, date_col,
                                            standards=["TradeReceivables"],
                                            concepts=["us-gaap_AccountsReceivableNetCurrent",
                                                      "us-gaap_AccountsReceivableNet"])
                        ad.receivables = to_millions(recv_raw)

                    if ad.inventory is None:
                        inv_raw = safe_get(bs_df, date_col,
                                           standards=["Inventories"],
                                           concepts=["us-gaap_InventoryNet"])
                        ad.inventory = to_millions(inv_raw)

                    if ad.long_term_debt is None:
                        lt_debt_raw = safe_get(bs_df, date_col,
                                               standards=["LongTermDebt"],
                                               concepts=["us-gaap_LongTermDebtNoncurrent",
                                                         "us-gaap_LongTermDebt"])
                        ad.long_term_debt = to_millions(lt_debt_raw)

                    if ad.total_debt is None:
                        # Recompute lt_debt_raw for total debt calculation
                        lt_debt_raw = safe_get(bs_df, date_col,
                                               standards=["LongTermDebt"],
                                               concepts=["us-gaap_LongTermDebtNoncurrent",
                                                         "us-gaap_LongTermDebt"])
                        debt_components = []
                        if lt_debt_raw is not None:
                            debt_components.append(lt_debt_raw)
                        cp_ltd_raw = safe_get(bs_df, date_col,
                                              standards=["CurrentPortionOfLongTermDebt"],
                                              concepts=["us-gaap_LongTermDebtCurrent"])
                        if cp_ltd_raw is not None:
                            debt_components.append(cp_ltd_raw)
                        st_only_raw = safe_get(bs_df, date_col,
                                               standards=["ShortTermDebt"],
                                               concepts=["us-gaap_CommercialPaper",
                                                         "us-gaap_ShortTermBorrowings"])
                        if st_only_raw is not None:
                            debt_components.append(st_only_raw)
                        if debt_components:
                            ad.total_debt = to_millions(sum(debt_components))

                    equity_raw = safe_get(bs_df, date_col,
                                          standards=["AllEquityBalance", "EquityBalance"],
                                          concepts=["us-gaap_StockholdersEquity"])
                    shares_bs_raw = safe_get(bs_df, date_col,
                                             standards=["SharesYearEnd"],
                                             concepts=["us-gaap_CommonStockSharesOutstanding"])

                    if ad.book_value_per_share is None:
                        if equity_raw is not None and shares_bs_raw is not None and shares_bs_raw != 0:
                            ad.book_value_per_share = round(equity_raw / shares_bs_raw, 2)

                    if ad.shares_outstanding is None and shares_bs_raw is not None:
                        ad.shares_outstanding = to_millions(shares_bs_raw)

                # === CASH FLOW STATEMENT ===
                if not cf_df.empty and date_col in cf_df.columns and ad.depreciation is None:
                    dep_raw = safe_get(cf_df, date_col,
                                       concepts=["us-gaap_DepreciationDepletionAndAmortization",
                                                  "us-gaap_DepreciationAndAmortization"])
                    ad.depreciation = to_millions(dep_raw)

                if not cf_df.empty and date_col in cf_df.columns and ad.operating_cashflow is None:
                    opcf_raw = None
                    # Find the row specifically for total operating cash flow
                    op_matches = cf_df[
                        (cf_df["concept"] == "us-gaap_NetCashProvidedByUsedInOperatingActivities")
                    ]
                    for _, row in op_matches.iterrows():
                        label_lower = str(row.get("label", "")).lower()
                        if "operating" in label_lower:
                            val = row.get(date_col)
                            if val is not None and pd.notna(val):
                                opcf_raw = float(val)
                                break
                    if opcf_raw is None:
                        opcf_raw = safe_get(cf_df, date_col,
                                            standards=["NetCashFromOperatingActivities"],
                                            concepts=["us-gaap_NetCashProvidedByUsedInOperatingActivities"])
                    ad.operating_cashflow = to_millions(opcf_raw)

                # === DERIVED METRICS ===
                if ad.net_margin is None and ad.revenue and ad.net_income and ad.revenue != 0:
                    ad.net_margin = round(ad.net_income / ad.revenue * 100, 2)

                if ad.roe is None and ad.net_income is not None and equity_raw is not None and equity_raw != 0:
                    net_income_raw_val = ad.net_income * 1e6
                    ad.roe = round(net_income_raw_val / equity_raw * 100, 2)

                if ad.revenue_per_share is None and ad.revenue and ad.shares_outstanding and ad.shares_outstanding != 0:
                    ad.revenue_per_share = round(ad.revenue / ad.shares_outstanding, 2)

                if ad.cash_flow_per_share is None and ad.operating_cashflow is not None and ad.shares_outstanding and ad.shares_outstanding != 0:
                    # operating_cashflow is in millions, shares_outstanding is in millions
                    ad.cash_flow_per_share = round(ad.operating_cashflow / ad.shares_outstanding, 2)

                # EBITDA = Operating Income + D&A (both in millions)
                if ad.ebitda is None and ad.operating_income is not None and ad.depreciation is not None:
                    ad.ebitda = round(ad.operating_income + ad.depreciation, 2)

                # Debt/Equity
                if ad.debt_to_equity is None and ad.total_debt is not None and equity_raw is not None and equity_raw != 0:
                    equity_m = equity_raw / 1e6  # convert to millions for comparison
                    if equity_m != 0:
                        ad.debt_to_equity = round(ad.total_debt / equity_m, 2)

                # Debt/EBITDA
                if ad.debt_to_ebitda is None and ad.total_debt is not None and ad.ebitda and ad.ebitda != 0:
                    ad.debt_to_ebitda = round(ad.total_debt / ad.ebitda, 2)

                # Net Debt/EBITDA
                if ad.net_debt_to_ebitda is None and ad.total_debt is not None and ad.cash is not None and ad.ebitda and ad.ebitda != 0:
                    net_debt = ad.total_debt - ad.cash
                    ad.net_debt_to_ebitda = round(net_debt / ad.ebitda, 2)

                # ROIC = NOPAT / Invested Capital
                if ad.roic is None and ad.operating_income is not None and ad.income_tax_expense is not None and ad.pretax_income is not None and ad.pretax_income != 0:
                    eff_tax_rate = ad.income_tax_expense / ad.pretax_income
                    nopat = ad.operating_income * (1 - eff_tax_rate)
                    # Invested Capital = Equity + Total Debt - Cash (all in millions)
                    equity_m = equity_raw / 1e6 if equity_raw is not None else None
                    if equity_m is not None and ad.total_debt is not None:
                        cash_m = ad.cash if ad.cash is not None else 0
                        invested_capital = equity_m + ad.total_debt - cash_m
                        if invested_capital != 0:
                            ad.roic = round(nopat / invested_capital * 100, 2)

                year_data[fiscal_year] = ad

        except Exception as e:
            print(f"[EDGAR] Error processing filing {i} for {ticker}: {e}")
            continue

    # Return sorted by year
    result = sorted(year_data.values(), key=lambda d: d.year)
    print(f"[EDGAR] Fetched {len(result)} years of annual data for {ticker}")
    return result


def fetch_edgar_quarterly(ticker: str) -> list[QuarterlyData]:
    """Fetch up to 5 years (~20 quarters) of quarterly data from SEC EDGAR 10-Q filings.

    Extracts revenue and EPS using the same XBRL label patterns as fetch_edgar_annual.

    10-Q income statements report YTD (cumulative) figures, not single-quarter.
    For example, Apple's Q3 filing (9-month period ending June) shows 9-month revenue.
    This function collects YTD data from all filings, then computes single-quarter
    values by subtracting the previous quarter's YTD from the current quarter's YTD.
    Q1 values are already single-quarter (no subtraction needed).

    It also extracts Q4 values by subtracting the Q3 YTD from the full-year 10-K data.
    """
    from edgar import Company, set_identity
    from edgar.financials import Financials
    import pandas as pd

    identity = os.environ.get("EDGAR_IDENTITY", "Value Line Skill user@example.com")
    set_identity(identity)

    current_year = datetime.now().year
    min_year = current_year - 6  # extra year for YTD subtraction

    try:
        company = Company(ticker)
    except Exception as e:
        print(f"[EDGAR] Could not find company '{ticker}' for quarterly data: {e}")
        return []

    # --- Determine fiscal year-end month from most recent 10-K (or 20-F) ---
    filings_10k = company.get_filings(form="10-K")
    if not filings_10k or len(filings_10k) == 0:
        filings_10k = company.get_filings(form="20-F")
    fy_end_month = 12  # default to calendar year
    if filings_10k and len(filings_10k) > 0:
        try:
            k_filing = filings_10k[0]
            por = k_filing.period_of_report
            if isinstance(por, str):
                por = date.fromisoformat(por)
            fy_end_month = por.month
        except Exception:
            pass

    def fiscal_quarter_from_date(period_end: date) -> int:
        """Given a period-end date and the FY-end month, return fiscal quarter 1-4.

        Quarter boundaries (months after FY-end):
          Q1 ends ~3 months after FY-end
          Q2 ends ~6 months after FY-end
          Q3 ends ~9 months after FY-end
          Q4 ends ~12 months after FY-end (i.e. same month as FY-end)

        Period-end dates sometimes fall a few days into the next calendar month
        (e.g., Apple Q3 ending July 1 instead of June 30). We handle this by
        checking if the day is <= 7 and, if so, treating it as the prior month.
        """
        month = period_end.month
        day = period_end.day
        # If the date is in the first week of a month, treat it as the prior month
        # to handle fiscal calendars that end e.g. July 1 instead of June 30
        if day <= 7:
            # Shift back one month
            month = month - 1 if month > 1 else 12

        months_after_fy_end = (month - fy_end_month) % 12
        if months_after_fy_end == 0:
            return 4  # same month as FY-end = Q4
        elif months_after_fy_end <= 3:
            return 1
        elif months_after_fy_end <= 6:
            return 2
        elif months_after_fy_end <= 9:
            return 3
        else:
            return 4

    def fiscal_year_for_period(period_end_date: date) -> int:
        """Determine fiscal year for a period end date.

        The fiscal year is the calendar year of the FY-end date.
        E.g., Apple Q1 ends Dec 2024 -> FY2025 (because FY ends Sep 2025).
        """
        month = period_end_date.month
        year = period_end_date.year
        # If this month is after the FY-end month, it belongs to the next fiscal year
        if month > fy_end_month:
            return year + 1
        return year

    META_COLS = {
        "concept", "label", "standard_concept", "level", "abstract",
        "dimension", "is_breakdown", "dimension_axis", "dimension_member",
        "dimension_member_label", "dimension_label", "balance", "weight",
        "preferred_sign", "parent_concept", "parent_abstract_concept",
    }

    def get_date_columns(df: pd.DataFrame) -> list[str]:
        return [c for c in df.columns if c not in META_COLS and c[:2] == "20"]

    def non_dimensional(df: pd.DataFrame) -> pd.DataFrame:
        mask = (df["dimension"] == False) | (df["dimension"].isna())
        return df[mask].copy()

    def safe_get(df: pd.DataFrame, col: str, *, concept: str | None = None,
                 standard: str | None = None, concepts: list[str] | None = None,
                 standards: list[str] | None = None) -> float | None:
        all_standards = []
        if standard:
            all_standards.append(standard)
        if standards:
            all_standards.extend(standards)
        all_concepts = []
        if concept:
            all_concepts.append(concept)
        if concepts:
            all_concepts.extend(concepts)

        for sc in all_standards:
            matches = df[df["standard_concept"] == sc]
            for _, row in matches.iterrows():
                if row.get("abstract", False):
                    continue
                val = row.get(col)
                if val is not None and pd.notna(val):
                    return float(val)

        for cn in all_concepts:
            if cn.startswith("us-gaap_"):
                matches = df[df["concept"] == cn]
            else:
                matches = df[df["concept"].str.contains(cn, na=False, regex=False)]
            for _, row in matches.iterrows():
                if row.get("abstract", False):
                    continue
                val = row.get(col)
                if val is not None and pd.notna(val):
                    return float(val)

        return None

    def to_millions(val: float | None) -> float | None:
        if val is None:
            return None
        return round(val / 1e6, 2)

    filings_10q = company.get_filings(form="10-Q")
    if not filings_10q or len(filings_10q) == 0:
        print(f"[EDGAR] No 10-Q filings found for {ticker}, trying 6-K...")
        filings_10q = company.get_filings(form="6-K")

    if not filings_10q or len(filings_10q) == 0:
        print(f"[EDGAR] No 10-Q or 6-K filings found for {ticker}")
        return []

    # Step 1: Collect YTD data from each filing.
    # Key: (fiscal_year, fiscal_quarter), Value: dict with ytd_revenue, ytd_eps
    # Each 10-Q has 2 date columns: current period and prior year comparable.
    # Both are YTD values ending at the respective quarter.
    ytd_data: dict[tuple[int, int], dict] = {}

    num_filings = min(len(filings_10q), 22)

    for i in range(num_filings):
        try:
            filing = filings_10q[i]
            xbrl_data = filing.xbrl()
            if xbrl_data is None:
                continue

            fins = Financials(xbrl_data)

            try:
                inc_stmt = fins.income_statement()
                inc_df = non_dimensional(inc_stmt.to_dataframe())
            except Exception:
                inc_df = pd.DataFrame()

            if inc_df.empty:
                continue

            date_cols = sorted(get_date_columns(inc_df))
            if not date_cols:
                continue

            # Only use the most recent date column (the primary/current period).
            # Prior year comparison columns can have mismatched period durations
            # (e.g., a Q3 filing's prior year column may cover a different span
            # than what the date suggests), leading to wrong YTD values.
            # We rely on each filing's own primary column for accurate data.
            for dc in [date_cols[-1]]:
                try:
                    period_end = date.fromisoformat(dc)
                except Exception:
                    continue

                fy = fiscal_year_for_period(period_end)
                fq = fiscal_quarter_from_date(period_end)

                if fy < min_year:
                    continue

                key = (fy, fq)
                if key in ytd_data:
                    continue  # prefer data from more recent filing (processed first)

                revenue_raw = safe_get(inc_df, dc,
                                       standards=["Revenue"],
                                       concepts=["us-gaap_Revenues",
                                                 "us-gaap_RevenueFromContractWithCustomerExcludingAssessedTax"])
                eps = safe_get(inc_df, dc,
                               concepts=["us-gaap_EarningsPerShareDiluted"])

                ytd_data[key] = {
                    "ytd_revenue": revenue_raw,
                    "ytd_eps": eps,
                }

        except Exception as e:
            print(f"[EDGAR] Error processing 10-Q filing {i} for {ticker}: {e}")
            continue

    # Step 2: Also get full-year data from 10-K filings to compute Q4
    # (Q4 = full_year - Q3_YTD)
    if filings_10k and len(filings_10k) > 0:
        num_k = min(len(filings_10k), 8)
        for i in range(num_k):
            try:
                filing = filings_10k[i]
                xbrl_data = filing.xbrl()
                if xbrl_data is None:
                    continue
                fins = Financials(xbrl_data)
                try:
                    inc_stmt = fins.income_statement()
                    inc_df = non_dimensional(inc_stmt.to_dataframe())
                except Exception:
                    continue
                if inc_df.empty:
                    continue
                date_cols = sorted(get_date_columns(inc_df))
                for dc in date_cols:
                    try:
                        period_end = date.fromisoformat(dc)
                    except Exception:
                        continue
                    # Use fiscal_quarter_from_date to determine if this is a Q4 (FY-end) column
                    fq = fiscal_quarter_from_date(period_end)
                    if fq != 4:
                        continue  # not a FY-end column
                    fy = fiscal_year_for_period(period_end)
                    if fy < min_year:
                        continue
                    key = (fy, 4)  # Q4 = full year
                    # Store as "full_year" data, not ytd
                    if key not in ytd_data:
                        revenue_raw = safe_get(inc_df, dc,
                                               standards=["Revenue"],
                                               concepts=["us-gaap_Revenues",
                                                         "us-gaap_RevenueFromContractWithCustomerExcludingAssessedTax"])
                        eps = safe_get(inc_df, dc,
                                       concepts=["us-gaap_EarningsPerShareDiluted"])
                        ytd_data[key] = {
                            "ytd_revenue": revenue_raw,
                            "ytd_eps": eps,
                            "is_full_year": True,
                        }
            except Exception as e:
                print(f"[EDGAR] Error processing 10-K filing {i} for quarterly Q4: {e}")
                continue

    # Step 3: Convert YTD to single-quarter values
    # Q1: value is already single-quarter (3 months from FY start)
    # Q2: subtract Q1 YTD from Q2 YTD
    # Q3: subtract Q2 YTD from Q3 YTD
    # Q4: subtract Q3 YTD from full-year (10-K) value
    quarter_data: dict[tuple[int, int], QuarterlyData] = {}
    cutoff_year = current_year - 5

    for (fy, fq), data in sorted(ytd_data.items()):
        if fy < cutoff_year:
            continue

        ytd_rev = data.get("ytd_revenue")
        ytd_eps = data.get("ytd_eps")
        is_full_year = data.get("is_full_year", False)

        if fq == 1:
            # Q1: YTD = single quarter, no subtraction needed
            single_rev = ytd_rev
            single_eps = ytd_eps
        elif fq == 4 and is_full_year:
            # Q4 from 10-K: subtract Q3 YTD
            prev_key = (fy, 3)
            prev = ytd_data.get(prev_key, {})
            prev_rev = prev.get("ytd_revenue")
            prev_eps = prev.get("ytd_eps")
            single_rev = (ytd_rev - prev_rev) if (ytd_rev is not None and prev_rev is not None) else None
            single_eps = round(ytd_eps - prev_eps, 4) if (ytd_eps is not None and prev_eps is not None) else None
        else:
            # Q2 or Q3: subtract previous quarter's YTD
            prev_key = (fy, fq - 1)
            prev = ytd_data.get(prev_key, {})
            prev_rev = prev.get("ytd_revenue")
            prev_eps = prev.get("ytd_eps")
            single_rev = (ytd_rev - prev_rev) if (ytd_rev is not None and prev_rev is not None) else None
            single_eps = round(ytd_eps - prev_eps, 4) if (ytd_eps is not None and prev_eps is not None) else None

        qd = QuarterlyData(
            year=fy,
            quarter=fq,
            revenue=to_millions(single_rev),
            eps=round(single_eps, 2) if single_eps is not None else None,
        )
        quarter_data[(fy, fq)] = qd

    result = sorted(quarter_data.values(), key=lambda d: (d.year, d.quarter))
    print(f"[EDGAR] Fetched {len(result)} quarters of data for {ticker}")
    return result


def fetch_segment_data(ticker: str) -> list[SegmentData]:
    """Fetch product/service and geographic segment revenue from 10-K (or 20-F) XBRL data."""
    from edgar import Company, set_identity
    from edgar.financials import Financials
    import pandas as pd

    identity = os.environ.get("EDGAR_IDENTITY", "Value Line Skill user@example.com")
    set_identity(identity)

    try:
        company = Company(ticker)
        filings_10k = company.get_filings(form="10-K")
        if not filings_10k or len(filings_10k) == 0:
            filings_10k = company.get_filings(form="20-F")
    except Exception as e:
        print(f"[EDGAR] Could not find company '{ticker}' for segment data: {e}")
        return []

    if not filings_10k or len(filings_10k) == 0:
        return []

    META_COLS = {
        "concept", "label", "standard_concept", "level", "abstract",
        "dimension", "is_breakdown", "dimension_axis", "dimension_member",
        "dimension_member_label", "dimension_label", "balance", "weight",
        "preferred_sign", "parent_concept", "parent_abstract_concept",
    }

    def get_date_columns(df: pd.DataFrame) -> list[str]:
        return [c for c in df.columns if c not in META_COLS and c[:2] == "20"]

    year_segments: dict[int, SegmentData] = {}
    num_filings = min(len(filings_10k), 16)

    for i in range(num_filings):
        try:
            filing = filings_10k[i]
            xbrl_data = filing.xbrl()
            if xbrl_data is None:
                continue
            fins = Financials(xbrl_data)
            try:
                inc_stmt = fins.income_statement()
                inc_df = inc_stmt.to_dataframe()
            except Exception:
                continue

            date_cols = sorted(get_date_columns(inc_df))
            if not date_cols:
                continue

            # Find revenue rows with dimensions (segments)
            rev_dim = inc_df[
                (inc_df["dimension"] == True) &
                (inc_df["concept"].str.contains("Revenue", na=False))
            ]

            for dc in date_cols:
                try:
                    fiscal_year = int(dc[:4])
                except (ValueError, IndexError):
                    continue

                if fiscal_year in year_segments:
                    continue

                sd = SegmentData(year=fiscal_year)

                for _, row in rev_dim.iterrows():
                    axis = str(row.get("dimension_axis", ""))
                    label = str(row.get("label", ""))
                    val = row.get(dc)
                    if val is None or pd.isna(val):
                        continue
                    val_m = round(float(val) / 1e6, 0)

                    # Product/Service segments
                    if axis == "srt:ProductOrServiceAxis":
                        sd.product_segments[label] = val_m
                    # Geographic/Operating segments
                    elif axis in ("srt:ConsolidationItemsAxis", "srt:StatementGeographicalAxis"):
                        # Clean label: remove "Operating segments - " prefix
                        clean_label = label.replace("Operating segments - ", "")
                        sd.geo_segments[clean_label] = val_m

                if sd.product_segments or sd.geo_segments:
                    year_segments[fiscal_year] = sd

        except Exception as e:
            print(f"[EDGAR] Error fetching segment data filing {i}: {e}")
            continue

    result = sorted(year_segments.values(), key=lambda s: s.year)
    print(f"[EDGAR] Fetched segment data for {len(result)} years for {ticker}")
    return result


def fetch_local_json(ticker: str) -> tuple[list[AnnualData], list[SegmentData]]:
    """Load financial data from a local JSON file in the due diligence folder.

    Searches for: DD_OUTPUT_DIR/{ticker}/financials/*_financials.json
    Returns (annual_data, segment_data) or ([], []) if not found.
    """
    import json
    import glob

    # Search multiple possible locations for the JSON file
    dd_bases = [
        os.environ.get("DD_OUTPUT_DIR", os.path.join(os.getcwd(), "due-diligence")),
    ]

    # Build search patterns: exact ticker match AND fuzzy match in folder names
    search_paths = []
    base_ticker = ticker.split('.')[0]  # CSU.TO -> CSU
    for dd_base in dd_bases:
        # Exact ticker folder
        search_paths.append(os.path.join(dd_base, ticker, "financials", "*_financials.json"))
        # Also search all subfolders for ones containing the base ticker
        if os.path.isdir(dd_base):
            for entry in os.listdir(dd_base):
                entry_upper = entry.upper().replace(' ', '')
                if base_ticker in entry_upper and os.path.isdir(os.path.join(dd_base, entry)):
                    search_paths.append(os.path.join(dd_base, entry, "financials", "*_financials.json"))

    json_path = None
    for pattern in search_paths:
        matches = glob.glob(pattern)
        if matches:
            json_path = matches[0]
            break

    if json_path is None:
        print(f"[local] No local JSON found for {ticker}")
        return ([], [])

    print(f"[local] Loading financial data from {json_path}")

    with open(json_path, "r") as f:
        data = json.load(f)

    years_data = data.get("years", {})
    if not years_data:
        print("[local] JSON has no 'years' data")
        return ([], [])

    annual_list: list[AnnualData] = []
    segment_list: list[SegmentData] = []

    for year_key, yd in years_data.items():
        year = int(year_key)

        # Extract raw values (already in millions per JSON spec)
        revenue = yd.get("revenue")
        net_income = yd.get("net_income")
        eps = yd.get("eps")
        operating_income = yd.get("operating_income")
        interest_expense = yd.get("interest_expense")
        income_tax_expense = yd.get("income_tax_expense")
        pretax_income = yd.get("pretax_income")
        depreciation = yd.get("depreciation")
        shares_outstanding = yd.get("shares_outstanding")
        total_debt = yd.get("total_debt")
        long_term_debt = yd.get("long_term_debt")
        current_assets = yd.get("current_assets")
        current_liabilities = yd.get("current_liabilities")
        cash = yd.get("cash")
        receivables = yd.get("receivables")
        inventory = yd.get("inventory")
        operating_cashflow = yd.get("operating_cashflow")
        shareholders_equity = yd.get("shareholders_equity")
        dividends_per_share = yd.get("dividends_per_share")

        # Interest expense: store as positive
        if interest_expense is not None and interest_expense < 0:
            interest_expense = abs(interest_expense)

        # Derived metrics
        revenue_per_share = None
        if revenue is not None and shares_outstanding and shares_outstanding != 0:
            revenue_per_share = round(revenue / shares_outstanding, 2)

        book_value_per_share = None
        if shareholders_equity is not None and shares_outstanding and shares_outstanding != 0:
            book_value_per_share = round(shareholders_equity / shares_outstanding, 2)

        cash_flow_per_share = None
        if operating_cashflow is not None and shares_outstanding and shares_outstanding != 0:
            cash_flow_per_share = round(operating_cashflow / shares_outstanding, 2)

        net_margin = None
        if net_income is not None and revenue and revenue != 0:
            net_margin = round(net_income / revenue * 100, 2)

        roe = None
        if net_income is not None and shareholders_equity and shareholders_equity != 0:
            roe = round(net_income / shareholders_equity * 100, 2)

        ebitda = None
        if operating_income is not None and depreciation is not None:
            ebitda = round(operating_income + depreciation, 2)

        roic = None
        if (operating_income is not None and income_tax_expense is not None
                and pretax_income is not None and pretax_income != 0):
            eff_tax_rate = income_tax_expense / pretax_income
            nopat = operating_income * (1 - eff_tax_rate)
            equity_val = shareholders_equity if shareholders_equity is not None else 0
            debt_val = total_debt if total_debt is not None else 0
            cash_val = cash if cash is not None else 0
            invested_capital = equity_val + debt_val - cash_val
            if invested_capital != 0:
                roic = round(nopat / invested_capital * 100, 2)

        debt_to_equity = None
        if total_debt is not None and shareholders_equity and shareholders_equity != 0:
            debt_to_equity = round(total_debt / shareholders_equity, 2)

        debt_to_ebitda = None
        if total_debt is not None and ebitda and ebitda != 0:
            debt_to_ebitda = round(total_debt / ebitda, 2)

        net_debt_to_ebitda = None
        if total_debt is not None and cash is not None and ebitda and ebitda != 0:
            net_debt = total_debt - cash
            net_debt_to_ebitda = round(net_debt / ebitda, 2)

        ad = AnnualData(
            year=year,
            revenue=revenue,
            net_income=net_income,
            eps=eps,
            dividends_per_share=dividends_per_share,
            book_value_per_share=book_value_per_share,
            cash_flow_per_share=cash_flow_per_share,
            shares_outstanding=shares_outstanding,
            total_debt=total_debt,
            long_term_debt=long_term_debt,
            interest_expense=interest_expense,
            current_assets=current_assets,
            current_liabilities=current_liabilities,
            cash=cash,
            receivables=receivables,
            inventory=inventory,
            net_margin=net_margin,
            roe=roe,
            revenue_per_share=revenue_per_share,
            operating_income=operating_income,
            operating_cashflow=operating_cashflow,
            income_tax_expense=income_tax_expense,
            pretax_income=pretax_income,
            roic=roic,
            debt_to_equity=debt_to_equity,
            debt_to_ebitda=debt_to_ebitda,
            net_debt_to_ebitda=net_debt_to_ebitda,
            ebitda=ebitda,
            depreciation=depreciation,
        )
        annual_list.append(ad)

        # Segments: collect all keys starting with "segments_"
        geo_segs = {}
        product_segs = {}
        for key, val in yd.items():
            if key.startswith("segments_") and isinstance(val, dict):
                if "geo" in key.lower():
                    geo_segs.update(val)
                elif "product" in key.lower() or "service" in key.lower():
                    product_segs.update(val)
                else:
                    # Default: treat as geo segments
                    geo_segs.update(val)

        if geo_segs or product_segs:
            sd = SegmentData(year=year, product_segments=product_segs, geo_segments=geo_segs)
            segment_list.append(sd)

    annual_list.sort(key=lambda d: d.year)
    segment_list.sort(key=lambda s: s.year)

    print(f"[local] Found local financial data: {len(annual_list)} years")
    return (annual_list, segment_list)


def fetch_yfinance_data(ticker: str) -> tuple:
    """Fetch market data and price history from Yahoo Finance.

    Returns (MarketData, price_history_DataFrame).
    """
    import yfinance as yf

    tk = yf.Ticker(ticker)
    info = tk.info or {}

    price = info.get("currentPrice") or info.get("regularMarketPrice")
    pe = info.get("trailingPE")
    div_yield = info.get("dividendYield")
    beta = info.get("beta")
    market_cap_raw = info.get("marketCap")
    market_cap = round(market_cap_raw / 1e9, 2) if market_cap_raw else None
    high_52 = info.get("fiftyTwoWeekHigh")
    low_52 = info.get("fiftyTwoWeekLow")
    company_name = info.get("shortName", "")
    exchange = info.get("exchange", "")
    sector = info.get("sector", "")
    industry = info.get("industry", "")
    description = info.get("longBusinessSummary", "")

    # Truncate description to 300 chars at word boundary
    if description and len(description) > 300:
        truncated = description[:300]
        last_space = truncated.rfind(" ")
        if last_space > 200:
            truncated = truncated[:last_space]
        description = truncated + "..."

    market = MarketData(
        price=price,
        pe_ratio=pe,
        dividend_yield=div_yield,
        beta=beta,
        market_cap=market_cap,
        week_52_high=high_52,
        week_52_low=low_52,
        company_name=company_name,
        exchange=exchange,
        sector=sector,
        industry=industry,
        description=description,
    )

    # Fetch weekly price history for ~15 years
    try:
        price_history = tk.history(period="15y", interval="1wk")
    except Exception as e:
        print(f"[yfinance] Error fetching price history: {e}")
        price_history = None

    print(f"[yfinance] Market data fetched for {ticker}: price={price}, PE={pe}")
    return (market, price_history)


def fetch_all_data(ticker: str) -> StockData:
    """Orchestrate all data fetching: local JSON or EDGAR for financials, yfinance for market data.

    Checks for local JSON first, then falls back to EDGAR, then yfinance.
    """
    import pandas as pd

    # Fetch market data from yfinance (always needed for price/market info)
    market, price_history = fetch_yfinance_data(ticker)

    # 1. Check for local JSON first
    local_annual, local_segments = fetch_local_json(ticker)

    if local_annual:
        annual = local_annual
        quarterly = []  # No quarterly from JSON
        segments = local_segments
    else:
        # 2. Try EDGAR (existing code)
        annual = fetch_edgar_annual(ticker)
        quarterly = fetch_edgar_quarterly(ticker)
        segments = fetch_segment_data(ticker)

    # Fallback: if EDGAR annual is empty, use yfinance financials
    if not annual:
        print(f"[fallback] EDGAR annual empty for {ticker}, trying yfinance financials...")
        import yfinance as yf
        tk = yf.Ticker(ticker)

        try:
            fin = tk.financials  # annual income statement
            if fin is not None and not fin.empty:
                for col in fin.columns:
                    try:
                        yr = col.year if hasattr(col, 'year') else int(str(col)[:4])
                    except Exception:
                        continue
                    ad = AnnualData(year=yr)

                    # Revenue
                    for label in ["Total Revenue", "Revenue"]:
                        if label in fin.index:
                            val = fin.loc[label, col]
                            if pd.notna(val):
                                ad.revenue = round(float(val) / 1e6, 2)
                                break

                    # Net Income
                    for label in ["Net Income", "Net Income Common Stockholders"]:
                        if label in fin.index:
                            val = fin.loc[label, col]
                            if pd.notna(val):
                                ad.net_income = round(float(val) / 1e6, 2)
                                break

                    # EPS (Diluted)
                    for label in ["Diluted EPS", "Basic EPS"]:
                        if label in fin.index:
                            val = fin.loc[label, col]
                            if pd.notna(val):
                                ad.eps = round(float(val), 2)
                                break

                    annual.append(ad)
        except Exception as e:
            print(f"[fallback] yfinance annual financials error: {e}")

        # Try balance sheet
        try:
            bs = tk.balance_sheet
            if bs is not None and not bs.empty:
                for col in bs.columns:
                    try:
                        yr = col.year if hasattr(col, 'year') else int(str(col)[:4])
                    except Exception:
                        continue
                    # Find existing AnnualData or create
                    existing = [a for a in annual if a.year == yr]
                    ad = existing[0] if existing else AnnualData(year=yr)
                    if not existing:
                        annual.append(ad)

                    for label, attr in [
                        ("Current Assets", "current_assets"),
                        ("Current Liabilities", "current_liabilities"),
                        ("Cash And Cash Equivalents", "cash"),
                        ("Net Receivables", "receivables"),
                        ("Inventory", "inventory"),
                        ("Long Term Debt", "long_term_debt"),
                        ("Total Debt", "total_debt"),
                    ]:
                        if label in bs.index and getattr(ad, attr) is None:
                            val = bs.loc[label, col]
                            if pd.notna(val):
                                setattr(ad, attr, round(float(val) / 1e6, 2))

                    # Shares outstanding
                    for label in ["Share Issued", "Ordinary Shares Number"]:
                        if label in bs.index and ad.shares_outstanding is None:
                            val = bs.loc[label, col]
                            if pd.notna(val):
                                ad.shares_outstanding = round(float(val) / 1e6, 2)
                                break

                    # Book value per share
                    for label in ["Stockholders Equity", "Total Stockholder Equity"]:
                        if label in bs.index and ad.book_value_per_share is None:
                            equity_val = bs.loc[label, col]
                            if pd.notna(equity_val) and ad.shares_outstanding and ad.shares_outstanding != 0:
                                ad.book_value_per_share = round(float(equity_val) / (ad.shares_outstanding * 1e6), 2)
                                break
        except Exception as e:
            print(f"[fallback] yfinance balance sheet error: {e}")

        # Try cash flow
        try:
            cf = tk.cashflow
            if cf is not None and not cf.empty:
                for col in cf.columns:
                    try:
                        yr = col.year if hasattr(col, 'year') else int(str(col)[:4])
                    except Exception:
                        continue
                    existing = [a for a in annual if a.year == yr]
                    ad = existing[0] if existing else AnnualData(year=yr)
                    if not existing:
                        annual.append(ad)

                    for label in ["Operating Cash Flow", "Total Cash From Operating Activities"]:
                        if label in cf.index and ad.operating_cashflow is None:
                            val = cf.loc[label, col]
                            if pd.notna(val):
                                ad.operating_cashflow = round(float(val) / 1e6, 2)
                                break
        except Exception as e:
            print(f"[fallback] yfinance cashflow error: {e}")

        # Derive metrics for fallback data
        for ad in annual:
            if ad.net_margin is None and ad.revenue and ad.net_income and ad.revenue != 0:
                ad.net_margin = round(ad.net_income / ad.revenue * 100, 2)
            if ad.revenue_per_share is None and ad.revenue and ad.shares_outstanding and ad.shares_outstanding != 0:
                ad.revenue_per_share = round(ad.revenue / ad.shares_outstanding, 2)
            if ad.cash_flow_per_share is None and ad.operating_cashflow is not None and ad.shares_outstanding and ad.shares_outstanding != 0:
                ad.cash_flow_per_share = round(ad.operating_cashflow / ad.shares_outstanding, 2)

        annual.sort(key=lambda d: d.year)

    # Fallback: if EDGAR quarterly is empty, use yfinance quarterly financials
    if not quarterly:
        print(f"[fallback] EDGAR quarterly empty for {ticker}, trying yfinance quarterly_financials...")
        import yfinance as yf
        tk = yf.Ticker(ticker)

        try:
            qfin = tk.quarterly_financials
            if qfin is not None and not qfin.empty:
                for col in qfin.columns:
                    try:
                        dt = col
                        yr = dt.year if hasattr(dt, 'year') else int(str(dt)[:4])
                        month = dt.month if hasattr(dt, 'month') else 1
                    except Exception:
                        continue
                    if month <= 3:
                        q = 1
                    elif month <= 6:
                        q = 2
                    elif month <= 9:
                        q = 3
                    else:
                        q = 4

                    qd = QuarterlyData(year=yr, quarter=q)

                    for label in ["Total Revenue", "Revenue"]:
                        if label in qfin.index:
                            val = qfin.loc[label, col]
                            if pd.notna(val):
                                qd.revenue = round(float(val) / 1e6, 2)
                                break

                    for label in ["Diluted EPS", "Basic EPS"]:
                        if label in qfin.index:
                            val = qfin.loc[label, col]
                            if pd.notna(val):
                                qd.eps = round(float(val), 2)
                                break

                    quarterly.append(qd)

                quarterly.sort(key=lambda d: (d.year, d.quarter))
        except Exception as e:
            print(f"[fallback] yfinance quarterly financials error: {e}")

    # Dividends: if not from EDGAR, try yfinance
    has_dividends = any(a.dividends_per_share is not None for a in annual)
    if not has_dividends and annual:
        try:
            import yfinance as yf
            tk = yf.Ticker(ticker)
            divs = tk.dividends
            if divs is not None and len(divs) > 0:
                # Group by year and sum
                yearly_divs: dict[int, float] = {}
                for dt_idx, amount in divs.items():
                    yr = dt_idx.year
                    yearly_divs[yr] = yearly_divs.get(yr, 0.0) + float(amount)

                for ad in annual:
                    if ad.year in yearly_divs:
                        ad.dividends_per_share = round(yearly_divs[ad.year], 4)
        except Exception as e:
            print(f"[yfinance] Error fetching dividends: {e}")

    stock_data = StockData(
        ticker=ticker,
        market=market,
        annual=annual,
        quarterly=quarterly,
        segments=segments,
        price_history=price_history,
    )

    print(f"[fetch_all_data] Complete: {len(annual)} annual, {len(quarterly)} quarterly, {len(segments)} segment years")
    return stock_data


def generate_price_chart(price_history_df) -> str:
    """Generate a base64-encoded PNG price chart with volume subplot.

    Args:
        price_history_df: pandas DataFrame with DatetimeIndex and columns
                          'Close' and 'Volume' (weekly data from yfinance).

    Returns:
        base64-encoded PNG string, or empty string if input is None/empty.
    """
    if price_history_df is None or price_history_df.empty:
        return ""

    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates

    fig, (ax_price, ax_vol) = plt.subplots(
        2, 1, sharex=True,
        gridspec_kw={'height_ratios': [3, 1]},
        figsize=(4.5, 2.5),
        dpi=150,
    )

    dates = price_history_df.index
    close = price_history_df['Close']
    volume = price_history_df['Volume']

    # Top subplot: price line
    ax_price.plot(dates, close, color='#1a237e', linewidth=1)
    ax_price.yaxis.set_major_formatter(
        plt.FuncFormatter(lambda x, _: f'${x:,.0f}')
    )
    ax_price.tick_params(axis='both', labelsize=7)
    ax_price.grid(False)
    ax_price.spines['top'].set_visible(False)
    ax_price.spines['right'].set_visible(False)

    # Bottom subplot: volume bars
    ax_vol.bar(dates, volume, color='#c5cae9', edgecolor='none', alpha=0.7, width=5)
    ax_vol.yaxis.set_major_formatter(
        plt.FuncFormatter(lambda x, _: f'{x / 1e6:,.0f}M')
    )
    ax_vol.tick_params(axis='both', labelsize=7)
    ax_vol.grid(False)
    ax_vol.spines['top'].set_visible(False)
    ax_vol.spines['right'].set_visible(False)

    # X-axis: show only years
    ax_vol.xaxis.set_major_locator(mdates.YearLocator())
    ax_vol.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
    plt.setp(ax_vol.xaxis.get_majorticklabels(), rotation=0, fontsize=7)

    fig.tight_layout(pad=0.3)

    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight', pad_inches=0.02)
    plt.close(fig)
    buf.seek(0)

    return base64.b64encode(buf.read()).decode('ascii')


# ── Formatting helpers ──────────────────────────────────────────────

def fmt_num(val, decimals=2):
    """Format number or return '—' if None."""
    if val is None: return "—"
    return f"{val:,.{decimals}f}"

def fmt_pct(val):
    """Format percentage or return '—' if None."""
    if val is None: return "—"
    return f"{val:.1f}%"

def fmt_money(val):
    """Format as $1.2B or $234.5M, or '—' if None."""
    if val is None: return "—"
    if abs(val) >= 1000:
        return f"${val/1000:.1f}B"
    return f"${val:.1f}M"

def calc_cagr(start_val, end_val, years):
    """Calculate CAGR. Returns percentage or None."""
    if not start_val or not end_val or years <= 0 or start_val <= 0:
        return None
    return ((end_val / start_val) ** (1 / years) - 1) * 100

def truncate(text, max_chars=300):
    """Truncate at word boundary, append '...' if needed."""
    if not text: return "—"
    if len(text) <= max_chars: return text
    truncated = text[:max_chars].rsplit(' ', 1)[0]
    return truncated + "..."


# ── HTML builder ────────────────────────────────────────────────────

def fmt_x(val):
    """Format ratio as 'x' multiple or return '—' if None."""
    if val is None: return "—"
    return f"{val:.1f}x"

def build_html(data: StockData, chart_b64: str) -> str:
    """Build a complete HTML document for a Value Line-style one-pager.

    Transposed layout: years as columns, metrics as rows.
    Full-width historical table at top, 2-column grid below.
    """
    import html as html_mod

    m = data.market
    today = date.today().strftime("%B %d, %Y")
    esc = html_mod.escape

    # ── Transposed historical financial data table ──
    # Build header row: Metric | year1 | year2 | ... | yearN
    years = data.annual
    year_headers = "".join(f"<th>{a.year}</th>" for a in years)

    def metric_row(label, values, fmt_fn, idx):
        bg = ' style="background:#f5f5f5;"' if idx % 2 == 0 else ""
        cells = "".join(f"<td>{fmt_fn(v)}</td>" for v in values)
        return f"<tr{bg}><td class='metric-label'><b>{label}</b></td>{cells}</tr>\n"

    row_idx = 0
    hist_rows = ""

    # Revenue ($M) - with commas
    hist_rows += metric_row("Revenue ($M)", [a.revenue for a in years], lambda v: fmt_num(v, 0) if v else "—", row_idx); row_idx += 1
    # Net Income ($M)
    hist_rows += metric_row("Net Income ($M)", [a.net_income for a in years], lambda v: fmt_num(v, 0) if v else "—", row_idx); row_idx += 1
    # EPS
    hist_rows += metric_row("EPS", [a.eps for a in years], lambda v: fmt_num(v) if v else "—", row_idx); row_idx += 1
    # Shares Outstanding (M)
    hist_rows += metric_row("Shares Out (M)", [a.shares_outstanding for a in years], lambda v: fmt_num(v, 0) if v else "—", row_idx); row_idx += 1
    # Div/Share
    hist_rows += metric_row("Div/Share", [a.dividends_per_share for a in years], lambda v: fmt_num(v) if v else "—", row_idx); row_idx += 1
    # BV/Share
    hist_rows += metric_row("BV/Share", [a.book_value_per_share for a in years], lambda v: fmt_num(v) if v else "—", row_idx); row_idx += 1
    # CF/Share
    hist_rows += metric_row("CF/Share", [a.cash_flow_per_share for a in years], lambda v: fmt_num(v) if v else "—", row_idx); row_idx += 1
    # Rev/Share
    hist_rows += metric_row("Rev/Share", [a.revenue_per_share for a in years], lambda v: fmt_num(v) if v else "—", row_idx); row_idx += 1
    # Net Margin
    hist_rows += metric_row("Net Margin", [a.net_margin for a in years], fmt_pct, row_idx); row_idx += 1
    # ROE
    hist_rows += metric_row("ROE", [a.roe for a in years], fmt_pct, row_idx); row_idx += 1
    # ROIC
    hist_rows += metric_row("ROIC", [a.roic for a in years], fmt_pct, row_idx); row_idx += 1
    # Debt/Equity
    hist_rows += metric_row("Debt/Equity", [a.debt_to_equity for a in years], fmt_x, row_idx); row_idx += 1
    # Debt/EBITDA
    hist_rows += metric_row("Debt/EBITDA", [a.debt_to_ebitda for a in years], fmt_x, row_idx); row_idx += 1
    # Net Debt/EBITDA
    hist_rows += metric_row("ND/EBITDA", [a.net_debt_to_ebitda for a in years], fmt_x, row_idx); row_idx += 1

    # ── Quarterly data table rows ──
    qtr_by_year: dict[int, dict[int, QuarterlyData]] = {}
    for q in data.quarterly:
        qtr_by_year.setdefault(q.year, {})[q.quarter] = q
    qtr_years = sorted(qtr_by_year.keys())[-5:]

    quarterly_rows = ""
    for i, yr in enumerate(qtr_years):
        bg = ' style="background:#f5f5f5;"' if i % 2 == 0 else ""
        qs = qtr_by_year[yr]
        rev_cells = ""
        eps_cells = ""
        for qi in range(1, 5):
            q = qs.get(qi)
            if q and q.revenue is not None:
                rev_cells += f"<td style='padding:1px 3px;text-align:right;'>{q.revenue/1000:.1f}</td>"
            else:
                rev_cells += "<td style='padding:1px 3px;text-align:right;'>—</td>"
            if q and q.eps is not None:
                eps_cells += f"<td style='padding:1px 3px;text-align:right;'>{fmt_num(q.eps)}</td>"
            else:
                eps_cells += "<td style='padding:1px 3px;text-align:right;'>—</td>"
        quarterly_rows += (
            f"<tr{bg}>"
            f"<td style='text-align:left;padding:1px 3px;'>{yr}</td>"
            f"{rev_cells}{eps_cells}"
            f"</tr>\n"
        )

    # ── Capital structure (most recent annual) ──
    recent = data.annual[-1] if data.annual else AnnualData(year=0)
    int_coverage = "—"
    if recent.operating_income and recent.interest_expense and recent.interest_expense > 0:
        int_coverage = f"{recent.operating_income / recent.interest_expense:.1f}x"

    cap_rows = [
        ("Total Debt", fmt_money(recent.total_debt)),
        ("LT Debt", fmt_money(recent.long_term_debt)),
        ("Cash", fmt_money(recent.cash)),
        ("Int. Coverage", int_coverage),
        ("Shares Out (M)", fmt_num(recent.shares_outstanding, 0)),
        ("Market Cap", f'${m.market_cap:.1f}B' if m.market_cap else '—'),
    ]
    cap_html = ""
    for idx, (label, val) in enumerate(cap_rows):
        bg = ' style="background:#f5f5f5;"' if idx % 2 == 0 else ""
        cap_html += f"<tr{bg}><td style='text-align:left;padding:1px 3px;'>{label}</td><td style='text-align:right;padding:1px 3px;'>{val}</td></tr>\n"

    # ── Segment data (multi-year transposed table) ──
    segment_html = ""
    if data.segments:
        seg_years = sorted(data.segments, key=lambda s: s.year)

        # Collect all product segment names across all years (ordered by most recent year's value)
        all_product_names: list[str] = []
        all_geo_names: list[str] = []
        if seg_years:
            latest_seg = seg_years[-1]
            all_product_names = [name for name, _ in sorted(latest_seg.product_segments.items(), key=lambda x: -x[1])]
            all_geo_names = [name for name, _ in sorted(latest_seg.geo_segments.items(), key=lambda x: -x[1])]
            # Add any names from earlier years not in latest
            for sy in seg_years:
                for name in sy.product_segments:
                    if name not in all_product_names:
                        all_product_names.append(name)
                for name in sy.geo_segments:
                    if name not in all_geo_names:
                        all_geo_names.append(name)

        seg_year_list = [s.year for s in seg_years]

        if all_product_names:
            seg_year_hdrs = "".join(f"<th style='text-align:right;padding:1px 2px;font-size:8px;'>{y}</th>" for y in seg_year_list)
            segment_html += f"<div style='font-weight:bold;padding:1px 3px;font-size:8.5px;'>Product Revenue ($B)</div>"
            segment_html += f"<table style='border-collapse:collapse;width:100%;font-family:\"Courier New\",monospace;font-size:8px;'>"
            segment_html += f"<tr style='border-bottom:1px solid #999;'><th style='text-align:left;padding:1px 2px;font-size:8px;'>Segment</th>{seg_year_hdrs}</tr>"
            for idx, name in enumerate(all_product_names):
                bg = ' style="background:#f5f5f5;"' if idx % 2 == 0 else ""
                cells = ""
                for sy in seg_years:
                    val = sy.product_segments.get(name)
                    if val is not None:
                        cells += f"<td style='text-align:right;padding:1px 2px;'>{val/1000:.1f}</td>"
                    else:
                        cells += "<td style='text-align:right;padding:1px 2px;'>—</td>"
                segment_html += f"<tr{bg}><td style='text-align:left;padding:1px 2px;white-space:nowrap;'>{esc(name)}</td>{cells}</tr>"
            segment_html += "</table>"

        if all_geo_names:
            seg_year_hdrs = "".join(f"<th style='text-align:right;padding:1px 2px;font-size:8px;'>{y}</th>" for y in seg_year_list)
            segment_html += f"<div style='font-weight:bold;padding:1px 3px;font-size:8.5px;margin-top:2px;'>Geographic Revenue ($B)</div>"
            segment_html += f"<table style='border-collapse:collapse;width:100%;font-family:\"Courier New\",monospace;font-size:8px;'>"
            segment_html += f"<tr style='border-bottom:1px solid #999;'><th style='text-align:left;padding:1px 2px;font-size:8px;'>Region</th>{seg_year_hdrs}</tr>"
            for idx, name in enumerate(all_geo_names):
                bg = ' style="background:#f5f5f5;"' if idx % 2 == 0 else ""
                cells = ""
                for sy in seg_years:
                    val = sy.geo_segments.get(name)
                    if val is not None:
                        cells += f"<td style='text-align:right;padding:1px 2px;'>{val/1000:.1f}</td>"
                    else:
                        cells += "<td style='text-align:right;padding:1px 2px;'>—</td>"
                segment_html += f"<tr{bg}><td style='text-align:left;padding:1px 2px;white-space:nowrap;'>{esc(name)}</td>{cells}</tr>"
            segment_html += "</table>"

    # ── Annual growth rates (CAGR) ──
    growth_html = ""
    if len(data.annual) >= 2:
        first = data.annual[0]
        last = data.annual[-1]
        n_total = last.year - first.year
        mid = None
        for a in data.annual:
            if last.year - a.year >= 4 and last.year - a.year <= 6:
                mid = a
                break
        if mid is None and len(data.annual) >= 3:
            mid = data.annual[len(data.annual) // 2]
        n_5yr = (last.year - mid.year) if mid else 0

        metrics = [
            ("Revenue", first.revenue, mid.revenue if mid else None, last.revenue),
            ("EPS", first.eps, mid.eps if mid else None, last.eps),
            ("Dividends", first.dividends_per_share, mid.dividends_per_share if mid else None, last.dividends_per_share),
            ("Book Value", first.book_value_per_share, mid.book_value_per_share if mid else None, last.book_value_per_share),
        ]
        growth_rows = ""
        for idx, (label, start_val, mid_val, end_val) in enumerate(metrics):
            cagr_10 = calc_cagr(start_val, end_val, n_total) if n_total > 0 else None
            cagr_5 = calc_cagr(mid_val, end_val, n_5yr) if n_5yr > 0 else None
            bg = ' style="background:#f5f5f5;"' if idx % 2 == 0 else ""
            growth_rows += (
                f"<tr{bg}>"
                f"<td style='text-align:left;padding:1px 3px;'>{label}</td>"
                f"<td style='text-align:right;padding:1px 3px;'>{fmt_pct(cagr_10)}</td>"
                f"<td style='text-align:right;padding:1px 3px;'>{fmt_pct(cagr_5)}</td>"
                f"</tr>\n"
            )
        growth_html = f"""
        <table style="border-collapse:collapse;width:100%;font-family:'Courier New',monospace;font-size:9px;">
          <tr style="font-weight:bold;border-bottom:1px solid #999;">
            <td style="text-align:left;padding:1px 3px;">Metric</td>
            <td style="text-align:right;padding:1px 3px;">10-Yr</td>
            <td style="text-align:right;padding:1px 3px;">5-Yr</td>
          </tr>
          {growth_rows}
        </table>"""

    # ── Business description ──
    desc = truncate(m.description, 250)

    # ── Chart image ──
    chart_img = ""
    if chart_b64:
        chart_img = f'<img src="data:image/png;base64,{chart_b64}" style="width:100%;height:160px;object-fit:contain;" />'

    # ── Full HTML document ──
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{esc(m.company_name)} ({esc(data.ticker)}) — Value Line One-Pager</title>
<style>
  @page {{ size: letter; margin: 0.25in; }}
  * {{ box-sizing: border-box; }}
  body {{
    font-family: Arial, Helvetica, sans-serif;
    font-size: 9px;
    margin: 0;
    padding: 0;
    overflow: hidden;
  }}
  .header {{
    background: #1a237e;
    color: #fff;
    padding: 4px 8px;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }}
  .header-left {{ font-size: 18px; font-weight: bold; }}
  .header-left span {{ font-size: 11px; font-weight: normal; opacity: 0.85; }}
  .header-right {{ text-align: right; font-size: 10px; }}
  .header-right td {{ padding: 0 2px; text-align: right; color: #fff; }}
  .section-hdr {{
    background: #e8eaf6;
    padding: 2px 4px;
    font-weight: bold;
    font-size: 10px;
    border-bottom: 1px solid #999;
  }}
  .hist-table {{
    border-collapse: collapse;
    width: 100%;
    font-family: 'Courier New', monospace;
    font-size: 9px;
  }}
  .hist-table th {{
    padding: 1px 2px;
    text-align: right;
    font-weight: bold;
    border-bottom: 1px solid #999;
    font-size: 7.5px;
  }}
  .hist-table th:first-child {{ text-align: left; min-width: 65px; }}
  .hist-table td {{ padding: 1px 2px; text-align: right; font-size: 7.5px; }}
  .hist-table td.metric-label {{ text-align: left; white-space: nowrap; font-size: 7.5px; }}
  .bottom-grid {{
    display: grid;
    grid-template-columns: 50% 50%;
    gap: 0;
  }}
  .bottom-left {{ border-right: 1px solid #999; }}
  .data-table {{
    border-collapse: collapse;
    width: 100%;
    font-family: 'Courier New', monospace;
    font-size: 9px;
  }}
  .data-table th {{
    padding: 1px 3px;
    text-align: right;
    font-weight: bold;
    border-bottom: 1px solid #999;
  }}
  .data-table th:first-child {{ text-align: left; }}
  .data-table td {{ padding: 1px 3px; text-align: right; }}
  .data-table td:first-child {{ text-align: left; }}
  .footer {{
    background: #f5f5f5;
    padding: 2px 8px;
    font-size: 8px;
    color: #666;
    border-top: 1px solid #999;
    text-align: center;
  }}
</style>
</head>
<body>

<!-- HEADER -->
<div class="header">
  <div class="header-left">
    {esc(m.company_name)} <span>&nbsp;{esc(data.ticker)} &bull; {esc(m.exchange)}</span>
  </div>
  <div class="header-right">
    <table><tr>
      <td><b>Price</b> {fmt_num(m.price)}</td>
      <td><b>P/E</b> {fmt_num(m.pe_ratio, 1)}</td>
      <td><b>Div Yld</b> {fmt_pct(m.dividend_yield)}</td>
      <td><b>Beta</b> {fmt_num(m.beta)}</td>
      <td><b>Mkt Cap</b> {f'${m.market_cap:.1f}B' if m.market_cap else '—'}</td>
      <td>{today}</td>
    </tr></table>
  </div>
</div>

<!-- HISTORICAL DATA (full width, transposed) -->
<div class="section-hdr">HISTORICAL FINANCIAL DATA</div>
<table class="hist-table">
  <tr><th>Metric</th>{year_headers}</tr>
  {hist_rows}
</table>

<!-- BOTTOM 2-COLUMN GRID -->
<div class="bottom-grid">

  <!-- BOTTOM LEFT -->
  <div class="bottom-left">
    <div class="section-hdr">PRICE HISTORY</div>
    {chart_img}

    <div class="section-hdr">QUARTERLY DATA (Rev $B / EPS)</div>
    <table class="data-table">
      <tr>
        <th>Year</th>
        <th>Q1 Rev</th><th>Q2 Rev</th><th>Q3 Rev</th><th>Q4 Rev</th>
        <th>Q1 EPS</th><th>Q2 EPS</th><th>Q3 EPS</th><th>Q4 EPS</th>
      </tr>
      {quarterly_rows}
    </table>
  </div>

  <!-- BOTTOM RIGHT -->
  <div class="bottom-right">
    <div class="section-hdr">SEGMENTS</div>
    <div style="padding:1px 4px;">
      {segment_html if segment_html else '<div style="font-size:9px;color:#999;padding:2px;">No segment data available</div>'}
    </div>

    <div class="section-hdr">CAPITAL STRUCTURE</div>
    <div style="padding:1px 4px;">
      <table style="border-collapse:collapse;width:100%;font-family:'Courier New',monospace;font-size:9px;">
        {cap_html}
      </table>
    </div>

    <div class="section-hdr">GROWTH RATES (CAGR)</div>
    <div style="padding:1px 4px;">
      {growth_html}
    </div>

    <div class="section-hdr">BUSINESS</div>
    <p style="padding:1px 4px;margin:0;font-size:9px;line-height:1.2;">
      {esc(desc)}
    </p>
  </div>

</div>

<!-- FOOTER -->
<div class="footer">
  Data sources: SEC EDGAR (edgartools), Yahoo Finance (yfinance) | Generated: {today} | Not investment advice
</div>

</body>
</html>"""

    return html


def render_pdf(html_string: str, output_path: str):
    """Render HTML string to PDF using weasyprint."""
    from weasyprint import HTML
    HTML(string=html_string).write_pdf(output_path)
    print(f"  PDF saved to: {output_path}")


def main():
    if len(sys.argv) < 2:
        print("Usage: value_line_onepager.py <TICKER>")
        sys.exit(1)

    ticker = sys.argv[1].upper()
    output_name = sys.argv[2] if len(sys.argv) > 2 else None
    today = date.today().isoformat()

    # Determine output path
    # Naming convention: {folder_prefix} {date} {ticker} VL.pdf
    # e.g., "dd1 2026-03-26 CSU VL.pdf" inside "due-diligence/dd1 CSU/"
    dd_base = os.environ.get("DD_OUTPUT_DIR", os.path.join(os.getcwd(), "due-diligence"))
    base_ticker = ticker.split('.')[0]  # CSU.TO -> CSU

    # Find the DD folder (from output_name arg or by searching)
    found_folder = None
    folder_prefix = None
    if output_name and os.path.isdir(os.path.join(dd_base, output_name)):
        found_folder = output_name
    elif os.path.isdir(dd_base):
        for entry in os.listdir(dd_base):
            entry_path = os.path.join(dd_base, entry)
            if os.path.isdir(entry_path) and base_ticker in entry.upper():
                found_folder = entry
                break

    if found_folder:
        # Extract folder prefix (e.g., "dd1" from "dd1 CSU")
        parts = found_folder.split(' ', 1)
        folder_prefix = parts[0] if parts else found_folder
        filename = f"{folder_prefix} {today} {base_ticker} VL.pdf"
        output_path = os.path.join(dd_base, found_folder, filename)
    else:
        output_path = f"{ticker}_value_line_{today}.pdf"

    print(f"Generating Value Line one-pager for {ticker}...")

    print("  Fetching financial data...")
    data = fetch_all_data(ticker)

    print("  Generating price chart...")
    chart_b64 = generate_price_chart(data.price_history)

    print("  Building HTML layout...")
    html = build_html(data, chart_b64)

    print("  Rendering PDF...")
    render_pdf(html, output_path)

    print(f"Done! Output: {output_path}")


if __name__ == "__main__":
    main()
