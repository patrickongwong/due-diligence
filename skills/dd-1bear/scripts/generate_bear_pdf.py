#!/usr/bin/env python3
"""
Bear Case One-Pager PDF Generator
Reads a JSON data file and produces a professional PDF with clickable source links.

Usage:
    python generate_bear_pdf.py <input.json> <output.pdf>

The JSON file should have this structure:
{
    "ticker": "AAPL",
    "company_name": "Apple Inc.",
    "date": "March 26, 2026",
    "price": "$252.62",
    "market_cap": "$3.71T",
    "metrics": [
        {"label": "Trailing P/E", "value": "31.9x", "is_bearish": true},
        ...
    ],
    "analysts": [
        {"name": "Edison Lee", "firm": "Jefferies", "date": "Oct 3, 2025",
         "rating": "Underperform", "pt": "$205", "downside": "-18.8%"},
        ...
    ],
    "theses": [
        {"number": "1", "title": "VALUATION: ...", "body": "...", "sources": [
            {"label": "CNBC: ...", "url": "https://..."},
            ...
        ]},
        ...
    ],
    "notable_bears": [
        {"who": "Warren Buffett", "when": "Q4 '23 - Q3 '25", "action": "Sold 74%",
         "argument": "Valuation stretched", "source_url": "https://...", "source_label": "CNBC"},
        ...
    ],
    "closing": "The bear case is not that..."
}
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '_shared'))
from auto_install import ensure_installed
ensure_installed('reportlab')

import json
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor, white
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether
)

# ── Colors ──
DARK_BG = HexColor("#1a1a2e")
ACCENT_RED = HexColor("#c0392b")
LIGHT_GRAY = HexColor("#f5f5f5")
MED_GRAY = HexColor("#e0e0e0")
TEXT_DARK = HexColor("#1a1a1a")
TEXT_MED = HexColor("#4a4a4a")
TEXT_LIGHT = HexColor("#6a6a6a")
LINK_BLUE = HexColor("#2471a3")
WHITE = white

# ── Styles ──
styles = {}
styles["title"] = ParagraphStyle(
    "title", fontName="Helvetica-Bold", fontSize=22, leading=26,
    textColor=WHITE, alignment=TA_LEFT)
styles["subtitle"] = ParagraphStyle(
    "subtitle", fontName="Helvetica", fontSize=10, leading=13,
    textColor=HexColor("#cccccc"), alignment=TA_LEFT)
styles["section_head"] = ParagraphStyle(
    "section_head", fontName="Helvetica-Bold", fontSize=11, leading=14,
    textColor=ACCENT_RED, spaceBefore=10, spaceAfter=4)
styles["body"] = ParagraphStyle(
    "body", fontName="Helvetica", fontSize=8.5, leading=11.5,
    textColor=TEXT_DARK, spaceBefore=0, spaceAfter=3)
styles["source"] = ParagraphStyle(
    "source", fontName="Helvetica", fontSize=7, leading=9,
    textColor=LINK_BLUE, spaceBefore=0, spaceAfter=1, leftIndent=10)
styles["kv_label"] = ParagraphStyle(
    "kv_label", fontName="Helvetica", fontSize=8, leading=10,
    textColor=TEXT_LIGHT, alignment=TA_CENTER)
styles["kv_value"] = ParagraphStyle(
    "kv_value", fontName="Helvetica-Bold", fontSize=12, leading=15,
    textColor=TEXT_DARK, alignment=TA_CENTER)
styles["kv_value_red"] = ParagraphStyle(
    "kv_value_red", fontName="Helvetica-Bold", fontSize=12, leading=15,
    textColor=ACCENT_RED, alignment=TA_CENTER)
styles["bear_name"] = ParagraphStyle(
    "bear_name", fontName="Helvetica-Bold", fontSize=8, leading=10,
    textColor=TEXT_DARK, spaceBefore=0, spaceAfter=0)
styles["bear_detail"] = ParagraphStyle(
    "bear_detail", fontName="Helvetica", fontSize=7.5, leading=10,
    textColor=TEXT_MED, spaceBefore=0, spaceAfter=0)
styles["footer"] = ParagraphStyle(
    "footer", fontName="Helvetica", fontSize=6.5, leading=8,
    textColor=TEXT_LIGHT, alignment=TA_CENTER)
styles["closing"] = ParagraphStyle(
    "closing", fontName="Helvetica-Oblique", fontSize=8.5, leading=11.5,
    textColor=TEXT_MED, spaceBefore=6, spaceAfter=2, leftIndent=10, rightIndent=10)


def make_link(url, text=None):
    display = text or url
    return f'<a href="{url}" color="#2471a3">{display}</a>'


def build_header(data):
    ticker = data["ticker"]
    title = Paragraph(f"{ticker} BEAR CASE", styles["title"])
    subtitle = Paragraph(
        f"The strongest arguments against {data['company_name']} from the smartest bears"
        f"&nbsp;&nbsp;|&nbsp;&nbsp;{data['date']}&nbsp;&nbsp;|&nbsp;&nbsp;"
        f"{data['price']}&nbsp;&nbsp;|&nbsp;&nbsp;Mkt Cap {data['market_cap']}",
        styles["subtitle"])
    t = Table([[title], [subtitle]], colWidths=[7.5 * inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), DARK_BG),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (0, 0), 10),
        ("BOTTOMPADDING", (0, 0), (0, 0), 2),
        ("TOPPADDING", (0, 1), (0, 1), 0),
        ("BOTTOMPADDING", (0, 1), (0, 1), 10),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    return t


def build_snapshot(metrics):
    mini_tables = []
    for m in metrics:
        val_style = styles["kv_value_red"] if m["is_bearish"] else styles["kv_value"]
        mt = Table(
            [[Paragraph(m["value"], val_style)], [Paragraph(m["label"], styles["kv_label"])]],
            colWidths=[0.9 * inch], rowHeights=[18, 12])
        mt.setStyle(TableStyle([
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]))
        mini_tables.append(mt)
    n = len(mini_tables) or 8
    snap = Table([mini_tables], colWidths=[7.5 * inch / n] * n)
    snap.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT_GRAY),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LINEAFTER", (0, 0), (-2, -1), 0.5, MED_GRAY),
    ]))
    return snap


def build_analyst_table(analysts):
    if not analysts:
        return Spacer(1, 0)
    header = [Paragraph(f"<b>{h}</b>", styles["body"])
              for h in ["Analyst", "Firm", "Date", "Rating", "PT", "Downside"]]
    rows = [header]
    for a in analysts:
        rating_text = a.get("rating", "")
        if any(kw in rating_text.lower() for kw in ["under", "sell", "reduce"]):
            rating_text = f"<font color='#c0392b'><b>{rating_text}</b></font>"
        else:
            rating_text = f"<b>{rating_text}</b>"
        downside = a.get("downside", "n/a")
        if downside.startswith("-"):
            downside = f"<font color='#c0392b'>{downside}</font>"
        rows.append([
            Paragraph(a.get("name", ""), styles["bear_detail"]),
            Paragraph(a.get("firm", ""), styles["bear_detail"]),
            Paragraph(a.get("date", ""), styles["bear_detail"]),
            Paragraph(rating_text, styles["bear_detail"]),
            Paragraph(a.get("pt", "n/a"), styles["bear_detail"]),
            Paragraph(downside, styles["bear_detail"]),
        ])
    t = Table(rows, colWidths=[1.15*inch, 1.25*inch, 0.9*inch, 1.4*inch, 0.6*inch, 2.2*inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), DARK_BG),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [LIGHT_GRAY, WHITE]),
        ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("GRID", (0, 0), (-1, -1), 0.5, MED_GRAY),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return t


def build_thesis_section(thesis):
    elements = []
    elements.append(Paragraph(f"{thesis['number']}. {thesis['title']}", styles["section_head"]))
    elements.append(Paragraph(thesis["body"], styles["body"]))
    for src in thesis.get("sources", []):
        elements.append(Paragraph(
            f"&rarr; {make_link(src['url'], src['label'])}", styles["source"]))
    elements.append(Spacer(1, 4))
    return KeepTogether(elements)


def build_notable_bears(bears):
    if not bears:
        return Spacer(1, 0)
    header = [Paragraph(f"<b>{h}</b>", styles["body"])
              for h in ["Who", "When", "Action", "Key Argument", "Source"]]
    rows = [header]
    for b in bears:
        rows.append([
            Paragraph(b.get("who", ""), styles["bear_name"]),
            Paragraph(b.get("when", ""), styles["bear_detail"]),
            Paragraph(b.get("action", ""), styles["bear_detail"]),
            Paragraph(b.get("argument", ""), styles["bear_detail"]),
            Paragraph(make_link(b.get("source_url", "#"), b.get("source_label", "Source")),
                      styles["source"]),
        ])
    t = Table(rows, colWidths=[1.2*inch, 0.9*inch, 1.2*inch, 2.7*inch, 1.5*inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), DARK_BG),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [LIGHT_GRAY, WHITE]),
        ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("GRID", (0, 0), (-1, -1), 0.5, MED_GRAY),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    return t


def generate_pdf(data, output_path):
    doc = SimpleDocTemplate(
        output_path, pagesize=letter,
        leftMargin=0.5*inch, rightMargin=0.5*inch,
        topMargin=0.4*inch, bottomMargin=0.4*inch)

    story = []

    # Header
    story.append(build_header(data))
    story.append(Spacer(1, 6))

    # Valuation snapshot
    if data.get("metrics"):
        story.append(build_snapshot(data["metrics"]))
        story.append(Spacer(1, 6))

    # Sell-side analysts
    if data.get("analysts"):
        story.append(Paragraph("BEARISH SELL-SIDE ANALYSTS", styles["section_head"]))
        story.append(build_analyst_table(data["analysts"]))
        story.append(Spacer(1, 2))

    # Bear theses
    if data.get("theses"):
        story.append(Paragraph("BEAR THESES BY RISK", styles["section_head"]))
        story.append(Spacer(1, 2))
        for thesis in data["theses"]:
            story.append(build_thesis_section(thesis))

    # Notable bears
    if data.get("notable_bears"):
        story.append(Spacer(1, 4))
        story.append(Paragraph("NOTABLE BEARS: WHO'S SELLING AND WHY", styles["section_head"]))
        story.append(build_notable_bears(data["notable_bears"]))

    # Closing
    if data.get("closing"):
        story.append(Spacer(1, 8))
        story.append(Paragraph(data["closing"], styles["closing"]))

    # Footer
    story.append(Spacer(1, 6))
    story.append(HRFlowable(width="100%", thickness=0.5, color=MED_GRAY))
    story.append(Spacer(1, 3))
    story.append(Paragraph(
        f"Compiled {data.get('date', 'today')} by Januarius Holdings Inc. "
        "All sources publicly available. This document is for informational purposes only "
        "and does not constitute investment advice. All links are clickable in this PDF.",
        styles["footer"]))

    doc.build(story)
    print(f"PDF saved to: {output_path}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python generate_bear_pdf.py <input.json> <output.pdf>")
        sys.exit(1)
    with open(sys.argv[1]) as f:
        data = json.load(f)
    generate_pdf(data, sys.argv[2])
