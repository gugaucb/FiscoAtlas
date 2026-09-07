from datetime import date
from decimal import Decimal
from unittest import mock
import io
import pytest
from pypdf import PdfReader
from fiscal.models import TaxRule
from fiscal.memoria import build_memoria, render_memoria_pdf
from ledger.models import Asset, BrokerAccount
from ledger.service import EventService

RATE = Decimal("5.00000000")
pytestmark = pytest.mark.django_db


@pytest.fixture
def setup(db):
    acct = BrokerAccount.objects.create(broker_name="Avenue Securities LLC", account_number="123")
    aapl = Asset.objects.create(ticker="AAPL", description="Apple Inc.", asset_type="FOREIGN_EQUITY")
    with mock.patch.object(EventService, "_ptax_rate", return_value=RATE):
        # compra 1: 10 @180, compra 2: 5 @190, venda 8 @200, dividendo
        EventService().record(dict(account=acct, event_type="BUY", asset=aapl, trade_date=date(2026, 1, 10),
                                   quantity=Decimal(10), price_usd=Decimal(180), fee_usd=Decimal(0)))
        EventService().record(dict(account=acct, event_type="BUY", asset=aapl, trade_date=date(2026, 2, 10),
                                   quantity=Decimal(5), price_usd=Decimal(190), fee_usd=Decimal(0)))
        EventService().record(dict(account=acct, event_type="SELL", asset=aapl, trade_date=date(2026, 3, 10),
                                   quantity=Decimal(8), price_usd=Decimal(200), fee_usd=Decimal(0)))
        EventService().record(dict(account=acct, event_type="DIVIDEND", asset=aapl, trade_date=date(2026, 4, 10),
                                   quantity=Decimal(7), per_share_usd=Decimal(1), tax_usd=Decimal(2), foreign_tax_payment_date=date(2026, 4, 10), date_evidence_source="BROKER_STATEMENT", country_code="US", jurisdiction_level="FEDERAL"))
    return acct, aapl


def _memoria(setup):
    acct, aapl = setup
    # imposto pago no exterior: PTAX COMPRA mockada (mesma taxa do cenário)
    with mock.patch("fiscal.engine.PtaxService.get_rate", return_value=mock.Mock(rate=RATE)):
        return build_memoria(2026), aapl


def test_memoria_structure_and_values(setup):
    mem, _ = _memoria(setup)
    assert mem["year"] == 2026
    block = mem["assets"][0]
    assert block["ticker"] == "AAPL"
    kinds = [r["kind"] for r in block["rows"]]
    assert kinds.count("COMPRA") == 2
    assert kinds == ["COMPRA", "COMPRA", "VENDA", "DIVIDENDO"]

    c1 = block["rows"][0]
    assert c1["quantity"] == Decimal(10)
    assert c1["price_usd"] == Decimal(180)
    assert c1["fx_rate"] == RATE
    assert c1["cost_brl"] == Decimal(1800 * 5)  # 9000
    assert c1["avg_brl_after"] == Decimal(900)  # 9000/10

    c2 = block["rows"][1]
    assert c2["cost_brl"] == Decimal(190 * 5 * 5)  # 4750
    assert c2["avg_brl_after"].quantize(Decimal("0.01")) == Decimal("916.67")  # 13750/15

    v = block["rows"][2]
    assert v["quantity"] == Decimal(8)
    assert v["amount_usd"] == Decimal(1600)
    assert v["sale_brl"] == Decimal(8000)
    # custo baixado: 8 × custo médio 13750/15 = 7333.33
    assert v["cost_sold_brl"] == Decimal("7333.33")
    assert v["gain_brl"] == Decimal("666.67")

    d = block["rows"][3]
    assert d["gross_usd"] == Decimal(7)
    assert d["tax_usd"] == Decimal(2)
    assert d["gross_brl"] == Decimal(35)
    assert d["ir_eua_brl"] == Decimal(10)


def test_memoria_pdf(setup):
    mem, _ = _memoria(setup)
    pdf_bytes = render_memoria_pdf(mem)
    assert pdf_bytes[:4] == b"%PDF"
    reader = PdfReader(io.BytesIO(pdf_bytes))
    text = "\n".join(p.extract_text() or "" for p in reader.pages)
    assert "MEMÓRIA DE CÁLCULO" in text
    assert "Ano-Calendário 2026" in text
    assert "AAPL" in text
    assert "COMPRA 01" in text
    assert "CUSTO MÉDIO" in text
    assert "VENDA" in text
    assert "Ganho BRL" in text
    assert "DIVIDENDO" in text
    assert "IR EUA" in text
