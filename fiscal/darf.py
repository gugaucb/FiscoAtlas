"""Guia orientativa do DARF código 0211 (RF-DARF-001/005, CT-029).

Saldo devedor da apuração anual → orientação formal de pagamento:
cota única com vencimento no último dia útil de abril do exercício ou
parcelamento em até 8 quotas com juros Selic a partir da 2ª quota.
Imposto devido < R$ 10,00 → vedada a emissão do DARF e o valor é adicionado
ao imposto do mesmo código dos períodos subsequentes
(art. 938, §§ 4º e 5º, RIR/2018 — Decreto 9.580/2018).
"""
from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP

CODIGO = "0211"
DESCRICAO = "IRPF — Declaração de Ajuste Anual"
MINIMO_DARF = Decimal(10)
MAX_QUOTAS = 8


def _ultimo_dia_util_abril(exercicio: int) -> date:
    ano = exercicio + 1
    dia = date(ano, 4, monthrange(ano, 4)[1])
    while dia.weekday() >= 5:  # sábado/domingo
        dia -= timedelta(days=1)
    return dia


class DarfGuideService:
    def __init__(self, year: int):
        self.year = year

    def build(self, tax_due_brl: Decimal) -> dict:
        tax_due = (tax_due_brl or Decimal(0)).quantize(Decimal("0.01"))
        guia = {
            "codigo": CODIGO,
            "descricao": DESCRICAO,
            "periodo_apuracao": f"{self.year}",
            "vencimento": _ultimo_dia_util_abril(self.year),
            "dispensado": False,
            "mensagem": "",
        }
        if tax_due < MINIMO_DARF:
            guia.update({
                "dispensado": True,
                "mensagem": (
                    "Imposto devido inferior a R$ 10,00: é vedada a emissão do "
                    "DARF (art. 938, § 4º, RIR/2018) e o valor é adicionado ao "
                    "imposto do mesmo código dos períodos subsequentes "
                    "(art. 938, § 5º, RIR/2018), até atingir R$ 10,00."
                ),
                "cota_unica": {"valor": tax_due},
                "parcelamento": None,
            })
            return guia
        quota = (tax_due / MAX_QUOTAS).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        guia.update({
            "cota_unica": {
                "valor": tax_due,
                "vencimento": _ultimo_dia_util_abril(self.year),
            },
            "parcelamento": {
                "n_quotas": MAX_QUOTAS,
                "valor_quota": quota,
                "juros": "Selic a partir do vencimento da cota única (2ª quota em diante)",
            },
        })
        return guia
