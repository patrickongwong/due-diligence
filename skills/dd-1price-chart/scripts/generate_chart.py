#!/usr/bin/env python3
"""
generate_chart.py -- Matplotlib chart rendering engine for dd-1price-chart skill.

Reads a JSON input file and produces a publication-quality annotated stock
price chart as a PNG.

Usage:
    python3 generate_chart.py /path/to/input.json
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '_shared'))
from auto_install import ensure_installed
ensure_installed('matplotlib')

import json
import sys
import math
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.dates import YearLocator, DateFormatter
import numpy as np


# ---------------------------------------------------------------------------
# 1. load_data
# ---------------------------------------------------------------------------

def load_data(json_path: str) -> dict:
    """Read the JSON input file and return a dict with parsed fields."""
    with open(json_path, "r") as f:
        raw = json.load(f)

    dates = [datetime.strptime(d, "%Y-%m-%d") for d in raw["dates_iso"]]
    prices = [float(p) for p in raw["prices"]]

    events = []
    for ev in raw.get("events", []):
        events.append({
            "date": datetime.strptime(ev["date"], "%Y-%m-%d"),
            "label": ev["label"],
        })

    return {
        "ticker": raw["ticker"],
        "company_name": raw["company_name"],
        "dates": dates,
        "prices": prices,
        "events": events,
        "log_scale": raw.get("log_scale", False),
        "output_path": raw["output_path"],
    }


# ---------------------------------------------------------------------------
# 2. compute_annotation_positions
# ---------------------------------------------------------------------------

def compute_annotation_positions(events, prices, dates, log_scale):
    """
    Assign 4-tier alternating vertical positions to event annotations.

    Cycle order:
        0 -> bottom-low   (further below)
        1 -> top-high      (further above)
        2 -> bottom-mid    (closer below)
        3 -> top-mid       (closer above)

    Returns a list of dicts with keys: date, label, text_y.
    """
    if not events or not prices:
        return []

    max_price = max(prices)
    min_price = min(p for p in prices if p > 0) if any(p > 0 for p in prices) else 1e-6

    if log_scale:
        top_high = max_price * 10
        top_mid = max_price * 3
        bot_mid = min_price * 0.3
        bot_low = min_price * 0.1
    else:
        price_range = max_price - min(prices)
        if price_range == 0:
            price_range = max_price if max_price > 0 else 1
        top_high = max_price + price_range * 0.25
        top_mid = max_price + price_range * 0.12
        bot_mid = -price_range * 0.15
        bot_low = -price_range * 0.28

    tier_cycle = [bot_low, top_high, bot_mid, top_mid]

    positioned = []
    for i, ev in enumerate(events):
        tier_idx = i % 4
        positioned.append({
            "date": ev["date"],
            "label": ev["label"],
            "text_y": tier_cycle[tier_idx],
        })

    return positioned


# ---------------------------------------------------------------------------
# 3. render_chart
# ---------------------------------------------------------------------------

def _nice_step(raw_step):
    """Snap a raw step size to the nearest 'nice' number."""
    nice_numbers = [
        0.01, 0.02, 0.05, 0.1, 0.2, 0.25, 0.5,
        1, 2, 2.5, 5, 10, 20, 25, 50, 100, 200, 250, 500,
        1000, 2000, 2500, 5000, 10000, 20000, 25000, 50000,
        100000, 200000, 250000, 500000, 1000000,
    ]
    best = nice_numbers[0]
    best_dist = abs(raw_step - best)
    for n in nice_numbers[1:]:
        dist = abs(raw_step - n)
        if dist < best_dist:
            best = n
            best_dist = dist
    return best


def render_chart(data: dict) -> str:
    """
    Render the annotated price chart and save as PNG.
    Returns the output path.
    """
    dates = data["dates"]
    prices = data["prices"]
    events = data["events"]
    log_scale = data["log_scale"]
    ticker = data["ticker"]
    company_name = data["company_name"]
    output_path = data["output_path"]

    max_price = max(prices)
    min_price = min(p for p in prices if p > 0) if any(p > 0 for p in prices) else 1e-6
    price_range = max_price - min(prices)
    if price_range == 0:
        price_range = max_price if max_price > 0 else 1

    start_year = dates[0].year
    end_year = dates[-1].year
    year_span = end_year - start_year

    # --- Annotation positions ---
    positioned_events = compute_annotation_positions(events, prices, dates, log_scale)

    # --- Figure ---
    fig, ax = plt.subplots(figsize=(26, 14))
    plt.subplots_adjust(left=0.12, right=0.95, top=0.90, bottom=0.10)

    # --- Price line ---
    ax.plot(dates, prices, color="#1a3a6e", linewidth=3.5, zorder=5)

    # --- Scale ---
    if log_scale:
        ax.set_yscale("log")
        ax.set_ylim(min_price * 0.05, max_price * 15)
    else:
        ax.set_ylim(-price_range * 0.35, max_price + price_range * 0.30)

    # --- Background ---
    ax.set_facecolor("white")
    fig.patch.set_facecolor("white")

    # --- No grid ---
    ax.grid(False)

    # --- Spines ---
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#999999")
    ax.spines["bottom"].set_color("#999999")

    # --- X-axis ---
    if year_span > 20:
        ax.xaxis.set_major_locator(YearLocator(5))
    elif year_span >= 10:
        ax.xaxis.set_major_locator(YearLocator(2))
    else:
        ax.xaxis.set_major_locator(YearLocator(1))
    ax.xaxis.set_minor_locator(YearLocator(1))
    ax.xaxis.set_major_formatter(DateFormatter("%Y"))

    x_start = datetime(start_year - 1, 1, 1)
    x_end = datetime(end_year + 1, 12, 31)
    ax.set_xlim(x_start, x_end)

    # --- Y-axis ticks ---
    if log_scale:
        # Generate ticks at 1, 2, 5 multiples of powers of 10
        y_lo, y_hi = min_price * 0.05, max_price * 15
        log_lo = math.floor(math.log10(max(y_lo, 1e-10)))
        log_hi = math.ceil(math.log10(max(y_hi, 1e-10)))
        ticks = []
        for exp in range(log_lo, log_hi + 1):
            for mult in [1, 2, 5]:
                val = mult * (10 ** exp)
                if y_lo <= val <= y_hi:
                    ticks.append(val)
        if ticks:
            ax.set_yticks(ticks)
            ax.yaxis.set_major_formatter(mticker.FuncFormatter(
                lambda v, _: f"${v:,.2f}" if v < 1 else (
                    f"${v:,.0f}" if v == int(v) else f"${v:,.2f}"
                )
            ))
    else:
        raw_step = max_price / 6
        step = _nice_step(raw_step)
        if step <= 0:
            step = 1
        y_lo_tick = 0
        y_hi_tick = (math.ceil(max_price / step) + 1) * step
        ticks = list(np.arange(y_lo_tick, y_hi_tick + step * 0.5, step))
        ax.set_yticks(ticks)
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(
            lambda v, _: f"${v:,.2f}" if v < 1 else (
                f"${v:,.0f}" if v == int(v) else f"${v:,.2f}"
            )
        ))

    # --- Fonts ---
    font_props = {"family": "serif", "weight": "bold"}

    ax.tick_params(axis="x", labelsize=20)
    ax.tick_params(axis="y", labelsize=20)
    for label in ax.get_xticklabels():
        label.set_fontfamily("serif")
        label.set_fontweight("bold")
    for label in ax.get_yticklabels():
        label.set_fontfamily("serif")
        label.set_fontweight("bold")

    # --- Title ---
    # Use "Price" for futures/commodities/indices, "Split-Adjusted Stock Price" for equities
    futures_suffixes = ("=F", "=X", "-USD")
    if any(ticker.upper().endswith(s) for s in futures_suffixes) or ticker.startswith("^"):
        price_label = "Price"
    else:
        price_label = "Split-Adjusted Stock Price"
    title_text = (
        f"{company_name} ({ticker}) {price_label}, "
        f"{start_year}\u2013{end_year}"
    )
    ax.set_title(title_text, fontsize=28, fontweight="bold", fontfamily="serif",
                 pad=20)

    # --- Annotations ---
    for ev in positioned_events:
        # Find the closest price for the arrow target
        closest_idx = 0
        closest_dist = abs((dates[0] - ev["date"]).days)
        for j, d in enumerate(dates):
            dist = abs((d - ev["date"]).days)
            if dist < closest_dist:
                closest_dist = dist
                closest_idx = j
        price_at_event = prices[closest_idx]

        ax.annotate(
            ev["label"],
            xy=(ev["date"], price_at_event),
            xytext=(ev["date"], ev["text_y"]),
            fontsize=14,
            fontweight="bold",
            fontfamily="serif",
            ha="center",
            va="center",
            arrowprops=dict(
                arrowstyle="-|>",
                lw=1.8,
                mutation_scale=16,
                color="#1a3a6e",
            ),
            zorder=10,
        )

    # --- Source line ---
    now = datetime.now()
    source_text = (
        f"Source: Yahoo Finance  |  {'Closing prices' if any(ticker.upper().endswith(s) for s in ('=F', '=X', '-USD')) or ticker.startswith('^') else 'Split-adjusted closing prices'}  |  "
        f"Data as of {now.strftime('%B')} {now.year}"
    )
    fig.text(
        0.5, 0.02, source_text,
        ha="center", fontsize=15, fontweight="bold", fontfamily="serif",
        color="#666666",
    )

    # --- Save ---
    fig.savefig(output_path, dpi=150, facecolor="white",
                bbox_inches="tight", pad_inches=0.6)
    plt.close(fig)

    return output_path


# ---------------------------------------------------------------------------
# 4. CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 generate_chart.py /path/to/input.json", file=sys.stderr)
        sys.exit(1)

    json_path = sys.argv[1]
    data = load_data(json_path)
    out = render_chart(data)
    print(f"Chart saved to: {out}")
