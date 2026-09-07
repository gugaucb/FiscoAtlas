"""Loss Ledger — rastreabilidade e compensação FIFO multianual (RF-LOS-006/007).

Cada alienação com resultado negativo vira um LossRecord (origem: ano +
evento). Na compensação anual os saldos abertos são consumidos FIFO e a
operação é registrada em LossCompensation (idempotente por reexecução).
"""
from decimal import Decimal

from django.db import transaction

from fiscal.models import LossCompensation, LossRecord

ZERO = Decimal("0.00")


class LossLedgerService:
    @staticmethod
    def record_loss(origin_year: int, amount_brl: Decimal,
                    source_event=None, description: str = "") -> LossRecord:
        """Idempotente: um registro por evento de origem. Reexecução ajusta o
        saldo pelo delta do valor (compensações já feitas são preservadas)."""
        amount = abs(amount_brl).quantize(Decimal("0.01"))
        if amount <= 0:
            raise ValueError("perda deve ser positiva")
        lookup = {"origin_year": origin_year, "source_event": source_event}
        record = LossRecord.objects.filter(**lookup).first()
        if record is None:
            record = LossRecord.objects.create(
                **lookup, amount_brl=amount, remaining_brl=amount,
                description=description,
            )
        else:
            delta = amount - record.amount_brl
            record.amount_brl = amount
            record.remaining_brl = (record.remaining_brl + delta).quantize(Decimal("0.01"))
            record.description = description or record.description
            record.save(update_fields=["amount_brl", "remaining_brl", "description"])
        return record

    @staticmethod
    def open_records(until_year: int):
        """Saldos abertos com origem até o ano informado, FIFO (mais antigo primeiro)."""
        return list(
            LossRecord.objects.filter(
                origin_year__lte=until_year, remaining_brl__gt=0,
            ).order_by("origin_year", "id")
        )

    @classmethod
    def available(cls, until_year: int) -> Decimal:
        return sum((r.remaining_brl for r in cls.open_records(until_year)), ZERO)

    @classmethod
    def apply_compensation(cls, year: int, income_brl: Decimal) -> Decimal:
        """Consome os saldos FIFO até o rendimento do ano (idempotente)."""
        restante = max(income_brl, ZERO)
        with transaction.atomic():
            LossCompensation.objects.filter(year=year).delete()
            compensado = ZERO
            for record in cls.open_records(year):
                if restante <= 0:
                    break
                uso = min(record.remaining_brl, restante)
                record.remaining_brl = (record.remaining_brl - uso).quantize(Decimal("0.01"))
                record.save(update_fields=["remaining_brl"])
                LossCompensation.objects.create(record=record, year=year, amount_brl=uso)
                compensado += uso
                restante -= uso
        return compensado
