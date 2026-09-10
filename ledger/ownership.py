"""RF-PER-003 / auditoria-fiscal 06: titularidade em UM só lugar.

O fator de participação fiscal do contribuinte numa conta é usado por
dividendos, juros, ganhos, perdas, crédito de imposto exterior, CBE e
atribuição no DIRPF. Nenhum cálculo fiscal deve aplicar a proporção por
conta própria — sempre via OwnershipService.
"""
from decimal import Decimal

from django.core.exceptions import ValidationError

HUNDRED = Decimal(100)


class OwnershipService:
    """Fator do contribuinte sobre os fatos fiscais de uma conta.

    100% → 1; 50% → 0,5; 0% → 0 (valor EXPLÍCITO no modelo — a faixa do
    modelo passa a permitir 0% justamente para contas de terceiros sem
    regra fiscal silenciosa)."""

    @staticmethod
    def taxpayer_share_factor(account) -> Decimal:
        share = account.ownership_share
        if share is None:
            raise ValidationError(
                f"Conta {account} sem participação fiscal definida. "
                "Informe ownership_share (0% deve ser decisão explícita)."
            )
        return share / HUNDRED
