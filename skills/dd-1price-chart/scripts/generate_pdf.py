#!/usr/bin/env python3
"""
generate_pdf.py -- Assembles a PDF with the price chart on top and
an event reference table with clickable source links below.

Usage:
    python3 generate_pdf.py /path/to/input.json

The input JSON is the same as generate_chart.py, but events now include
extra fields: "description", "source_name", "source_url".

Example event:
{
    "date": "2020-04-01",
    "label": "Negative pricing;\nCOVID crash",
    "description": "WTI futures briefly traded below zero for the first time in history as storage capacity ran out amid COVID-19 demand collapse and the OPEC+ price war.",
    "source_name": "World Economic Forum",
    "source_url": "https://www.weforum.org/stories/2020/04/oil-barrel-prices..."
}
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '_shared'))
from auto_install import ensure_installed
ensure_installed('reportlab')

import json
import sys
import os
import subprocess
from datetime import datetime

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Image, Spacer, Table, TableStyle, Paragraph,
    KeepTogether
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER


def load_data(json_path):
    with open(json_path, "r") as f:
        return json.load(f)


def generate_chart_png(json_path):
    """Call generate_chart.py to produce the PNG, return its path."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    chart_script = os.path.join(script_dir, "generate_chart.py")

    # Modify output_path to be a temp PNG
    with open(json_path, "r") as f:
        data = json.load(f)

    png_path = data["output_path"].replace(".pdf", "_chart.png")
    data["output_path"] = png_path

    tmp_json = json_path + ".chart_tmp.json"
    with open(tmp_json, "w") as f:
        json.dump(data, f)

    subprocess.run(
        ["python3", chart_script, tmp_json],
        check=True, capture_output=True
    )
    os.remove(tmp_json)
    return png_path


def build_pdf(data, chart_png_path):
    """Build the final PDF with chart on top and event table below."""
    output_path = data["output_path"]
    ticker = data["ticker"]
    company_name = data["company_name"]
    events = data.get("events", [])

    # Sort events chronologically
    events_sorted = sorted(events, key=lambda e: e["date"])

    # Determine date range
    dates = data["dates_iso"]
    start_year = dates[0][:4]
    end_year = dates[-1][:4]

    # --- Styles ---
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "ChartTitle",
        parent=styles["Title"],
        fontName="Times-Bold",
        fontSize=16,
        leading=20,
        textColor=HexColor("#111111"),
        alignment=TA_CENTER,
        spaceAfter=6,
    )

    subtitle_style = ParagraphStyle(
        "ChartSubtitle",
        parent=styles["Normal"],
        fontName="Times-Roman",
        fontSize=10,
        textColor=HexColor("#666666"),
        alignment=TA_CENTER,
        spaceAfter=12,
    )

    section_style = ParagraphStyle(
        "SectionHeader",
        parent=styles["Heading2"],
        fontName="Times-Bold",
        fontSize=13,
        leading=16,
        textColor=HexColor("#1a3a6e"),
        spaceBefore=12,
        spaceAfter=6,
    )

    date_style = ParagraphStyle(
        "EventDate",
        parent=styles["Normal"],
        fontName="Times-Bold",
        fontSize=9,
        leading=11,
        textColor=HexColor("#111111"),
    )

    headline_style = ParagraphStyle(
        "EventHeadline",
        parent=styles["Normal"],
        fontName="Times-Bold",
        fontSize=9,
        leading=12,
        textColor=HexColor("#111111"),
    )

    desc_style = ParagraphStyle(
        "EventDesc",
        parent=styles["Normal"],
        fontName="Times-Roman",
        fontSize=8.5,
        leading=11,
        textColor=HexColor("#333333"),
    )

    source_style = ParagraphStyle(
        "EventSource",
        parent=styles["Normal"],
        fontName="Times-Italic",
        fontSize=8,
        leading=10,
        textColor=HexColor("#1a4d8f"),
    )

    footer_style = ParagraphStyle(
        "Footer",
        parent=styles["Normal"],
        fontName="Times-Italic",
        fontSize=8,
        textColor=HexColor("#999999"),
        alignment=TA_CENTER,
    )

    # --- Build document ---
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        leftMargin=0.6 * inch,
        rightMargin=0.6 * inch,
        topMargin=0.5 * inch,
        bottomMargin=0.5 * inch,
    )

    story = []

    # Chart image -- scale to fit page width
    page_width = letter[0] - 1.2 * inch  # account for margins
    chart_img = Image(chart_png_path, width=page_width, height=page_width * 0.54)
    story.append(chart_img)
    story.append(Spacer(1, 8))

    # Section header
    story.append(Paragraph("Key Events & Annotations", section_style))

    # Build event table
    if events_sorted:
        table_data = []
        # Header style (white text on dark background)
        header_style = ParagraphStyle(
            "TableHeader",
            parent=styles["Normal"],
            fontName="Times-Bold",
            fontSize=9,
            leading=11,
            textColor=HexColor("#ffffff"),
        )

        # Header row
        table_data.append([
            Paragraph("<b>Date</b>", header_style),
            Paragraph("<b>Event</b>", header_style),
            Paragraph("<b>Details</b>", header_style),
            Paragraph("<b>Source</b>", header_style),
        ])

        for ev in events_sorted:
            # Parse date
            dt = datetime.strptime(ev["date"], "%Y-%m-%d")
            date_str = dt.strftime("%b %Y")

            # Clean label (remove \n for table)
            label = ev.get("label", "").replace("\n", " ")

            # Description
            description = ev.get("description", "")

            # Source with clickable link
            source_name = ev.get("source_name", "")
            source_url = ev.get("source_url", "")
            if source_url and source_name:
                source_cell = Paragraph(
                    f'<a href="{source_url}" color="#1a4d8f">{source_name}</a>',
                    source_style
                )
            elif source_url:
                source_cell = Paragraph(
                    f'<a href="{source_url}" color="#1a4d8f">Link</a>',
                    source_style
                )
            elif source_name:
                source_cell = Paragraph(source_name, source_style)
            else:
                source_cell = Paragraph("", source_style)

            table_data.append([
                Paragraph(date_str, date_style),
                Paragraph(label, headline_style),
                Paragraph(description, desc_style),
                source_cell,
            ])

        col_widths = [
            0.65 * inch,    # Date
            1.2 * inch,     # Event
            3.6 * inch,     # Details
            1.55 * inch,    # Source
        ]

        tbl = Table(table_data, colWidths=col_widths, repeatRows=1)
        tbl.setStyle(TableStyle([
            # Header
            ("BACKGROUND", (0, 0), (-1, 0), HexColor("#1a3a6e")),
            ("TEXTCOLOR", (0, 0), (-1, 0), HexColor("#ffffff")),
            ("FONTNAME", (0, 0), (-1, 0), "Times-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
            # Alternating rows
            ("BACKGROUND", (0, 1), (-1, -1), HexColor("#ffffff")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [HexColor("#ffffff"), HexColor("#f5f7fa")]),
            # Grid
            ("GRID", (0, 0), (-1, -1), 0.4, HexColor("#cccccc")),
            ("LINEBELOW", (0, 0), (-1, 0), 1.2, HexColor("#1a3a6e")),
            # Alignment
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ]))

        story.append(tbl)

    # Footer
    story.append(Spacer(1, 12))
    now = datetime.now()
    story.append(Paragraph(
        f"Source: Yahoo Finance  |  Data as of {now.strftime('%B')} {now.year}",
        footer_style
    ))

    doc.build(story)
    print(f"PDF saved to: {output_path}")

    # Clean up intermediate PNG
    if os.path.exists(chart_png_path):
        os.remove(chart_png_path)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 generate_pdf.py /path/to/input.json")
        sys.exit(1)

    json_path = sys.argv[1]
    data = load_data(json_path)

    # Generate chart PNG first
    chart_png = generate_chart_png(json_path)

    # Build final PDF
    build_pdf(data, chart_png)
