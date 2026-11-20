"""Invoice numbers, VAT split and PDF rendering (reportlab). The same data feeds the HTML invoice page."""
import io
from decimal import ROUND_HALF_UP, Decimal
from xml.sax.saxutils import escape

from django.conf import settings
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from content.models import StoreSettings

TEAL = colors.HexColor("#0f766e")
SLATE = colors.HexColor("#475569")


def invoice_data(order):
    cfg = StoreSettings.load()
    items = list(order.items.all())
    total = sum((i.line_total() for i in items), Decimal("0"))
    vat = Decimal("0")
    if cfg.tax_rate > 0:  # prices already include VAT
        vat = (total * cfg.tax_rate / (100 + cfg.tax_rate)).quantize(Decimal("0.01"), ROUND_HALF_UP)
    paid_with = order.payments.filter(status="success").first()
    return {"order": order, "cfg": cfg, "items": items, "total": total, "vat": vat, "net": total - vat,
            "currency": settings.CURRENCY, "number": order.invoice_number, "receipt": paid_with.receipt if paid_with else "",
            "method": order.get_payment_method_display()}


def _p(text, style):
    return Paragraph(escape(str(text)).replace("\n", "<br/>"), style)


def build_pdf(order):
    d = invoice_data(order)
    cfg, cur = d["cfg"], d["currency"]
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=16 * mm,
                            title=f"Invoice {d['number']}", author=cfg.business_name)
    ss = getSampleStyleSheet()
    body = ParagraphStyle("body", parent=ss["Normal"], fontSize=9.5, leading=13, textColor=colors.HexColor("#0f172a"))
    small = ParagraphStyle("small", parent=body, fontSize=8.5, textColor=SLATE)
    h1 = ParagraphStyle("h1", parent=body, fontSize=22, leading=26, textColor=TEAL, fontName="Helvetica-Bold")
    bold = ParagraphStyle("bold", parent=body, fontName="Helvetica-Bold")
    right = ParagraphStyle("right", parent=body, alignment=2)
    right_bold = ParagraphStyle("rb", parent=bold, alignment=2)

    business = [_p(cfg.business_name, bold)]
    for line in (cfg.address, cfg.phone, cfg.email, f"PIN: {cfg.tax_pin}" if cfg.tax_pin else ""):
        if line:
            business.append(_p(line, small))
    state = "PAID" if order.paid else "UNPAID"
    head = Table([[business, [Paragraph("INVOICE", h1), _p(f"No. {d['number']}", bold),
                              _p(f"Date: {order.created:%d %b %Y}", small), _p(f"Status: {state}", bold if order.paid else small)]]],
                 colWidths=[95 * mm, 77 * mm])
    head.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("ALIGN", (1, 0), (1, 0), "RIGHT")]))
    bill = [_p("Bill to", small), _p(order.name, bold), _p(order.email, small)]
    if order.phone:
        bill.append(_p(order.phone, small))
    bill.append(_p(order.address, small))

    rows = [[_p("Item", bold), _p("Qty", right_bold), _p(f"Price ({cur})", right_bold), _p(f"Total ({cur})", right_bold)]]
    for i in d["items"]:
        rows.append([_p(i.display_name, body), _p(i.quantity, right), _p(f"{i.price:,.2f}", right), _p(f"{i.line_total():,.2f}", right)])
    items = Table(rows, colWidths=[85 * mm, 15 * mm, 36 * mm, 36 * mm], repeatRows=1)
    items.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
                               ("LINEBELOW", (0, 0), (-1, -1), 0.4, colors.HexColor("#e2e8f0")),
                               ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
    totals = [[_p("Total", right_bold), _p(f"{cur} {d['total']:,.2f}", right_bold)]]
    if d["vat"]:
        totals = [[_p(f"Subtotal (excl. VAT)", right), _p(f"{cur} {d['net']:,.2f}", right)],
                  [_p(f"VAT {cfg.tax_rate.normalize():f}% (included)", right), _p(f"{cur} {d['vat']:,.2f}", right)]] + totals
    tot = Table(totals, colWidths=[136 * mm, 36 * mm])
    pay = f"Payment: {d['method']}" + (f" - M-Pesa receipt {d['receipt']}" if d["receipt"] else "")
    story = [head, Spacer(1, 8 * mm), Table([[bill]], colWidths=[172 * mm]), Spacer(1, 6 * mm), items, Spacer(1, 3 * mm), tot,
             Spacer(1, 6 * mm), _p(pay, small)]
    if cfg.invoice_footer:
        story += [Spacer(1, 10 * mm), _p(cfg.invoice_footer, small)]
    doc.build(story)
    return buf.getvalue()
