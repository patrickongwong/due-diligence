#!/usr/bin/env python3
"""
Compute operating metrics from extracted financial statement JSON.
Usage: python3 compute_metrics.py data.json [TICKER]

Reads financial_statements from the JSON, computes profitability, credit quality,
capital, funding, per-share metrics, and writes operating_metrics back to the same JSON.
Also attempts to extract regulatory capital and charge-off data from XBRL if available.
"""
import json
import sys
import traceback


def safe_div(a, b):
    if a is None or b is None or b == 0:
        return None
    return a / b


def safe_avg(a, b):
    if a is None and b is None:
        return None
    if a is None:
        return b
    if b is None:
        return a
    return (a + b) / 2


def lookup(items, label):
    if items is None:
        return None
    for item in items:
        if item["line_item"] == label:
            return item
    return None


def lookup_partial(items, partial, exclude=None):
    if items is None:
        return None
    for item in items:
        lbl = item["line_item"]
        if partial.lower() in lbl.lower():
            if exclude and any(ex.lower() in lbl.lower() for ex in exclude):
                continue
            return item
    return None


def get_val(item, year):
    if item is None:
        return None
    v = item.get(year)
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


def try_extract_xbrl_data(ticker, years):
    """Attempt to extract regulatory capital and charge-off data from XBRL facts."""
    xbrl_data = {}
    try:
        from edgar import Company, set_identity
        set_identity("Patrick Wong patrick@januariusholdings.com")
        company = Company(ticker)
        all_10k = company.get_filings(form="10-K")
        if len(all_10k) == 0:
            all_10k = company.get_filings(form="20-F")

        for idx in range(min(6, len(all_10k))):
            try:
                f = all_10k[idx]
                xbrl = f.xbrl()
                if xbrl is None:
                    continue
                facts_df = xbrl.facts
                if facts_df is None or len(facts_df) == 0:
                    continue

                # Search for regulatory capital concepts
                for _, row in facts_df.iterrows():
                    concept = str(row.get("concept", ""))
                    value = row.get("value")
                    period_end = str(row.get("end_date", row.get("period", "")))[:4]
                    if not period_end or period_end not in years:
                        continue

                    if period_end not in xbrl_data:
                        xbrl_data[period_end] = {}

                    concept_lower = concept.lower()
                    try:
                        num_val = float(value)
                    except (ValueError, TypeError):
                        continue

                    if "commonequitytier1" in concept_lower and "ratio" in concept_lower:
                        xbrl_data[period_end]["cet1_ratio"] = round(num_val * 100, 2) if num_val < 1 else round(num_val, 2)
                    elif "commonequitytier1" in concept_lower and "capital" in concept_lower:
                        xbrl_data[period_end]["cet1_capital_mm"] = round(num_val / 1e6)
                    elif "tier1" in concept_lower and "ratio" in concept_lower and "leverage" not in concept_lower:
                        xbrl_data[period_end]["tier1_ratio"] = round(num_val * 100, 2) if num_val < 1 else round(num_val, 2)
                    elif "tier1" in concept_lower and "capital" in concept_lower and "common" not in concept_lower:
                        xbrl_data[period_end]["tier1_capital_mm"] = round(num_val / 1e6)
                    elif "totalcapital" in concept_lower and "ratio" in concept_lower:
                        xbrl_data[period_end]["total_capital_ratio"] = round(num_val * 100, 2) if num_val < 1 else round(num_val, 2)
                    elif "chargeoff" in concept_lower and "gross" not in concept_lower and "recovery" not in concept_lower:
                        if "net" in concept_lower or "chargedoff" in concept_lower:
                            pass  # skip net, we compute it
                    elif "chargedoff" in concept_lower or ("writeoff" in concept_lower and "financing" in concept_lower):
                        xbrl_data[period_end]["gross_chargeoffs_mm"] = round(abs(num_val) / 1e6)
                    elif "recoveriesof" in concept_lower and "financing" in concept_lower:
                        xbrl_data[period_end]["recoveries_mm"] = round(abs(num_val) / 1e6)

            except Exception:
                continue

    except Exception as e:
        print(f"  XBRL enrichment failed: {e}")

    return xbrl_data


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 compute_metrics.py data.json [TICKER]")
        sys.exit(1)

    json_path = sys.argv[1]
    ticker_override = sys.argv[2].upper() if len(sys.argv) > 2 else None

    with open(json_path) as f:
        data = json.load(f)

    ticker = ticker_override or data.get("ticker", "UNKNOWN")
    fs = data.get("financial_statements", {})
    is_items = fs.get("income_statement", [])
    bs_items = fs.get("balance_sheet", [])
    cf_items = fs.get("cash_flow_statement", [])

    # Determine all years
    all_years = set()
    for items in [is_items, bs_items, cf_items]:
        if items:
            for item in items:
                all_years.update(k for k in item.keys() if k != "line_item" and k.isdigit())
    years = sorted(all_years)
    print(f"Computing metrics for {ticker}, years: {years}")

    # Extract key line items
    def find(items, *labels):
        for label in labels:
            item = lookup(items, label)
            if item:
                return item
        return None

    def find_p(items, partial, **kwargs):
        return lookup_partial(items, partial, **kwargs)

    # Income statement items
    net_income_item = find(is_items, "Net income")
    net_income_common_item = find(is_items, "Net income attributable to common shareholders", "Net income attributable to common stockholders")
    total_revenue_item = find(is_items, "Total net revenue", "Total revenue", "Revenue")
    nii_item = find(is_items, "Net financing revenue and other interest income", "Net interest income")
    ni_income_item = find(is_items, "Total other revenue", "Total noninterest income", "Noninterest income")
    nie_item = find(is_items, "Total noninterest expense")
    provision_item = find(is_items, "Provision for credit losses")
    pretax_item = find(is_items, "Income from continuing operations before income tax expense", "Income before income tax expense", "Income before provision for income taxes")
    tax_item = find(is_items, "Total income tax expense from continuing operations", "Income tax expense")
    int_income_item = find(is_items, "Total financing revenue and other interest income", "Total interest income")
    int_expense_item = find(is_items, "Total interest expense")
    int_on_deposits_item = find(is_items, "Interest on deposits")
    int_on_loans_item = find(is_items, "Interest and fees on finance receivables and loans", "Interest and fees on loans")
    insurance_premiums_item = find(is_items, "Insurance premiums and service revenue earned")
    insurance_losses_item = find(is_items, "Insurance losses and loss adjustment expenses")
    comp_item = find(is_items, "Compensation and benefits expense")
    other_opex_item = find(is_items, "Other operating expenses")
    ops_lease_rev_item = find(is_items, "Operating leases")
    ops_lease_dep_item = find(is_items, "Net depreciation expense on operating lease assets")
    eps_item = find(is_items, "Net income (in dollars per share)")
    if not eps_item:
        eps_item = find_p(is_items, "diluted earnings per common share")
    dps_item = find(is_items, "Cash dividends declared per common share (in dollars per share)")
    if not dps_item:
        dps_item = find(is_items, "Cash dividends declared per common share")
    diluted_shares_item = find(is_items, "Diluted weighted-average common shares outstanding (in shares)")

    # Balance sheet items
    total_assets_item = find(bs_items, "Total assets")
    total_equity_item = find(bs_items, "Total equity", "Total stockholders' equity")
    total_liab_item = find(bs_items, "Total liabilities")
    total_deposits_item = find(bs_items, "Total deposit liabilities", "Total deposits")
    total_loans_net_item = find(bs_items, "Total finance receivables and loans, net", "Total loans, net")
    gross_loans_item = find(bs_items, "Finance receivables and loans, net of unearned income")
    allowance_item = find(bs_items, "Allowance for loan losses", "Allowance for credit losses")
    preferred_item = find(bs_items, "Preferred stock")
    aoci_item = find(bs_items, "Accumulated other comprehensive loss", "Accumulated other comprehensive income (loss)")
    retained_item = find(bs_items, "Retained earnings")
    lt_debt_item = find(bs_items, "Long-term debt")
    st_borr_item = find(bs_items, "Short-term borrowings")

    # Cash flow items
    cf_divs_item = find(cf_items, "Common stock dividends paid", "Dividends paid")
    cf_pref_divs_item = find(cf_items, "Preferred stock dividends paid")
    cf_buybacks_item = find(cf_items, "Repurchases of common stock", "Repurchase of common stock")

    # Try XBRL enrichment for regulatory capital and charge-offs
    print("Attempting XBRL enrichment for regulatory capital and charge-offs...")
    xbrl_data = try_extract_xbrl_data(ticker, years)

    # Compute metrics for each year
    operating_metrics = {}
    raw_data = {}

    for i, year in enumerate(years):
        m = {}
        rd = {}

        # Raw values
        ni = get_val(net_income_item, year)
        ni_common = get_val(net_income_common_item, year)
        total_rev = get_val(total_revenue_item, year)
        nii = get_val(nii_item, year)
        ni_income = get_val(ni_income_item, year)
        nie = get_val(nie_item, year)
        provision = get_val(provision_item, year)
        pretax = get_val(pretax_item, year)
        tax = get_val(tax_item, year)
        int_income = get_val(int_income_item, year)
        int_expense = get_val(int_expense_item, year)
        int_deposits = get_val(int_on_deposits_item, year)
        int_loans = get_val(int_on_loans_item, year)
        ta = get_val(total_assets_item, year)
        te = get_val(total_equity_item, year)
        tl = get_val(total_liab_item, year)
        deposits = get_val(total_deposits_item, year)
        loans_net = get_val(total_loans_net_item, year)
        gross_loans = get_val(gross_loans_item, year)
        allowance = get_val(allowance_item, year)
        preferred = get_val(preferred_item, year)
        eps_val = get_val(eps_item, year)
        dps_val = get_val(dps_item, year)
        diluted_shares = get_val(diluted_shares_item, year)
        ins_prem = get_val(insurance_premiums_item, year)
        ins_loss = get_val(insurance_losses_item, year)
        ops_lease_rev = get_val(ops_lease_rev_item, year)
        ops_lease_dep = get_val(ops_lease_dep_item, year)
        divs_paid = get_val(cf_divs_item, year)
        pref_divs = get_val(cf_pref_divs_item, year)
        buybacks = get_val(cf_buybacks_item, year)

        # Previous year values for averages
        prev_year = years[i - 1] if i > 0 else None
        prev_ta = get_val(total_assets_item, prev_year) if prev_year else None
        prev_te = get_val(total_equity_item, prev_year) if prev_year else None
        prev_loans = get_val(total_loans_net_item, prev_year) if prev_year else None
        prev_deposits = get_val(total_deposits_item, prev_year) if prev_year else None

        avg_ta = safe_avg(ta, prev_ta)
        avg_te = safe_avg(te, prev_te)
        avg_loans = safe_avg(loans_net, prev_loans)
        avg_deposits = safe_avg(deposits, prev_deposits)

        # Absolute expense values
        nie_abs = abs(nie) if nie else None
        int_exp_abs = abs(int_expense) if int_expense else None
        tax_abs = abs(tax) if tax else None

        # NII (might be stored directly or need computing)
        if nii is None and int_income and int_expense:
            nii = int_income + int_expense  # int_expense is negative

        # Total revenue
        if total_rev is None and nii and ni_income:
            total_rev = nii + ni_income

        # Noninterest income
        if ni_income is None and total_rev and nii:
            ni_income = total_rev - nii

        # ── Profitability ──
        m["roe"] = round(safe_div(ni, avg_te) * 100, 2) if safe_div(ni, avg_te) else None
        m["roa"] = round(safe_div(ni, avg_ta) * 100, 2) if safe_div(ni, avg_ta) else None

        # ROTCE: use (equity - preferred) as TCE
        tce = (te - (preferred or 0)) if te is not None else None
        prev_tce = None
        if prev_te is not None:
            prev_pref = get_val(preferred_item, prev_year) if prev_year else 0
            prev_tce = prev_te - (prev_pref or 0)
        avg_tce = safe_avg(tce, prev_tce)
        ni_for_tce = ni_common if ni_common else ni
        m["rotce"] = round(safe_div(ni_for_tce, avg_tce) * 100, 2) if safe_div(ni_for_tce, avg_tce) else None

        m["nim_pct"] = round(safe_div(nii, avg_ta) * 100, 2) if safe_div(nii, avg_ta) and nii else None

        # Efficiency ratio: NIE / (NII + NI Income) or NIE / Total Rev
        if nie_abs and total_rev and total_rev > 0:
            m["efficiency_ratio"] = round(nie_abs / total_rev * 100, 2)
        else:
            m["efficiency_ratio"] = None

        m["effective_tax_rate"] = round(safe_div(tax_abs, pretax) * 100, 2) if safe_div(tax_abs, pretax) else None

        # ── PPNR ──
        ppnr = (total_rev - nie_abs) if total_rev and nie_abs else None
        m["ppnr_mm"] = round(ppnr / 1e6) if ppnr else None
        m["ppnr_to_assets"] = round(safe_div(ppnr, avg_ta) * 100, 2) if safe_div(ppnr, avg_ta) and ppnr else None

        # ── Yields & Spreads ──
        m["yield_on_earning_assets"] = round(safe_div(int_income, avg_ta) * 100, 2) if safe_div(int_income, avg_ta) and int_income else None
        m["yield_on_loans"] = round(safe_div(int_loans, avg_loans) * 100, 2) if safe_div(int_loans, avg_loans) and int_loans else None
        m["cost_of_deposits"] = round(safe_div(int_deposits, avg_deposits) * 100, 2) if safe_div(int_deposits, avg_deposits) and int_deposits else None
        m["cost_of_funds"] = round(safe_div(int_exp_abs, avg_ta) * 100, 2) if safe_div(int_exp_abs, avg_ta) and int_exp_abs else None

        if m.get("yield_on_earning_assets") and m.get("cost_of_funds"):
            m["net_interest_spread"] = round(m["yield_on_earning_assets"] - m["cost_of_funds"], 2)
        else:
            m["net_interest_spread"] = None

        # ── Credit Quality ──
        m["provision_mm"] = round(provision / 1e6) if provision else None
        m["provision_to_loans"] = round(safe_div(provision, avg_loans) * 100, 2) if safe_div(provision, avg_loans) and provision else None
        m["allowance_to_loans"] = round(safe_div(abs(allowance), abs(gross_loans or loans_net or 0)) * 100, 2) if allowance and (gross_loans or loans_net) else None

        # XBRL enrichment
        xd = xbrl_data.get(year, {})
        for xkey in ["cet1_ratio", "cet1_capital_mm", "tier1_ratio", "tier1_capital_mm", "total_capital_ratio",
                      "gross_chargeoffs_mm", "recoveries_mm"]:
            if xkey in xd:
                m[xkey] = xd[xkey]

        # Net charge-offs from XBRL
        if "gross_chargeoffs_mm" in m and "recoveries_mm" in m:
            m["net_chargeoffs_mm"] = m["gross_chargeoffs_mm"] - m["recoveries_mm"]
            m["nco_ratio"] = round(safe_div(m["net_chargeoffs_mm"] * 1e6, avg_loans) * 100, 2) if avg_loans else None

        # ── Balance Sheet ──
        m["total_assets_mm"] = round(ta / 1e6) if ta else None
        m["total_loans_net_mm"] = round(loans_net / 1e6) if loans_net else None
        m["total_deposits_mm"] = round(deposits / 1e6) if deposits else None
        m["total_equity_mm"] = round(te / 1e6) if te else None

        # ── Funding & Leverage ──
        m["loan_to_deposit"] = round(safe_div(loans_net, deposits) * 100, 2) if safe_div(loans_net, deposits) and loans_net else None
        m["deposits_to_liabilities"] = round(safe_div(deposits, tl) * 100, 2) if safe_div(deposits, tl) and deposits else None
        m["leverage_ratio"] = round(safe_div(te, ta) * 100, 2) if safe_div(te, ta) and te else None

        # ── Revenue composition ──
        m["net_interest_income_mm"] = round(nii / 1e6) if nii else None
        m["noninterest_income_mm"] = round(ni_income / 1e6) if ni_income else None
        m["total_net_revenue_mm"] = round(total_rev / 1e6) if total_rev else None
        m["noninterest_expense_mm"] = round(nie_abs / 1e6) if nie_abs else None
        m["net_income_mm"] = round(ni / 1e6) if ni else None

        # ── Insurance ──
        if ins_prem and ins_loss:
            m["insurance_loss_ratio"] = round(ins_loss / ins_prem * 100, 2)
        if ops_lease_rev and ops_lease_dep:
            m["operating_lease_net_revenue"] = ops_lease_rev + ops_lease_dep

        # ── Per Share ──
        m["eps_diluted"] = eps_val
        m["dps"] = dps_val

        # BVPS
        shares_out = diluted_shares
        if not shares_out:
            # Try to compute from EPS
            if eps_val and ni and eps_val != 0:
                shares_out = ni / eps_val
        m["diluted_shares_mm"] = round(diluted_shares / 1e6, 1) if diluted_shares else None

        if te and shares_out and shares_out > 0:
            m["bvps"] = round(te / shares_out, 2)
            tce_for_bvps = te - (preferred or 0)
            m["tbvps"] = round(tce_for_bvps / shares_out, 2)
        m["shares_outstanding_mm"] = round(shares_out / 1e6, 1) if shares_out else None

        # ── Capital Return ──
        buybacks_abs = abs(buybacks) if buybacks else 0
        m["buybacks_mm"] = round(buybacks_abs / 1e6) if buybacks_abs else None

        if dps_val and eps_val and eps_val != 0:
            m["dividend_payout_ratio"] = round(dps_val / eps_val * 100, 2)
        if ni and ni > 0:
            total_return = (abs(divs_paid) if divs_paid else 0) + buybacks_abs
            m["total_payout_ratio"] = round(total_return / ni * 100, 2)

        # Clean out None values for compactness
        operating_metrics[year] = {k: v for k, v in m.items() if v is not None}

    # Save back to JSON
    data["operating_metrics"] = operating_metrics
    data["operating_metrics_notes"] = {
        "units": "Percentages shown as %, absolute values in millions USD (suffix _mm), per-share in dollars",
        "nim_approximation": "NIM approximated as NII / Avg Total Assets",
        "tce_approximation": "TCE = Total Equity - Preferred Stock",
        "capital_ratios": "CET1/Tier1/Total Capital ratios from XBRL regulatory facts if available",
    }

    with open(json_path, "w") as f:
        json.dump(data, f, indent=2, default=str)

    print(f"Saved metrics to {json_path}")
    print(f"Years with metrics: {list(operating_metrics.keys())}")
    print("METRICS_COMPLETE")


if __name__ == "__main__":
    main()
