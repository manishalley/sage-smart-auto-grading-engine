"""
report_generator.py
Phase 3: Generate a clean PDF report from evaluation results.
"""

import json
import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT


def generate_report(evaluation: dict, output_path: str):
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=2*cm, leftMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm
    )

    styles = getSampleStyleSheet()
    elements = []

    BLUE = colors.HexColor("#2563EB")
    GREEN = colors.HexColor("#16A34A")
    RED = colors.HexColor("#DC2626")
    LIGHT_BLUE = colors.HexColor("#EFF6FF")
    LIGHT_GRAY = colors.HexColor("#F9FAFB")
    DARK = colors.HexColor("#1E293B")

    title_style = ParagraphStyle("Title", parent=styles["Title"], fontSize=20,
                                  textColor=BLUE, spaceAfter=4, alignment=TA_CENTER)
    subtitle_style = ParagraphStyle("Subtitle", parent=styles["Normal"], fontSize=11,
                                     textColor=colors.gray, alignment=TA_CENTER)
    heading_style = ParagraphStyle("Heading", parent=styles["Heading2"], fontSize=13,
                                    textColor=BLUE, spaceBefore=14, spaceAfter=6)
    normal = ParagraphStyle("Body", parent=styles["Normal"], fontSize=9.5,
                             textColor=DARK, leading=14)
    small = ParagraphStyle("Small", parent=styles["Normal"], fontSize=8.5,
                            textColor=colors.gray, leading=12)
    bold = ParagraphStyle("Bold", parent=styles["Normal"], fontSize=9.5,
                           textColor=DARK, fontName="Helvetica-Bold")

    totals = evaluation["totals"]

    elements.append(Paragraph("AI-Powered Answer Evaluation System", title_style))
    elements.append(Paragraph(f"Subject: {evaluation.get('subject', 'N/A')} | "
                               f"Student: {evaluation.get('student_name', 'N/A')}", subtitle_style))
    elements.append(Spacer(1, 10))
    elements.append(HRFlowable(width="100%", thickness=2, color=BLUE))
    elements.append(Spacer(1, 10))

    summary_data = [
        ["Part A Score", "Part B Score", "Total Score", "Percentage", "Grade"],
        [
            f"{totals['part_a_total']} / {totals['part_a_max']}",
            f"{totals['part_b_total']} / {totals['part_b_max']}",
            f"{totals['grand_total']} / {totals['grand_max']}",
            f"{totals['percentage']}%",
            totals['grade'].split("(")[0].strip()
        ]
    ]
    summary_table = Table(summary_data, colWidths=[3.2*cm, 3.2*cm, 3.2*cm, 3.2*cm, 4.6*cm])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BLUE),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 10),
        ("FONTSIZE", (0, 1), (-1, 1), 12),
        ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWHEIGHT", (0, 0), (-1, 0), 22),
        ("ROWHEIGHT", (0, 1), (-1, 1), 28),
        ("BACKGROUND", (0, 1), (-1, 1), LIGHT_BLUE),
        ("TEXTCOLOR", (2, 1), (2, 1), BLUE),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 16))

    elements.append(Paragraph("Part A — Short Answers (1 Mark Each)", heading_style))
    part_a_data = [["Q#", "Student Answer", "Correct Answer", "Marks", "AI Feedback"]]
    for r in evaluation["part_a"]:
        override = r.get("teacher_override")
        marks_cell = str(override if override is not None else r["marks_awarded"]) + f"/{r['max_marks']}"
        if override is not None:
            marks_cell += " ✎"
        part_a_data.append([
            r["question"],
            Paragraph(r["student_answer"][:120], small),
            Paragraph(r["correct_answer"][:120], small),
            marks_cell,
            Paragraph(r["ai_feedback"][:200], small)
        ])

    part_a_table = Table(part_a_data, colWidths=[1.2*cm, 4.0*cm, 4.0*cm, 1.5*cm, 6.5*cm])
    part_a_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BLUE),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("ALIGN", (3, 0), (3, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_GRAY]),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.lightgrey),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    elements.append(part_a_table)
    elements.append(Spacer(1, 16))

    elements.append(Paragraph("Part B — Long Answers (10 Marks Each)", heading_style))

    for r in evaluation["part_b"]:
        override = r.get("teacher_override")
        final_marks = override if override is not None else r["marks_awarded"]
        override_note = "  ✎ (Teacher Override)" if override is not None else ""

        unit_data = [[
            Paragraph(f"<b>{r['unit']} — {r['question']}</b>", bold),
            Paragraph(f"<b>Marks: {final_marks}/{r['max_marks']}{override_note}</b>", bold)
        ]]
        unit_table = Table(unit_data, colWidths=[12*cm, 5.2*cm])
        unit_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), LIGHT_BLUE),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.lightgrey),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ]))
        elements.append(unit_table)

        if r["question"] != "Not attempted":
            detail_data = [
                ["AI Feedback:", Paragraph(r.get("ai_feedback", ""), normal)],
            ]
            if r.get("concepts_covered"):
                detail_data.append(["Covered:", Paragraph(", ".join(r["concepts_covered"]), small)])
            if r.get("concepts_missing"):
                detail_data.append(["Missing:", Paragraph(", ".join(r["concepts_missing"]), small)])

            detail_table = Table(detail_data, colWidths=[2.5*cm, 14.7*cm])
            detail_table.setStyle(TableStyle([
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (0, -1), 8),
                ("TEXTCOLOR", (0, 0), (0, -1), colors.gray),
            ]))
            elements.append(detail_table)
        else:
            elements.append(Paragraph("Not attempted", small))

        elements.append(Spacer(1, 8))

    elements.append(HRFlowable(width="100%", thickness=1, color=colors.lightgrey))
    elements.append(Spacer(1, 4))
    elements.append(Paragraph(
        "Generated by AI-Powered Answer Evaluation System | Marks marked ✎ were overridden by the teacher.",
        ParagraphStyle("Footer", parent=styles["Normal"], fontSize=7.5,
                       textColor=colors.gray, alignment=TA_CENTER)
    ))

    doc.build(elements)
    print(f"✅ Report saved to: {output_path}")