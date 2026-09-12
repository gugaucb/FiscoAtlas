"""Ticket 05 (auditoria-fiscal): elegibilidade do crédito de imposto no
exterior em UM serviço central (Lei 14.754/2023, art. 4º).

Antes a regra vivia espalhada (engine inline + validador bloqueante com
retenção > 15% como erro). Uma retenção estrangeira maior (ex.: 30% dos
EUA) é legítima: o que a lei limita é o crédito aproveitável — limitado ao
IR devido, sem carryforward do excedente. O fechamento só bloqueia para
pagamento com tratamento fiscal desconhecido (UNKNOWN).
"""
# RF-FTC-002/003: reciprocidade de tratamento para tributos FEDERAIS
# sobre a renda.
RECIPROCITY_COUNTRIES = {"US"}

# Tributos que geram crédito: imposto sobre a renda retido na fonte ou não.
ELIGIBLE_TAX_TYPES = {"WITHHOLDING_INCOME_TAX", "INCOME_TAX"}


class ForeignTaxCreditService:
    @staticmethod
    def eligibility(pagamento) -> tuple[bool, str]:
        """(elegível, motivo) para um ForeignTaxPayment.

        Motivos de inelegibilidade: UNKNOWN_*, NAO_FEDERAL,
        SEM_RECIPROCIDADE, TRIBUTO_NAO_ELEGIVEL, RECOVERABLE. UNKNOWN
        (jurisdição, tipo, evidência ou recuperabilidade) exige classificação
        do usuário — sem regra silenciosa.

        P0 do auditor: o crédito (Lei 14.754/2023, art. 4º; IN RFB
        2.180/2024) é só para imposto pago em CARÁTER DEFINITIVO — tributo
        passível de restituição/reembolso/compensação no exterior não gera
        crédito brasileiro (RECOVERABLE → crédito zero).
        """
        if pagamento.jurisdiction_level == "UNKNOWN":
            return False, "UNKNOWN_JURISDICAO"
        if pagamento.tax_type == "UNKNOWN":
            return False, "UNKNOWN_TIPO"
        if pagamento.date_evidence_source in ("", "UNKNOWN"):
            return False, "UNKNOWN_EVIDENCIA"
        if getattr(pagamento, "recoverability_status", "UNKNOWN") == "UNKNOWN":
            return False, "UNKNOWN_RECUPERABILIDADE"
        if pagamento.recoverability_status == "RECOVERABLE":
            return False, "RECOVERABLE"
        if pagamento.jurisdiction_level != "FEDERAL":
            return False, "NAO_FEDERAL"
        if pagamento.country_code not in RECIPROCITY_COUNTRIES:
            return False, "SEM_RECIPROCIDADE"
        if pagamento.tax_type not in ELIGIBLE_TAX_TYPES:
            return False, "TRIBUTO_NAO_ELEGIVEL"
        return True, ""

    @classmethod
    def is_eligible(cls, pagamento) -> bool:
        return cls.eligibility(pagamento)[0]

    @classmethod
    def exige_classificacao(cls, pagamentos) -> bool:
        """True quando algum pagamento tem tratamento fiscal desconhecido
        (UNKNOWN) — único caso que bloqueia o fechamento do ano."""
        return any(
            motivo.startswith("UNKNOWN")
            for _, motivo in (cls.eligibility(p) for p in pagamentos)
        )
