import io

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def _fmt(value) -> str:
    return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _line(style, text=""):
    return Paragraph(text, style)


def render_pdf(report: dict) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, title=f"Relatório Auxiliar DIRPF {report['year']}")
    styles = getSampleStyleSheet()
    h1 = styles["Title"]
    h2 = styles["Heading2"]
    body = styles["BodyText"]
    closing = report.get("closing", {})
    if closing.get("is_closed"):
        closed_at = closing.get("closed_at")
        status = f"Ano fechado em {closed_at:%d/%m/%Y %H:%M}" if closed_at else "Ano fechado"
    else:
        status = "Ano em aberto"
    if not closing.get("prev_closed"):
        status += (f" — ATENÇÃO: o ano-calendário {report['year'] - 1} não está fechado; "
                   "o saldo de prejuízo a compensar herdado pode estar incompleto.")
    story = [
        Paragraph("RELATÓRIO AUXILIAR PARA DECLARAÇÃO DE IMPOSTO DE RENDA", h1),
        Paragraph(f"Exercício {report['exercise']}<br/>Ano-Calendário {report['year']}", body),
        Paragraph(f"Status: {status}", body),
        Spacer(1, 12),
    ]

    story.append(Paragraph("1 — IDENTIFICAÇÃO DA INSTITUIÇÃO", h2))
    for i in report["identification"]:
        story.append(_line(body, f"Corretora:<br/>{i['broker_name']}<br/><br/>País:<br/>{COUNTRY_NAMES.get(i['country_code'], i['country_code'])}"))
    story.append(Spacer(1, 12))

    story.append(Paragraph("2 — BENEFICIÁRIO", h2))
    b = report.get("beneficiary", {})
    story.append(_line(body, f"Nome:<br/>{b.get('name', '')}<br/><br/>CPF:<br/>{b.get('cpf', '')}"))
    story.append(Spacer(1, 12))

    story.append(Paragraph("3 — BENS E DIREITOS / SALDOS", h2))
    ptax = report["ptax_yearend"]
    for c in report["cash"]:
        acct = c["account"]
        story.append(_line(body, f"{acct.broker_name} — conta {acct.account_number}"))
        rows = [
            ["Moeda", "USD"],
            [f"Saldo em 31/12/{report['year']}", f"US$ {_fmt(c['balance_usd'])}"],
            ["PTAX", f"R$ {str(ptax['rate']).replace('.', ',')}"],
            ["Valor para declaração", f"R$ {_fmt(c['balance_brl'])}"],
        ]
        story.append(Table(rows))
    story.append(Spacer(1, 12))

    story.append(Paragraph("4 — ATIVOS EM CUSTÓDIA", h2))
    for a in report["assets"]:
        story.append(Paragraph(f"{a['ticker']} — {a['description'].upper()}", h2))
        rows = [
            ["Grupo/Código", a["grupo_codigo"]],
            ["Localização", f"{a['country_code_rfb']} – {a['country_name']}"],
            ["Tipo", a["asset_type"]],
            ["Quantidade", str(a["quantity"])],
            ["Custo aquisição USD", a.get("cost_usd_text", f"US$ {_fmt(a['cost_usd_total'])}")],
            ["PTAX média", f"R$ {str(a['ptax_media']).replace('.', ',')}"],
            ["Custo fiscal BRL", f"R$ {_fmt(a['cost_brl_total'])}"],
            [f"Situação 31/12/{report['year'] - 1}", f"R$ {_fmt(a['prev_cost_brl'])}"],
            [f"Situação 31/12/{report['year']}", f"R$ {_fmt(a['cost_brl_total'])}"],
        ]
        story.append(Table(rows))
        story.append(Paragraph("APLICAÇÃO FINANCEIRA", styles["Heading3"]))
        app_rows = [
            ["Dividendos", f"R$ {_fmt(a['dividends_brl'])}"],
            ["Ganhos em alienações", f"R$ {_fmt(a['gains_brl'])}"],
            ["Prejuízos em alienações", f"-R$ {_fmt(a['losses_brl'])}"],
            ["Imposto pago no exterior", f"R$ {_fmt(a['withholding_brl'])}"],
        ]
        story.append(Table(app_rows))
        story.append(_line(body, "Discriminação sugerida:"))
        story.append(_line(body, a["discriminacao"]))
        story.append(Spacer(1, 12))

    inc = report["income"]
    story.append(Paragraph("5 — RENDIMENTOS E GANHOS (consolidado, Lei 14.754/2023)", h2))
    rows = [
        ["Rendimento bruto (BRL)", _fmt(inc["income_brl"])],
        ["Perdas do ano (BRL)", _fmt(inc["loss_brl"])],
        [f"Prejuízo herdado de {report['year'] - 1} (BRL)", _fmt(inc.get("loss_inherited_brl", 0))],
        ["Base tributável (BRL)", _fmt(inc["taxable_brl"])],
        ["Imposto (15%)", _fmt(inc["tax_brl"])],
        ["Crédito withholding EUA", _fmt(inc["withholding_credit_brl"])],
        ["Imposto devido (BRL)", _fmt(inc["tax_due_brl"])],
        ["Prejuízo a compensar (BRL)", _fmt(inc["loss_carryforward_brl"])],
    ]
    table = Table(rows)
    table.setStyle(TableStyle([("FONTNAME", (0, 5), (1, 5), "Helvetica-Bold")]))
    story.append(table)
    story.append(Spacer(1, 12))

    story.append(Paragraph("6 — CRÉDITO DE IMPOSTO PAGO NO EXTERIOR (Lei 14.754/2023, art. 5º)", h2))
    credit_rows = [["Rendimento", "Bruto BRL", "Limite 15%", "IR exterior", "Crédito usado", "Não aproveitado"]]
    for r in inc.get("credit_detail", []):
        credit_rows.append([
            str(r["description"]), _fmt(r["gross_brl"]), _fmt(r["limit_brl"]),
            _fmt(r["withholding_brl"]), _fmt(r["credit_used_brl"]), _fmt(r["credit_unused_brl"]),
        ])
    if len(credit_rows) > 1:
        story.append(Table(credit_rows))
    else:
        story.append(_line(body, "Sem rendimentos com retenção no exterior."))
    story.append(Spacer(1, 12))

    story.append(Paragraph("7 — RENDIMENTOS ISENTOS E NÃO TRIBUTÁVEIS", h2))
    story.append(_line(body, "IN RFB 2180/2024, art. 3º — variação cambial de caixa não remunerado"))
    for e in report["exempt"]["accounts"]:
        acct = e["account"]
        story.append(_line(body, f"{acct.name or acct.broker_name}: R$ {_fmt(e['exempt_brl'])}"))
    if not report["exempt"]["accounts"]:
        story.append(_line(body, "Nenhum caixa não remunerado."))
    total_exempt = Table([
        ["Total isento", f"R$ {_fmt(report['exempt']['total_brl'])}"],
    ])
    total_exempt.setStyle(TableStyle([("FONTNAME", (0, 0), (1, 0), "Helvetica-Bold")]))
    story.append(total_exempt)
    story.append(Spacer(1, 12))
    darf = report.get("darf")
    if darf:
        story.append(Paragraph(
            "8 — ORIENTAÇÃO DE PAGAMENTO — DARF "
            f"{darf.get('codigo') or '—'} — IRPF Declaração de Ajuste Anual "
            f"[{darf.get('status')}]", h2))
        if darf.get("aviso"):
            story.append(_line(body, darf["aviso"]))
        if darf.get("adiado"):
            story.append(_line(body, darf["mensagem"]))
        else:
            venc = darf["cota_unica"].get("vencimento")
            story.append(_line(
                body,
                f"Cota única: R$ {_fmt(darf['cota_unica']['valor'])} — vencimento "
                + (venc.strftime("%d/%m/%Y") if venc else "—"),
            ))
            parc = darf.get("parcelamento") or {}
            if parc:
                story.append(_line(
                    body,
                    f"Parcelamento: até {parc['n_quotas']} quotas de "
                    f"R$ {_fmt(parc['valor_quota'])} ({parc['juros']})",
                ))
        story.append(Spacer(1, 12))
    story.append(Paragraph("Documento de conferência — não substitui a declaração oficial.", styles["Italic"]))

    doc.build(story)
    return buf.getvalue()


COUNTRY_NAMES = {"US": "Estados Unidos"}
