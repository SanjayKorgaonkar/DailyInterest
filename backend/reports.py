"""Monthly reconciliation checklist PDF generation."""
import io
from datetime import datetime, timezone

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

STATUS_COLORS = {
    "Certified": colors.HexColor("#0f9d78"),
    "Auto-matched": colors.HexColor("#0d9488"),
    "Needs review": colors.HexColor("#d1453b"),
}


def month_label(month: str) -> str:
    y, m = map(int, month.split("-"))
    return datetime(y, m, 1).strftime("%B %Y")


def build_monthly_checklist_pdf(month: str, rows: list, totals: dict) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=20 * mm, bottomMargin=18 * mm, leftMargin=16 * mm, rightMargin=16 * mm)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("ChecklistTitle", parent=styles["Title"], fontSize=18, textColor=colors.HexColor("#0f172a"))
    sub_style = ParagraphStyle("ChecklistSub", parent=styles["Normal"], fontSize=9, textColor=colors.HexColor("#64748b"))

    elems = [
        Paragraph(f"Monthly Reconciliation Checklist &mdash; {month_label(month)}", title_style),
        Paragraph(f"Generated {datetime.now(timezone.utc).strftime('%d %b %Y, %H:%M UTC')} &middot; Ledgerline", sub_style),
        Spacer(1, 14),
    ]

    header = ["Bank", "Facility", "Type", "Calculated (Rs.)", "Bank Charged (Rs.)", "Variance (Rs.)", "Status"]
    data = [header]
    for r in rows:
        data.append([r["bank"], r["name"], r["type"], f"{r['ours']:,.2f}", f"{r['bank_amount']:,.2f}",
                     f"{r['variance']:,.2f}", r["status"]])
    data.append(["", "", "TOTAL", f"{totals['ours']:,.2f}", f"{totals['bank']:,.2f}", f"{totals['variance']:,.2f}", ""])

    table = Table(data, colWidths=[75, 115, 42, 82, 88, 78, 75])
    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
        ("TOPPADDING", (0, 0), (-1, 0), 8),
        ("GRID", (0, 0), (-1, -2), 0.5, colors.HexColor("#dbe3ec")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, colors.HexColor("#f7f9fc")]),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("LINEABOVE", (0, -1), (-1, -1), 1, colors.HexColor("#0f172a")),
        ("TOPPADDING", (0, -1), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]
    for i, r in enumerate(rows, start=1):
        c = STATUS_COLORS.get(r["status"])
        if c:
            style_cmds.append(("TEXTCOLOR", (6, i), (6, i), c))
            style_cmds.append(("FONTNAME", (6, i), (6, i), "Helvetica-Bold"))
    table.setStyle(TableStyle(style_cmds))
    elems.append(table)
    elems.append(Spacer(1, 16))
    elems.append(Paragraph(
        "Status legend: <font color='#0f9d78'><b>Certified</b></font> = bank certificate on file &middot; "
        "<font color='#0d9488'><b>Auto-matched</b></font> = bank interest captured from statement/entries &middot; "
        "<font color='#d1453b'><b>Needs review</b></font> = no bank figure captured for this facility yet.",
        sub_style,
    ))
    doc.build(elems)
    return buf.getvalue()
