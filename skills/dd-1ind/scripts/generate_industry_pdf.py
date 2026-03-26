#!/usr/bin/env python3
"""
Industry Analysis One-Pager PDF Generator
Reads a JSON data file and produces a professional PDF with clickable source links.

Usage:
    python generate_industry_pdf.py <input.json> <output.pdf>

The JSON file should have this structure:
{
    "ticker": "NVDA",
    "company_name": "NVIDIA Corporation",
    "industry": "Semiconductors — GPU & AI Accelerators",
    "date": "March 26, 2026",
    "price": "$120.50",
    "market_cap": "$2.95T",
    "revenue_ttm": "$130.5B",
    "industry_overview": {
        "market_size": "$250B",
        "market_size_year": "2025",
        "growth_rate": "15% CAGR",
        "num_major_players": 6,
        "sources": [{"label": "...", "url": "..."}]
    },
    "market_share": {
        "players": [
            {
                "company": "NVIDIA",
                "ticker": "NVDA",
                "share_current": "80%",
                "share_history": [
                    {"year": "2022", "share": "65%"},
                    {"year": "2023", "share": "72%"},
                    {"year": "2024", "share": "78%"},
                    {"year": "2025", "share": "80%"}
                ],
                "trend": "gaining",
                "revenue_ttm": "$130.5B"
            }
        ],
        "narrative": "Market share narrative text...",
        "sources": [{"label": "...", "url": "..."}]
    },
    "whos_winning": [
        {
            "company": "NVIDIA",
            "narrative": "Gladwell-style paragraph about this competitor...",
            "sources": [{"label": "...", "url": "..."}]
        }
    ],
    "silver_bullets": [
        {
            "shooter": "NVIDIA",
            "target": "AMD",
            "reasoning": "Because AMD is the only credible alternative..."
        }
    ],
    "silver_bullets_sources": [{"label": "...", "url": "..."}],
    "ecosystem": {
        "suppliers": [
            {"name": "TSMC", "supplies": "Chip fabrication", "risk": "High — sole advanced node fab"}
        ],
        "customers": [
            {"name": "Hyperscalers (AWS, Azure, GCP)", "pct_revenue": "~50%", "trend": "Growing"}
        ],
        "regulations": [
            {"name": "US Export Controls (Oct 2022, Oct 2023)", "impact": "Restricts sales to China", "status": "Active, tightening"}
        ],
        "suppliers_sources": [{"label": "...", "url": "..."}],
        "customers_sources": [{"label": "...", "url": "..."}],
        "regulations_sources": [{"label": "...", "url": "..."}]
    },
    "tailwinds": ["AI infrastructure buildout", "..."],
    "headwinds": ["Export controls on China", "..."],
    "tailwinds_headwinds_sources": [{"label": "...", "url": "..."}]
}
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '_shared'))
from auto_install import ensure_installed
ensure_installed('reportlab')

import json
from xml.sax.saxutils import escape as xml_escape
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor, white
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether, PageBreak
)

# ── Colors ──
DARK_BG = HexColor("#16213e")
ACCENT_BLUE = HexColor("#0f3460")
ACCENT_TEAL = HexColor("#1a936f")
ACCENT_RED = HexColor("#c0392b")
LIGHT_GRAY = HexColor("#f5f5f5")
MED_GRAY = HexColor("#e0e0e0")
DARK_GRAY = HexColor("#555555")
TEXT_DARK = HexColor("#1a1a1a")
TEXT_MED = HexColor("#4a4a4a")
TEXT_LIGHT = HexColor("#6a6a6a")
LINK_BLUE = HexColor("#2471a3")
GREEN = HexColor("#27ae60")
WHITE = white

# ── Styles ──
styles = {}
styles["title"] = ParagraphStyle(
    "title", fontName="Helvetica-Bold", fontSize=20, leading=24,
    textColor=WHITE, alignment=TA_LEFT)
styles["subtitle"] = ParagraphStyle(
    "subtitle", fontName="Helvetica", fontSize=9, leading=12,
    textColor=HexColor("#bbbbbb"), alignment=TA_LEFT)
styles["section_head"] = ParagraphStyle(
    "section_head", fontName="Helvetica-Bold", fontSize=11, leading=14,
    textColor=ACCENT_BLUE, spaceBefore=10, spaceAfter=4)
styles["subsection_head"] = ParagraphStyle(
    "subsection_head", fontName="Helvetica-Bold", fontSize=9, leading=12,
    textColor=DARK_GRAY, spaceBefore=6, spaceAfter=2)
styles["body"] = ParagraphStyle(
    "body", fontName="Helvetica", fontSize=8.5, leading=11.5,
    textColor=TEXT_DARK, spaceBefore=0, spaceAfter=3)
styles["body_italic"] = ParagraphStyle(
    "body_italic", fontName="Helvetica-Oblique", fontSize=8.5, leading=11.5,
    textColor=TEXT_MED, spaceBefore=0, spaceAfter=3)
styles["source"] = ParagraphStyle(
    "source", fontName="Helvetica", fontSize=7, leading=9,
    textColor=LINK_BLUE, spaceBefore=0, spaceAfter=1, leftIndent=10)
styles["table_header"] = ParagraphStyle(
    "table_header", fontName="Helvetica-Bold", fontSize=7.5, leading=10,
    textColor=WHITE)
styles["table_cell"] = ParagraphStyle(
    "table_cell", fontName="Helvetica", fontSize=7.5, leading=10,
    textColor=TEXT_DARK)
styles["table_cell_bold"] = ParagraphStyle(
    "table_cell_bold", fontName="Helvetica-Bold", fontSize=7.5, leading=10,
    textColor=TEXT_DARK)
styles["kv_label"] = ParagraphStyle(
    "kv_label", fontName="Helvetica", fontSize=7.5, leading=10,
    textColor=TEXT_LIGHT, alignment=TA_CENTER)
styles["kv_value"] = ParagraphStyle(
    "kv_value", fontName="Helvetica-Bold", fontSize=11, leading=14,
    textColor=TEXT_DARK, alignment=TA_CENTER)
styles["bullet"] = ParagraphStyle(
    "bullet", fontName="Helvetica", fontSize=8, leading=11,
    textColor=TEXT_DARK, leftIndent=15, bulletIndent=5)
styles["footer"] = ParagraphStyle(
    "footer", fontName="Helvetica", fontSize=6.5, leading=8,
    textColor=TEXT_LIGHT, alignment=TA_CENTER)
styles["silver_shooter"] = ParagraphStyle(
    "silver_shooter", fontName="Helvetica-Bold", fontSize=8, leading=10,
    textColor=ACCENT_BLUE)
styles["silver_target"] = ParagraphStyle(
    "silver_target", fontName="Helvetica-Bold", fontSize=8, leading=10,
    textColor=ACCENT_RED)
styles["silver_reason"] = ParagraphStyle(
    "silver_reason", fontName="Helvetica", fontSize=7.5, leading=10,
    textColor=TEXT_MED)


def safe_text(text):
    """Escape XML-special characters so ReportLab Paragraphs render safely."""
    if not text:
        return ""
    return xml_escape(str(text))


def make_link(url, text=None):
    display = text or url
    return f'<a href="{url}" color="#2471a3">{display}</a>'


def build_header(data):
    ticker = data["ticker"]
    title = Paragraph(f"{ticker} INDUSTRY ANALYSIS", styles["title"])
    parts = [data.get("company_name", "")]
    if data.get("industry"):
        parts.append(data["industry"])
    parts.append(data.get("date", ""))
    parts.append(data.get("price", ""))
    parts.append(f"Mkt Cap {data.get('market_cap', '')}")
    subtitle = Paragraph("&nbsp;&nbsp;|&nbsp;&nbsp;".join(parts), styles["subtitle"])
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


def build_overview_strip(overview):
    items = [
        ("Market Size", overview.get("market_size", "N/A")),
        ("Year", overview.get("market_size_year", "N/A")),
        ("Growth Rate", overview.get("growth_rate", "N/A")),
        ("Major Players", str(overview.get("num_major_players", "N/A"))),
    ]
    cells = []
    for label, value in items:
        cell = Table(
            [[Paragraph(value, styles["kv_value"])],
             [Paragraph(label, styles["kv_label"])]],
            colWidths=[1.85 * inch], rowHeights=[18, 12])
        cell.setStyle(TableStyle([
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]))
        cells.append(cell)
    strip = Table([cells], colWidths=[1.875 * inch] * 4)
    strip.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT_GRAY),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LINEAFTER", (0, 0), (-2, -1), 0.5, MED_GRAY),
    ]))
    return strip


def build_share_bar(share_str):
    """Create a simple text-based bar for market share."""
    try:
        pct = float(share_str.replace("%", "").strip())
        filled = int(pct / 5)  # each block = 5%
        bar = "\u2588" * filled + "\u2591" * (20 - filled)
        return f"{bar} {share_str}"
    except (ValueError, AttributeError):
        return share_str or "N/A"


def build_market_share_table(market_share):
    players = market_share.get("players", [])
    if not players:
        return Spacer(1, 0)

    # Build header
    header = [Paragraph(f"<b>{h}</b>", styles["table_header"])
              for h in ["Company", "Share", "Trend", "Rev (TTM)", "Share History"]]
    rows = [header]

    for p in players:
        # Build mini history string
        history = p.get("share_history", [])
        hist_str = " → ".join([f"{h['year']}: {h['share']}" for h in history[-4:]]) if history else "—"

        trend = p.get("trend", "")
        if trend.lower() == "gaining":
            trend_display = f'<font color="#27ae60"><b>▲ {trend}</b></font>'
        elif trend.lower() == "losing":
            trend_display = f'<font color="#c0392b"><b>▼ {trend}</b></font>'
        else:
            trend_display = f"<b>● {trend}</b>"

        rows.append([
            Paragraph(f"<b>{p.get('company', '')}</b> ({p.get('ticker', '')})", styles["table_cell"]),
            Paragraph(f"<b>{p.get('share_current', 'N/A')}</b>", styles["table_cell_bold"]),
            Paragraph(trend_display, styles["table_cell"]),
            Paragraph(p.get("revenue_ttm", "N/A"), styles["table_cell"]),
            Paragraph(hist_str, styles["table_cell"]),
        ])

    col_widths = [1.6*inch, 0.7*inch, 0.8*inch, 0.8*inch, 3.6*inch]
    t = Table(rows, colWidths=col_widths)
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


def build_sources(sources):
    elements = []
    for src in (sources or []):
        elements.append(Paragraph(
            f"&rarr; {make_link(src['url'], src['label'])}", styles["source"]))
    return elements


def build_whos_winning(entries):
    elements = []
    for entry in entries:
        elements.append(Paragraph(
            f"<b>{entry['company']}</b>", styles["subsection_head"]))
        elements.append(Paragraph(entry.get("narrative", ""), styles["body"]))
        elements.extend(build_sources(entry.get("sources", [])))
        elements.append(Spacer(1, 2))
    return elements


def build_silver_bullets_table(bullets):
    if not bullets:
        return Spacer(1, 0)

    header = [Paragraph(f"<b>{h}</b>", styles["table_header"])
              for h in ["Player", "Would Eliminate", "Why"]]
    rows = [header]
    for b in bullets:
        rows.append([
            Paragraph(f"<b>{b.get('shooter', '')}</b>", styles["table_cell_bold"]),
            Paragraph(f"<font color='#c0392b'><b>{b.get('target', '')}</b></font>", styles["table_cell"]),
            Paragraph(b.get("reasoning", ""), styles["table_cell"]),
        ])

    t = Table(rows, colWidths=[1.3*inch, 1.3*inch, 4.9*inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), DARK_BG),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [LIGHT_GRAY, WHITE]),
        ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("GRID", (0, 0), (-1, -1), 0.5, MED_GRAY),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    return t


def build_ecosystem_table(items, columns, col_widths):
    if not items:
        return Spacer(1, 0)

    header = [Paragraph(f"<b>{h}</b>", styles["table_header"]) for h in columns]
    rows = [header]
    for item in items:
        row = []
        for col in columns:
            key = col.lower().replace(" ", "_").replace("%", "pct")
            # Try common key mappings
            val = ""
            if col == "Name" or col == "Supplier" or col == "Customer/Segment":
                val = item.get("name", item.get("supplier", item.get("customer", "")))
            elif col == "Supplies" or col == "What They Supply":
                val = item.get("supplies", item.get("what_they_supply", ""))
            elif col == "Risk" or col == "Concentration Risk":
                val = item.get("risk", item.get("concentration_risk", ""))
            elif col == "% of Revenue" or col == "% Rev":
                val = item.get("pct_revenue", item.get("pct_of_revenue", ""))
            elif col == "Trend":
                val = item.get("trend", "")
            elif col == "Regulation":
                val = item.get("name", item.get("regulation", ""))
            elif col == "Impact":
                val = item.get("impact", "")
            elif col == "Status":
                val = item.get("status", "")
            else:
                val = item.get(key, "")
            row.append(Paragraph(str(val), styles["table_cell"]))
        rows.append(row)

    t = Table(rows, colWidths=col_widths)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), ACCENT_BLUE),
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


def build_timeline_table(timeline):
    if not timeline:
        return Spacer(1, 0)
    header = [Paragraph(f"<b>{h}</b>", styles["table_header"])
              for h in ["Year", "Event", "Significance"]]
    rows = [header]
    for t in timeline:
        rows.append([
            Paragraph(f"<b>{safe_text(t.get('year', ''))}</b>", styles["table_cell_bold"]),
            Paragraph(safe_text(t.get("event", "")), styles["table_cell"]),
            Paragraph(safe_text(t.get("significance", "")), styles["table_cell"]),
        ])
    t = Table(rows, colWidths=[0.8*inch, 3.35*inch, 3.35*inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), DARK_BG),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [LIGHT_GRAY, WHITE]),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("GRID", (0, 0), (-1, -1), 0.5, MED_GRAY),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    return t


def build_tailwinds_headwinds(tailwinds, headwinds):
    elements = []

    if tailwinds:
        tw_items = []
        for tw in tailwinds:
            tw_items.append(Paragraph(
                f'<font color="#27ae60"><b>▲</b></font> {tw}', styles["bullet"]))
        elements.extend(tw_items)

    if headwinds:
        hw_items = []
        for hw in headwinds:
            hw_items.append(Paragraph(
                f'<font color="#c0392b"><b>▼</b></font> {hw}', styles["bullet"]))
        elements.extend(hw_items)

    return elements


def generate_pdf(data, output_path):
    doc = SimpleDocTemplate(
        output_path, pagesize=letter,
        leftMargin=0.5*inch, rightMargin=0.5*inch,
        topMargin=0.4*inch, bottomMargin=0.4*inch)

    story = []

    # ── Header ──
    story.append(build_header(data))
    story.append(Spacer(1, 6))

    # ── Industry Overview Strip ──
    overview = data.get("industry_overview", {})
    if overview:
        story.append(build_overview_strip(overview))
        story.append(Spacer(1, 4))
        story.extend(build_sources(overview.get("sources", [])))
        story.append(Spacer(1, 4))

    # ── What Is This Industry? ──
    industry_explanation = data.get("industry_explanation", "")
    if industry_explanation:
        story.append(Paragraph("WHAT IS THIS INDUSTRY?", styles["section_head"]))
        # Split into paragraphs for readability
        for para in industry_explanation.split("\n\n"):
            if para.strip():
                story.append(Paragraph(safe_text(para.strip()), styles["body"]))
        story.extend(build_sources(data.get("industry_explanation_sources", [])))
        story.append(Spacer(1, 4))

    # ── Industry History ──
    history_narrative = data.get("history_narrative", "")
    if history_narrative:
        story.append(Paragraph("INDUSTRY HISTORY", styles["section_head"]))
        for para in history_narrative.split("\n\n"):
            if para.strip():
                # Handle bold section headers
                p = para.strip()
                if p.startswith("**") and p.endswith("**"):
                    story.append(Paragraph(f"<b>{safe_text(p.strip('*'))}</b>", styles["subsection_head"]))
                else:
                    story.append(Paragraph(safe_text(p), styles["body"]))
        story.extend(build_sources(data.get("history_sources", [])))
        story.append(Spacer(1, 4))

    # ── Timeline ──
    timeline = data.get("timeline", [])
    if timeline:
        story.append(Paragraph("KEY MILESTONES", styles["section_head"]))
        story.append(build_timeline_table(timeline))
        story.append(Spacer(1, 4))

    # ── Private / Non-Public Competitors ──
    private_competitors = data.get("private_competitors", [])
    if private_competitors:
        story.append(Paragraph("PRIVATE & PE COMPETITORS", styles["section_head"]))
        for entry in private_competitors:
            company = entry.get("company", "")
            comp_type = entry.get("type", "")
            label = f"<b>{company}</b> ({comp_type})" if comp_type else f"<b>{company}</b>"
            story.append(Paragraph(label, styles["subsection_head"]))
            story.append(Paragraph(entry.get("narrative", ""), styles["body"]))
            story.extend(build_sources(entry.get("sources", [])))
            story.append(Spacer(1, 2))
        story.append(Spacer(1, 4))

    # ── Market Share ──
    market_share = data.get("market_share", {})
    if market_share:
        story.append(Paragraph("MARKET SHARE LANDSCAPE", styles["section_head"]))
        story.append(build_market_share_table(market_share))
        story.append(Spacer(1, 3))
        if market_share.get("narrative"):
            story.append(Paragraph(market_share["narrative"], styles["body"]))
        story.extend(build_sources(market_share.get("sources", [])))
        story.append(Spacer(1, 4))

    # ── Who's Winning ──
    whos_winning = data.get("whos_winning", [])
    if whos_winning:
        story.append(Paragraph("WHO'S WINNING — AND WHY", styles["section_head"]))
        story.extend(build_whos_winning(whos_winning))
        story.append(Spacer(1, 4))

    # ── Silver Bullet ──
    silver_bullets = data.get("silver_bullets", [])
    if silver_bullets:
        story.append(Paragraph(
            "THE SILVER BULLET — WHO WOULD EACH PLAYER ELIMINATE?",
            styles["section_head"]))
        story.append(Paragraph(
            "If each major player had one silver bullet — one competitor they could permanently "
            "remove from the industry — who would they aim at? The answer reveals where the "
            "real competitive tensions lie.",
            styles["body_italic"]))
        story.append(Spacer(1, 3))
        story.append(build_silver_bullets_table(silver_bullets))
        story.extend(build_sources(data.get("silver_bullets_sources", [])))
        story.append(Spacer(1, 4))

    # ── Industry Ecosystem ──
    ecosystem = data.get("ecosystem", {})
    if ecosystem:
        story.append(Paragraph("INDUSTRY ECOSYSTEM", styles["section_head"]))

        # Suppliers
        suppliers = ecosystem.get("suppliers", [])
        if suppliers:
            story.append(Paragraph("Key Suppliers", styles["subsection_head"]))
            story.append(build_ecosystem_table(
                suppliers,
                ["Name", "Supplies", "Risk"],
                [1.5*inch, 3.0*inch, 3.0*inch]))
            story.extend(build_sources(ecosystem.get("suppliers_sources", [])))
            story.append(Spacer(1, 4))

        # Customers
        customers = ecosystem.get("customers", [])
        if customers:
            story.append(Paragraph("Key Customers", styles["subsection_head"]))
            story.append(build_ecosystem_table(
                customers,
                ["Customer/Segment", "% Rev", "Trend"],
                [2.5*inch, 1.5*inch, 3.5*inch]))
            story.extend(build_sources(ecosystem.get("customers_sources", [])))
            story.append(Spacer(1, 4))

        # Regulations
        regulations = ecosystem.get("regulations", [])
        if regulations:
            story.append(Paragraph("Key Regulations", styles["subsection_head"]))
            story.append(build_ecosystem_table(
                regulations,
                ["Regulation", "Impact", "Status"],
                [2.5*inch, 3.0*inch, 2.0*inch]))
            story.extend(build_sources(ecosystem.get("regulations_sources", [])))
            story.append(Spacer(1, 4))

    # ── Tailwinds & Headwinds ──
    tailwinds = data.get("tailwinds", [])
    headwinds = data.get("headwinds", [])
    if tailwinds or headwinds:
        story.append(Paragraph("TAILWINDS & HEADWINDS", styles["section_head"]))
        story.extend(build_tailwinds_headwinds(tailwinds, headwinds))
        story.extend(build_sources(data.get("tailwinds_headwinds_sources", [])))

    # ── Footer ──
    story.append(Spacer(1, 8))
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
        print("Usage: python generate_industry_pdf.py <input.json> <output.pdf>")
        sys.exit(1)
    with open(sys.argv[1]) as f:
        data = json.load(f)
    generate_pdf(data, sys.argv[2])
