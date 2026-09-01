import io

from decimal import Decimal

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table

from ledger.models import Asset, FinancialEvent, OpeningPosition

CENT = Decimal("0.01")


def _q(v):
    return (v or Decimal(0)).quantize(CENT)


def build_memoria(year: int) -> dict:
    """Memória de cálculo (auditoria): linha a linha de cada evento fiscal do ano,
    com PTAX congelada por evento, custo médio BRL corrido e resultado por venda."""
    assets_out = []
    for asset in Asset.objects.filter(active=True).order_by("ticker"):
        events = list(
            FinancialEvent.objects.filter(
                asset=asset, active=True, event_type__in=("BUY", "SELL", "DIVIDEND"),
                trade_date__year=year,
            ).order_by("trade_date", "id")
        )
        op = OpeningPosition.objects.filter(asset=asset).first()
        rows = []
        qty = Decimal(0)
        cost_brl = Decimal(0)
        cost_usd = Decimal(0)
        if op:
            qty = op.quantity
            cost_brl = op.total_cost_brl
            rows.append({
                "kind": "ABERTURA", "date": op.reference_date,
                "quantity": op.quantity, "cost_brl": _q(op.total_cost_brl),
            })
        buy_seq = 0
        for ev in events:
            if ev.event_type == "BUY":
                buy_seq += 1
                cost = _q(abs(ev.amount_brl or 0))
                qty += ev.quantity
                cost_brl += cost
                cost_usd += ev.quantity * ev.price_usd + ev.fee_usd
                rows.append({
                    "kind": "COMPRA", "seq": buy_seq, "event": ev, "date": ev.trade_date,
                    "quantity": ev.quantity, "price_usd": ev.price_usd, "fee_usd": ev.fee_usd,
                    "fx_rate": ev.fx_rate, "cost_brl": cost, "amount_usd": ev.amount_usd,
                    "avg_brl_after": _q(cost_brl / qty) if qty else Decimal(0),
                })
            elif ev.event_type == "SELL":
                avg_brl = cost_brl / qty if qty else Decimal(0)
                avg_usd = cost_usd / qty if qty else Decimal(0)
                sale_brl = _q(ev.amount_usd * (ev.fx_rate or 0))
                cost_sold_brl = _q(avg_brl * ev.quantity)
                gain_brl = _q(sale_brl - cost_sold_brl)
                qty -= ev.quantity
                cost_brl -= cost_sold_brl
                cost_usd -= avg_usd * ev.quantity
                rows.append({
                    "kind": "VENDA", "event": ev, "date": ev.trade_date,
                    "quantity": ev.quantity, "price_usd": ev.price_usd,
                    "fx_rate": ev.fx_rate, "amount_usd": ev.amount_usd,
                    "sale_brl": sale_brl, "cost_sold_brl": cost_sold_brl,
                    "gain_brl": gain_brl, "avg_brl": _q(avg_brl),
                })
            elif ev.event_type == "DIVIDEND":
                gross_usd = ev.amount_usd + ev.tax_usd
                fx = ev.fx_rate or Decimal(0)
                rows.append({
                    "kind": "DIVIDENDO", "event": ev, "date": ev.trade_date,
                    "quantity": ev.quantity, "per_share_usd": ev.quantity and ev.amount_usd / ev.quantity or Decimal(0),
                    "gross_usd": gross_usd, "tax_usd": ev.tax_usd, "fx_rate": ev.fx_rate,
                    "gross_brl": _q(gross_usd * fx), "ir_eua_brl": _q(ev.tax_usd * fx),
                    "net_brl": _q(ev.amount_usd * fx),
                })
        if rows:
            assets_out.append({"ticker": asset.ticker, "description": asset.description, "rows": rows})
    return {"year": year, "assets": assets_out}


def _fmt(value) -> str:
    return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _fmt_rate(value) -> str:
    return f"{value:,.4f}".replace(",", "X").replace(".", ",").replace("X", ".")


def render_memoria_pdf(memoria: dict) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, title=f"Memória de Cálculo {memoria['year']}")
    styles = getSampleStyleSheet()
    h1 = styles["Title"]
    h2 = styles["Heading2"]
    h3 = styles["Heading3"]
    body = styles["BodyText"]
    story = [
        Paragraph("MEMÓRIA DE CÁLCULO — RELATÓRIO TÉCNICO DE AUDITORIA", h1),
        Paragraph(f"Ano-Calendário {memoria['year']}<br/>Investimentos no exterior (Lei 14.754/2023)", body),
        Spacer(1, 12),
    ]
    for a in memoria["assets"]:
        story.append(Paragraph(f"{a['ticker']} — {a['description'].upper()}", h2))
        for r in a["rows"]:
            if r["kind"] == "ABERTURA":
                rows = [
                    ["POSIÇÃO ABERTURA (31/12/2025)", ""],
                    ["Quantidade", str(r["quantity"])],
                    ["Custo BRL", f"R$ {_fmt(r['cost_brl'])}"],
                ]
                story.append(Table(rows))
            elif r["kind"] == "COMPRA":
                story.append(Paragraph(f"COMPRA {r['seq']:02d} — {r['date'].strftime('%d/%m/%Y')}", h3))
                rows = [
                    ["Quantidade", f"{r['quantity']} ações"],
                    ["Preço", f"US$ {_fmt(r['price_usd'])}"],
                    ["PTAX", _fmt_rate(r["fx_rate"])],
                    ["Custo BRL", f"R$ {_fmt(r['cost_brl'])}"],
                    ["CUSTO MÉDIO", f"R$ {_fmt(r['avg_brl_after'])}"],
                ]
                story.append(Table(rows))
            elif r["kind"] == "VENDA":
                story.append(Paragraph(f"VENDA — {r['date'].strftime('%d/%m/%Y')}", h3))
                rows = [
                    ["Quantidade", f"{r['quantity']} ações"],
                    ["Valor", f"US$ {_fmt(r['amount_usd'])}"],
                    ["PTAX", _fmt_rate(r["fx_rate"])],
                    ["Valor venda BRL", f"R$ {_fmt(r['sale_brl'])}"],
                    ["Custo baixado BRL", f"R$ {_fmt(r['cost_sold_brl'])}"],
                    ["Ganho BRL", f"R$ {_fmt(r['gain_brl'])}"],
                ]
                story.append(Table(rows))
            elif r["kind"] == "DIVIDENDO":
                story.append(Paragraph(f"DIVIDENDO — {r['date'].strftime('%d/%m/%Y')}", h3))
                rows = [
                    ["Valor bruto", f"US$ {_fmt(r['gross_usd'])}"],
                    ["PTAX", _fmt_rate(r["fx_rate"])],
                    ["Bruto BRL", f"R$ {_fmt(r['gross_brl'])}"],
                    ["IR EUA", f"R$ {_fmt(r['ir_eua_brl'])}"],
                    ["Líquido BRL", f"R$ {_fmt(r['net_brl'])}"],
                ]
                story.append(Table(rows))
            story.append(Spacer(1, 8))
        story.append(Spacer(1, 12))
    story.append(Paragraph("Documento de auditoria — não substitui a declaração oficial.", styles["Italic"]))
    doc.build(story)
    return buf.getvalue()
