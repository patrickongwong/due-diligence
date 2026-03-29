#!/usr/bin/env python3
"""
Convert an existing flat financial JSON (like CSU's csu_financials.json)
into the standard dd-2financials format with financial_statements and operating_metrics.
Usage: python3 convert_existing_json.py input.json output.json [TICKER]
"""
import json
import sys


def main():
    if len(sys.argv) < 3:
        print("Usage: python3 convert_existing_json.py input.json output.json [TICKER]")
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2]
    ticker_override = sys.argv[3] if len(sys.argv) > 3 else None

    with open(input_path) as f:
        raw = json.load(f)

    ticker = ticker_override or raw.get("ticker", "UNKNOWN")
    company_name = raw.get("company", ticker)
    currency = raw.get("currency", "USD")
    units = raw.get("units", "millions")

    # The raw data has a "years" dict where each year maps to flat key-value financial data
    years_data = raw.get("years", raw)
    if not isinstance(years_data, dict):
        print("ERROR: Cannot find year-by-year financial data.")
        sys.exit(1)

    # If the top-level is just years (no "years" key), use the data directly
    # Filter to only year keys
    year_keys = sorted([k for k in years_data.keys() if k.isdigit()])
    if not year_keys:
        print("ERROR: No year data found.")
        sys.exit(1)

    print(f"Converting {ticker}: {len(year_keys)} years ({year_keys[0]}-{year_keys[-1]})")

    # Multiplier to convert to raw dollars (the standard format stores raw values)
    multiplier = 1_000_000 if units == "millions" else (1_000 if units == "thousands" else 1)

    # Build IS, BS, CF line items
    # Map from raw keys to standard labels
    is_map = [
        ("revenue", "Revenue"),
        ("operating_income", "Operating income"),
        ("interest_expense", "Interest expense"),
        ("pretax_income", "Income before income taxes"),
        ("income_tax_expense", "Income tax expense"),
        ("net_income", "Net income"),
        ("depreciation", "Depreciation and amortization"),
    ]
    bs_map = [
        ("cash", "Cash and cash equivalents"),
        ("receivables", "Accounts receivable"),
        ("inventory", "Inventory"),
        ("current_assets", "Total current assets"),
        ("total_assets", "Total assets"),
        ("current_liabilities", "Total current liabilities"),
        ("total_debt", "Total debt"),
        ("long_term_debt", "Long-term debt"),
        ("shareholders_equity", "Shareholders' equity"),
        ("total_equity", "Total equity"),
    ]
    cf_map = [
        ("operating_cashflow", "Cash from operating activities"),
        ("capex", "Capital expenditures"),
    ]
    per_share_map = [
        ("eps", "Earnings per share (diluted)"),
        ("shares_outstanding", "Shares outstanding (millions)"),
    ]

    def build_items(mapping, is_per_share=False):
        items = []
        for raw_key, label in mapping:
            item = {"line_item": label}
            for year in year_keys:
                yd = years_data[year]
                val = yd.get(raw_key)
                if val is not None:
                    if is_per_share:
                        item[year] = str(val)
                    else:
                        item[year] = str(int(val * multiplier)) if isinstance(val, (int, float)) else str(val)
                else:
                    item[year] = None
            # Only include if at least one year has data
            if any(item.get(y) is not None for y in year_keys):
                items.append(item)
        return items

    is_items = build_items(is_map) + build_items(per_share_map, is_per_share=True)
    bs_items = build_items(bs_map)
    cf_items = build_items(cf_map)

    # Add computed items
    # FCF = Operating CF + Capex (capex is negative)
    fcf_item = {"line_item": "Free cash flow"}
    for year in year_keys:
        yd = years_data[year]
        ocf = yd.get("operating_cashflow")
        capex = yd.get("capex")
        if ocf is not None and capex is not None:
            fcf_item[year] = str(int((ocf + capex) * multiplier))
        else:
            fcf_item[year] = None
    cf_items.append(fcf_item)

    # Geographic segments if available
    for year in year_keys:
        yd = years_data[year]
        if "segments_geographic" in yd:
            for seg_name, seg_val in yd["segments_geographic"].items():
                # Find or create the item
                seg_label = f"Revenue - {seg_name}"
                existing = next((i for i in is_items if i["line_item"] == seg_label), None)
                if not existing:
                    existing = {"line_item": seg_label}
                    for y in year_keys:
                        existing[y] = None
                    is_items.append(existing)
                existing[year] = str(int(seg_val * multiplier))

    # Compute operating metrics
    metrics = {}
    for i, year in enumerate(year_keys):
        yd = years_data[year]
        m = {}
        prev = years_data.get(year_keys[i-1]) if i > 0 else None

        rev = yd.get("revenue")
        oi = yd.get("operating_income")
        ni = yd.get("net_income")
        ta = yd.get("total_assets")
        te = yd.get("total_equity") or yd.get("shareholders_equity")
        se = yd.get("shareholders_equity")
        ocf = yd.get("operating_cashflow")
        capex = yd.get("capex")
        dep = yd.get("depreciation")
        eps = yd.get("eps")
        shares = yd.get("shares_outstanding")
        int_exp = yd.get("interest_expense")
        tax = yd.get("income_tax_expense")
        pretax = yd.get("pretax_income")
        debt = yd.get("total_debt")
        lt_debt = yd.get("long_term_debt")
        cash = yd.get("cash")
        ca = yd.get("current_assets")
        cl = yd.get("current_liabilities")

        prev_ta = prev.get("total_assets") if prev else None
        prev_te = (prev.get("total_equity") or prev.get("shareholders_equity")) if prev else None

        def avg(a, b):
            if a is None and b is None: return None
            if a is None: return b
            if b is None: return a
            return (a + b) / 2

        avg_ta = avg(ta, prev_ta)
        avg_te = avg(te, prev_te)

        # Profitability
        if ni and avg_te and avg_te > 0:
            m["roe"] = round(ni / avg_te * 100, 2)
        if ni and avg_ta and avg_ta > 0:
            m["roa"] = round(ni / avg_ta * 100, 2)
        if rev and oi:
            m["operating_margin"] = round(oi / rev * 100, 2)
        if rev and ni:
            m["net_margin"] = round(ni / rev * 100, 2)
        if pretax and tax:
            m["effective_tax_rate"] = round(abs(tax) / pretax * 100, 2) if pretax > 0 else None

        # Revenue growth
        prev_rev = prev.get("revenue") if prev else None
        if rev and prev_rev and prev_rev > 0:
            m["revenue_growth"] = round((rev - prev_rev) / prev_rev * 100, 2)

        # ROIC = NOPAT / Invested Capital
        if oi and tax and pretax and pretax > 0:
            tax_rate = abs(tax) / pretax
            nopat = oi * (1 - tax_rate)
            invested_capital = (te or 0) + (debt or 0) - (cash or 0)
            prev_ic = ((prev.get("total_equity") or prev.get("shareholders_equity") or 0) + (prev.get("total_debt") or 0) - (prev.get("cash") or 0)) if prev else None
            avg_ic = avg(invested_capital, prev_ic)
            if avg_ic and avg_ic > 0:
                m["roic"] = round(nopat / avg_ic * 100, 2)

        # Cash flow
        if ocf and capex:
            m["fcf_mm"] = round(ocf + capex, 1)
        if ocf and rev and rev > 0:
            m["ocf_margin"] = round(ocf / rev * 100, 2)
        if ocf and capex and rev and rev > 0:
            m["fcf_margin"] = round((ocf + capex) / rev * 100, 2)

        # Leverage
        if debt and te and te > 0:
            m["debt_to_equity"] = round(debt / te, 2)
        if debt and ta and ta > 0:
            m["debt_to_assets"] = round(debt / ta * 100, 2)
        if cash and debt:
            m["net_debt_mm"] = round(debt - cash, 1)
        if ca and cl and cl > 0:
            m["current_ratio"] = round(ca / cl, 2)

        # Per share
        m["eps_diluted"] = eps
        if ni and shares and shares > 0:
            m["bvps"] = round((se or te or 0) / shares, 2)
        m["shares_outstanding_mm"] = shares

        # Absolute values
        m["revenue_mm"] = rev
        m["operating_income_mm"] = oi
        m["net_income_mm"] = ni
        m["total_assets_mm"] = ta
        m["total_equity_mm"] = te
        m["total_debt_mm"] = debt
        m["ocf_mm"] = ocf

        # Clean nulls
        metrics[year] = {k: v for k, v in m.items() if v is not None}

    # Load existing output if present
    try:
        with open(output_path) as f:
            out_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        out_data = {}

    out_data.update({
        "ticker": ticker,
        "company_name": company_name,
        "cik": None,
        "data_source": f"Company IR website (converted from existing JSON), currency: {currency}",
        "financial_statements": {
            "income_statement": is_items,
            "balance_sheet": bs_items,
            "cash_flow_statement": cf_items,
        },
        "operating_metrics": metrics,
        "operating_metrics_notes": {
            "units": f"Absolute values in {units} {currency}, percentages as %",
            "source": f"Converted from {input_path}",
        }
    })

    with open(output_path, "w") as f:
        json.dump(out_data, f, indent=2, default=str)

    print(f"Saved: {output_path}")
    print(f"Years: {year_keys[0]}-{year_keys[-1]}")
    print("CONVERSION_COMPLETE")


if __name__ == "__main__":
    main()
