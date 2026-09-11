"""Guia orientativa do DARF (RF-DARF-001/005, CT-029).

Ticket 08 (auditoria-fiscal): as regras de arrecadação são versionadas por
EXERCÍCIO da declaração (FilingRule) — ano-calendário 2026 → exercício
2027. Sem regra homologada, a orientação fica PRELIMINAR com aviso: nunca
vencimento, código ou parcelamento inventados a partir de constantes.

Semântica do mínimo (art. 938, §§ 4º e 5º, RIR/2018): DARF inferior a
R$ 10,00 não é imposto extinto — é ADIAMENTO: vedada a emissão e o valor
se acumula ao imposto do mesmo código dos períodos subsequentes.
"""
from decimal import Decimal

from fiscal.models import FilingRule

DESCRICAO = "IRPF — Declaração de Ajuste Anual"


class DarfGuideService:
    def __init__(self, year: int):
        self.year = year  # ano-calendário

    def build(self, tax_due_brl: Decimal) -> dict:
        tax_due = (tax_due_brl or Decimal(0)).quantize(Decimal("0.01"))
        exercicio = self.year + 1
        guia = {
            "periodo_apuracao": f"{self.year}",
            "exercicio": exercicio,
            "dispensado": False,
            "status": "PRELIMINAR",
            "aviso": "",
            "codigo": None,
            "vencimento": None,
            "mensagem": "",
        }
        regra = None
        candidata = FilingRule.objects.filter(filing_year=exercicio).first()
        if candidata and candidata.is_homologated:
            regra = candidata
        if regra is None:
            if candidata:
                guia["aviso"] = (
                    f"Regra {candidata.rule_version} do exercício {exercicio} "
                    "não está homologada — orientação PRELIMINAR."
                )
            else:
                guia["aviso"] = (
                    f"Nenhuma regra de arrecadação homologada para o exercício "
                    f"{exercicio} — orientação PRELIMINAR, sem vencimento "
                    "definitivo. Cadastre e homologue em FilingRule."
                )
            guia["cota_unica"] = {"valor": tax_due}
            guia["parcelamento"] = None
            return guia

        guia["status"] = "HOMOLOGADO"
        guia["codigo"] = regra.darf_code
        guia["vencimento"] = regra.due_date
        if tax_due <= 0:
            guia.update({
                "adiado": True,
                "payment_required_now": False,
                "mensagem": "Nenhum imposto devido.",
                "cota_unica": {"valor": tax_due},
                "parcelamento": None,
            })
            return guia
        if tax_due < regra.minimum_darf:
            # ticket 08: semântica de ADIAMENTO — não extinção do imposto
            guia.update({
                "adiado": True,
                "payment_required_now": False,
                "mensagem": (
                    "Imposto devido inferior a R$ 10,00: é vedada a emissão do "
                    "DARF (art. 938, § 4º, RIR/2018) e o valor é ADIADO — "
                    "adiciona-se ao imposto do mesmo código dos períodos "
                    "subsequentes (art. 938, § 5º, RIR/2018), até atingir o "
                    "mínimo. O imposto permanece devido."
                ),
                "cota_unica": {"valor": tax_due},
                "parcelamento": None,
            })
            return guia
        guia.update({
            "payment_required_now": True,
            "cota_unica": {
                "valor": tax_due,
                "vencimento": regra.due_date,
            },
            "parcelamento": self._parcelamento(tax_due, regra),
        })
        return guia

    @staticmethod
    def _parcelamento(tax_due: Decimal, regra) -> dict:
        n = DarfGuideService._n_quotas(tax_due, regra)
        return {
            "n_quotas": n,
            "valor_quota": (tax_due / n).quantize(Decimal("0.01")),
            "juros": "Selic a partir do vencimento da cota única (2ª quota em diante)",
        }

    @staticmethod
    def _n_quotas(tax_due: Decimal, regra) -> int:
        """Maior número de quotas cujo valor respeita a quota mínima, sem
        exceder o máximo (não é divisão automática pelo máximo)."""
        minimo = regra.minimum_installment
        if tax_due < regra.minimum_tax_for_installment:
            return 1
        n = regra.maximum_installments
        while n > 1 and (tax_due / n).quantize(Decimal("0.01")) < minimo:
            n -= 1
        return n