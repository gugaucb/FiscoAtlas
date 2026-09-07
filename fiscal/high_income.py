"""Tributação mínima de altas rendas — Lei nº 15.270/2025 (RF-HI-001..004).

A partir do ano-calendário 2026, contribuintes com renda global anual
superior a R$ 600.000,00 ficam sujeitos à tributação mínima progressiva.
A plataforma apura apenas rendimentos NO EXTERIOR: se só esse recorte já
supera o limiar, o alerta é destacado; caso contrário o teste fica
indeterminado (a renda global não é conhecida aqui).
"""
from decimal import Decimal

from fiscal.engine import TaxEngine

LIMIAR_ANUAL_BRL = Decimal(600_000)
ANO_INICIO = 2026


class HighIncomeService:
    def __init__(self, year: int):
        self.year = year

    def evaluate(self) -> dict:
        if self.year < ANO_INICIO:
            return {
                "status": "HIGH_INCOME_NOT_APPLICABLE",
                "foreign_income_brl": None,
                "message": (
                    "Lei nº 15.270/2025 vigente a partir do ano-calendário 2026."
                ),
                "highlight": False,
            }
        resultado = TaxEngine(self.year).compute()
        renda_exterior = resultado["income_brl"]
        if renda_exterior > LIMIAR_ANUAL_BRL:
            return {
                "status": "HIGH_INCOME_THRESHOLD_EXCEEDED",
                "foreign_income_brl": renda_exterior,
                "message": (
                    "Os rendimentos no exterior apurados pela plataforma "
                    f"(R$ {renda_exterior}) já superam o limiar de R$ 600.000,00 "
                    "da tributação mínima de altas rendas (Lei nº 15.270/2025). "
                    "Verifique a renda global e a incidência da alíquota mínima."
                ),
                "highlight": True,
            }
        return {
            "status": "HIGH_INCOME_TEST_UNDETERMINED",
            "foreign_income_brl": renda_exterior,
            "message": (
                "A plataforma não conhece sua renda global. Se a soma dos "
                "rendimentos (Brasil + exterior) superar R$ 600.000,00, aplique "
                "as regras de tributação mínima de altas rendas (Lei nº "
                "15.270/2025) na declaração."
            ),
            "highlight": False,
        }
