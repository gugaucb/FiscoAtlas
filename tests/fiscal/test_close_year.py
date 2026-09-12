import pytest
from fiscal.models import AnnualAssessment, TaxRule

pytestmark = pytest.mark.django_db


@pytest.fixture
def rules(db, residente):
    TaxRule.objects.create(tax_year=2025, rule_version="V2",
                           brackets=[{"limit_brl": None, "rate": "0.15"}],
                           confirmed=True,
                           effective_from="2025-01-01", effective_until="2025-12-31")


def test_fechar_ano_salva_snapshot(client, rules):
    resp = client.post("/apuracao/2025/fechar/")
    assert resp.status_code == 302
    assert resp.url == "/apuracao/2025/"
    snap = AnnualAssessment.objects.get(year=2025)
    assert snap.rule_version == "V2"


def test_fechar_ano_confirma_e_mensagem(client, rules):
    client.post("/apuracao/2025/fechar/")
    page = client.get("/apuracao/2025/").content.decode()
    assert "Ano fechado" in page
    assert "Imposto devido" in page
    snap = AnnualAssessment.objects.get(year=2025)
    assert snap.confirmed is True


def test_refechar_atualiza_sem_duplicar(client, rules):
    client.post("/apuracao/2025/fechar/")
    client.post("/apuracao/2025/fechar/")
    assert AnnualAssessment.objects.filter(year=2025).count() == 1


def test_apuracao_mostra_ano_em_aberto_sem_snapshot(client, rules):
    page = client.get("/apuracao/2025/").content.decode()
    assert "Ano em aberto" in page


def test_heranca_prejuizo_ano_seguinte(client, rules):
    """Com snapshot 2025 salvo com saldo a compensar, apuração 2026 herda."""
    TaxRule.objects.create(tax_year=2026, rule_version="V2",
                           brackets=[{"limit_brl": None, "rate": "0.15"}],
                           confirmed=True,
                           effective_from="2026-01-01", effective_until="2026-12-31")
    snap = AnnualAssessment.objects.create(
        year=2025, rule_version="V2", income_brl=0, loss_brl=1000,
        taxable_brl=0, tax_brl=0, withholding_credit_brl=0, tax_due_brl=0,
        loss_carryforward_brl=1000, detail=[])
    snap.confirmed = True
    snap.save()
    page = client.get("/apuracao/2026/").content.decode()
    assert "Prejuízo a compensar de 2025" in page


def _snapshot_ano(year, rule_version="V2"):
    snap = AnnualAssessment.objects.create(
        year=year, rule_version=rule_version, income_brl=0, loss_brl=0,
        taxable_brl=0, tax_brl=0, withholding_credit_brl=0, tax_due_brl=0,
        loss_carryforward_brl=0, detail=[])
    snap.confirmed = True
    snap.save()
    return snap


def test_reabrir_ano_apaga_snapshot(client, rules):
    """P0 do auditor (23): reabertura formal pela aplicação. Falha no código
    atual — não havia caminho para reabrir um ano fechado."""
    client.post("/apuracao/2025/fechar/")
    resp = client.post("/apuracao/2025/reabrir/", {"confirmar": "2025"})
    assert resp.status_code == 302
    assert not AnnualAssessment.objects.filter(year=2025).exists()
    page = client.get("/apuracao/2025/").content.decode()
    assert "Ano em aberto" in page
    assert "reaberto" in page


def test_reabrir_ano_bloqueado_por_ano_posterior_fechado(client, rules):
    """Reabrir 2025 com 2026 fechado desfaria consumos de prejuízo em
    cascata — bloqueia; reabra do mais recente para o mais antigo."""
    TaxRule.objects.create(tax_year=2026, rule_version="V2",
                           brackets=[{"limit_brl": None, "rate": "0.15"}],
                           confirmed=True,
                           effective_from="2026-01-01", effective_until="2026-12-31")
    client.post("/apuracao/2025/fechar/")
    client.post("/apuracao/2026/fechar/")
    client.post("/apuracao/2025/reabrir/", {"confirmar": "2025"})
    assert AnnualAssessment.objects.filter(year=2025).exists()  # não reabriu
    # reabrindo 2026 primeiro, 2025 pode ser reaberto
    client.post("/apuracao/2026/reabrir/", {"confirmar": "2026"})
    assert not AnnualAssessment.objects.filter(year=2026).exists()
    client.post("/apuracao/2025/reabrir/", {"confirmar": "2025"})
    assert not AnnualAssessment.objects.filter(year=2025).exists()


def test_reabrir_exige_confirmacao(client, rules):
    client.post("/apuracao/2025/fechar/")
    client.post("/apuracao/2025/reabrir/")  # sem o campo confirmar
    assert AnnualAssessment.objects.filter(year=2025).exists()
