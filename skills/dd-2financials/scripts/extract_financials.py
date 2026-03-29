#!/usr/bin/env python3
"""
Extract financial statements from SEC EDGAR 10-K filings for any ticker.
Usage: python3 extract_financials.py TICKER output.json [--max-filings N]
"""
import json
import sys
import traceback
import pandas as pd
from edgar import Company, set_identity
from edgar.financials import Financials

set_identity("Patrick Wong patrick@januariusholdings.com")


def dedup_index(df):
    return df[~df.index.duplicated(keep='first')]


def get_statement_df(fin, method_name):
    try:
        stmt = getattr(fin, method_name)()
        if stmt is None:
            return None
        df = stmt.to_dataframe()
        if df is None or df.empty:
            return None
        return df
    except Exception as e:
        print(f"    Warning ({method_name}): {e}")
        return None


def merge_dfs(dfs_list):
    if not dfs_list:
        return None
    deduped = [dedup_index(df) for df in dfs_list]
    merged = deduped[0].copy()
    for df in deduped[1:]:
        for col in df.columns:
            if col not in merged.columns:
                merged = merged.join(df[[col]], how="outer")
    year_cols = sorted(merged.columns, reverse=True)
    return merged[year_cols]


def df_to_json_records(df):
    if df is None:
        return None
    records = []
    for idx, row in df.iterrows():
        entry = {"line_item": str(idx)}
        for col in df.columns:
            val = row[col]
            if pd.isna(val):
                entry[str(col)] = None
            elif isinstance(val, float):
                entry[str(col)] = int(val) if val == int(val) else val
            elif isinstance(val, (int,)):
                entry[str(col)] = val
            else:
                entry[str(col)] = str(val)
        records.append(entry)
    return records


def main():
    if len(sys.argv) < 3:
        print("Usage: python3 extract_financials.py TICKER output.json [--max-filings N]")
        sys.exit(1)

    ticker = sys.argv[1].upper()
    output_path = sys.argv[2]
    max_filings = 10
    if "--max-filings" in sys.argv:
        idx = sys.argv.index("--max-filings")
        max_filings = int(sys.argv[idx + 1])

    print(f"Extracting financial statements for {ticker}...")
    company = Company(ticker)
    print(f"Company: {company.name}, CIK: {company.cik}")

    # Try 10-K first, fall back to 20-F for foreign filers
    all_filings = company.get_filings(form="10-K")
    form_type = "10-K"
    if len(all_filings) == 0:
        print("No 10-K filings found, trying 20-F...")
        all_filings = company.get_filings(form="20-F")
        form_type = "20-F"
    if len(all_filings) == 0:
        print("ERROR: No 10-K or 20-F filings found.")
        sys.exit(1)

    filing_count = len(all_filings)
    print(f"Total {form_type} filings: {filing_count}")

    # Strategy: process every 3rd filing to get non-overlapping years,
    # plus fill BS gaps with adjacent filings.
    # Each 10-K has ~3 years IS/CF, ~2 years BS.
    indices_to_try = list(range(0, min(filing_count, max_filings)))
    # Prioritize: 0, 3, 6, 9, ... then fill in 1, 4, 7, ... for BS gaps
    primary = [i for i in range(0, min(filing_count, max_filings), 3)]
    secondary = [i for i in range(1, min(filing_count, max_filings), 3)]
    indices_to_try = primary + secondary

    income_dfs = []
    balance_dfs = []
    cashflow_dfs = []
    processed = 0
    failed_consecutive = 0

    for idx in indices_to_try:
        if idx >= filing_count:
            continue
        filing = all_filings[idx]
        fy = filing.report_date[:4] if filing.report_date else filing.filing_date[:4]
        print(f"\n[{processed+1}] Processing {form_type} FY{fy} (filed {filing.filing_date})...")

        try:
            xbrl = filing.xbrl()
            if xbrl is None:
                print("    No XBRL data, skipping.")
                failed_consecutive += 1
                if failed_consecutive >= 3:
                    print("    3 consecutive failures, stopping.")
                    break
                continue

            fin = Financials(xbrl)
            got_data = False

            df = get_statement_df(fin, "get_income_statement")
            if df is not None:
                income_dfs.append(df)
                print(f"    Income Statement: {list(df.columns)}")
                got_data = True

            df = get_statement_df(fin, "get_balance_sheet")
            if df is not None:
                balance_dfs.append(df)
                print(f"    Balance Sheet: {list(df.columns)}")
                got_data = True

            df = get_statement_df(fin, "get_cash_flow_statement")
            if df is not None:
                cashflow_dfs.append(df)
                print(f"    Cash Flow: {list(df.columns)}")
                got_data = True

            if got_data:
                failed_consecutive = 0
                processed += 1
            else:
                failed_consecutive += 1
                if failed_consecutive >= 3:
                    print("    3 consecutive failures, stopping.")
                    break

        except Exception as e:
            print(f"    Error: {e}")
            failed_consecutive += 1
            if failed_consecutive >= 3:
                print("    3 consecutive failures, stopping.")
                break

    print(f"\nMerging data from {processed} filings...")
    income_merged = merge_dfs(income_dfs)
    balance_merged = merge_dfs(balance_dfs)
    cashflow_merged = merge_dfs(cashflow_dfs)

    for name, df in [("Income Statement", income_merged), ("Balance Sheet", balance_merged), ("Cash Flow", cashflow_merged)]:
        if df is not None:
            print(f"  {name}: {len(df)} items x {len(df.columns)} periods: {list(df.columns)}")

    # Load existing JSON if present, merge in
    try:
        with open(output_path) as f:
            json_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        json_data = {}

    json_data.update({
        "ticker": ticker,
        "company_name": str(company.name),
        "cik": int(company.cik),
        "data_source": f"SEC EDGAR {form_type} filings via edgartools",
        "financial_statements": {
            "income_statement": df_to_json_records(income_merged),
            "balance_sheet": df_to_json_records(balance_merged),
            "cash_flow_statement": df_to_json_records(cashflow_merged),
        }
    })

    with open(output_path, "w") as f:
        json.dump(json_data, f, indent=2, default=str)

    print(f"\nSaved: {output_path}")
    print("EXTRACTION_COMPLETE")


if __name__ == "__main__":
    main()
