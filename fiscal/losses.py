"""Loss Ledger — rastreabilidade e compensação FIFO multianual (RF-LOS-006/007).

Cada alienação com resultado negativo vira um LossRecord (origem: ano +
evento). Na compensação anual os saldos abertos são consumidos FIFO e a
operação é registrada em LossCompensation (idempotente por reexecução).
"""
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q

from fiscal.models import AnnualAssessment, LossCompensation, LossRecord

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
        """Saldos abertos com origem até o ano informado, FIFO (mais antigo primeiro).

        Achado P0 do auditor: perda cujo source_event foi desativado
        (corrigido) não é lançamento fiscal válido — sai da compensação.
        A correção da venda gera um novo evento, que registra sua própria
        perda; a perda fantasma do evento antigo não pode reduzir imposto
        futuro. Registros sem source_event (manual/legado) permanecem."""
        return list(
            LossRecord.objects.filter(
                Q(source_event__isnull=True) | Q(source_event__active=True),
                origin_year__lte=until_year, remaining_brl__gt=0,
            ).order_by("origin_year", "id")
        )

    @classmethod
    def available(cls, until_year: int) -> Decimal:
        return sum((r.remaining_brl for r in cls.open_records(until_year)), ZERO)

    @classmethod
    def apply_compensation(cls, year: int, income_brl: Decimal) -> Decimal:
        """Consome os saldos FIFO até o rendimento do ano (idempotente).

        Auditoria-fiscal 09: refechar um ano NÃO pode corromper o saldo —
        antes de recalcular, cada compensação existente do ano é DEVOLVIDA
        ao registro de origem (em transação atômica, com bloqueio
        concorrente nos registros). Recalcular um ano anterior com ano
        posterior já fechado é bloqueado: nunca alterar história fechada
        invisivelmente (reabertura em cascata fica explícita para o usuário)."""
        if AnnualAssessment.objects.filter(year__gt=year).exists():
            raise ValidationError(
                f"Não é possível recalcular a compensação de {year}: existe "
                f"fechamento posterior consolidado. Reabra os anos em cascata "
                "explicitamente antes de recalcular."
            )
        restante = max(income_brl, ZERO)
        with transaction.atomic():
            # 1) devolve cada compensação do ano ao saldo de origem
            for comp in LossCompensation.objects.filter(year=year).select_related("record"):
                record = LossRecord.objects.select_for_update().get(pk=comp.record_id)
                record.remaining_brl = (record.remaining_brl + comp.amount_brl).quantize(Decimal("0.01"))
                record.save(update_fields=["remaining_brl"])
                comp.delete()
            # 2) recalcula FIFO com bloqueio concorrente
            compensado = ZERO
            for aberto in cls.open_records(year):
                record = LossRecord.objects.select_for_update().get(pk=aberto.pk)
                if restante <= 0:
                    break
                uso = min(record.remaining_brl, restante)
                record.remaining_brl = (record.remaining_brl - uso).quantize(Decimal("0.01"))
                record.save(update_fields=["remaining_brl"])
                LossCompensation.objects.create(record=record, year=year, amount_brl=uso)
                compensado += uso
                restante -= uso
        return compensado
