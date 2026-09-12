import io
from unittest import mock
from pypdf import PdfReader
from fiscal.pdf import render_pdf


def _report():
    return {
        "year": 2026,
        "exercise": 2027,
        "beneficiary": {"name": "Gustavo", "cpf": "000.000.000-00"},
        "identification": [{"broker_name": "Avenue Securities LLC", "account_number": "123", "country_code": "US"}],
        "assets": [{
            "ticker": "AAPL", "description": "Apple Inc.", "asset_type": "STOCK",
            "quantity": 25, "avg_cost_usd": 180, "cost_brl_total": 24444.45,
            "cost_brl_attrib": 12222.22, "prev_cost_brl_attrib": 7500,
            "prev_cost_brl": 15000, "cost_usd_total": 4500, "ptax_media": 5.4321,
            "grupo_codigo": "03/01", "country_code_rfb": "249",
            "country_name": "Estados Unidos", "cost_usd_text": "US$ 4.500,00",
            "discriminacao": "25 ações de Apple Inc. (AAPL), custo total de aquisição US$ 4.500,00",
            "dividends_brl": 820, "withholding_brl": 246,
            "gains_brl": 1500, "losses_brl": 300,
        }],
        "cash": [{"account": mock.Mock(broker_name="Avenue Securities LLC", account_number="123"),
                  "balance_usd": 4297, "balance_brl": 21485, "balance_brl_attrib": 10742.50}],
        "income": {"income_brl": 2020, "loss_brl": 300, "taxable_brl": 1720, "tax_brl": 258,
                   "withholding_credit_brl": 246, "tax_due_brl": 12, "loss_carryforward_brl": 0},
        "ptax_yearend": {"rate": 5, "effective_date": "2026-12-31"},
        "exempt": {
            "accounts": [{"account": mock.Mock(name="Avenue Cash", broker_name="Avenue Securities LLC"),
                          "exempt_brl": 1000}],
            "total_brl": 1000,
            "legal_basis": "IN RFB 2180/2024, art. 3º",
        },
    }


def test_render_pdf_target_layout():
    pdf_bytes = render_pdf(_report())
    assert pdf_bytes[:4] == b"%PDF"
    reader = PdfReader(io.BytesIO(pdf_bytes))
    text = "\n".join(p.extract_text() or "" for p in reader.pages)
    assert "RELATÓRIO AUXILIAR PARA DECLARAÇÃO DE" in text
    assert "IMPOSTO DE RENDA" in text
    assert "Exercício 2027" in text
    assert "Ano-Calendário 2026" in text
    assert "BENEFICIÁRIO" in text
    assert "Gustavo" in text
    assert "BENS E DIREITOS / SALDOS" in text
    assert "ATIVOS EM CUSTÓDIA" in text
    assert "AAPL" in text
    assert "Grupo/Código" in text
    assert "03/01" in text
    assert "249" in text
    assert "Situação 31/12/2025" in text
    assert "Situação 31/12/2026" in text
    assert "APLICAÇÃO FINANCEIRA" in text
    assert "Imposto pago no exterior" in text
    assert "Discriminação sugerida" in text
    assert "PTAX média" in text
    assert "RENDIMENTOS ISENTOS" in text
    assert "art. 3º" in text
    # Achado P0 do auditor (16): campos fiscais levam a fatia do contribuinte
    assert "fatia do contribuinte" in text
    assert "R$ 10.742,50" in text   # caixa — valor para declaração (50%)
    assert "R$ 12.222,22" in text   # custódia — custo fiscal (50%)
    assert "R$ 7.500,00" in text    # situação 31/12/2025 (50%)
    assert "Integral da conta (auxiliar)" in text
