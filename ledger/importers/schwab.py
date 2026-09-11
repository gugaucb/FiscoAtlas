"""Importador de extratos Charles Schwab / Avenue (RF-IMP-001..004).

Colunas: Date,Action,Symbol,Description,Quantity,Price,Amount,Fees
Ações suportadas: Buy → BUY; Sell → SELL; Dividend/Reinvest Dividend → DIVIDEND.
Deduplicação: hash SHA-256 do arquivo (CT-030) — reimport não cria eventos.

Auditoria-fiscal 01: nenhuma linha desaparece silenciosamente. Ação não
suportada (ex.: Transfer) vira pendência visível/bloqueante (ImportIssue),
nunca um descarte sem rastro.
"""
from decimal import Decimal

from ledger.importers.base import StatementImportError, StatementImporter, parse_date_us
from ledger.models import Asset, ImportBatch, ImportIssue
from ledger.service import EventService

ACTION_MAP = {
    "buy": "BUY",
    "sell": "SELL",
    "dividend": "DIVIDEND",
    "reinvest dividend": "DIVIDEND",
}


class SchwabStatementImporter(StatementImporter):
    source = "SCHWAB"

    def preview(self, text: str) -> list[dict]:
        """Linhas normalizadas sem gravar (tela de pré-visualização).
        Linhas não suportadas aparecem com status UNSUPPORTED — nunca
        são descartadas."""
        return self._rows(text)

    def _rows(self, text: str) -> list[dict]:
        import csv
        import io

        rows = []
        reader = csv.DictReader(io.StringIO(text.strip()))
        for line_no, raw in enumerate(reader, start=2):
            action = (raw.get("Action") or "").strip()
            etype = ACTION_MAP.get(action.lower())
            if etype is None:
                # Auditoria-fiscal 01: pendência explícita, nunca `continue` silencioso.
                rows.append({
                    "line": line_no, "event_type": None, "raw_action": action,
                    "status": "UNSUPPORTED", "severity": "BLOCKING",
                    "reason": "Evento potencialmente fiscal não importado",
                    "raw_data": {k: v for k, v in raw.items() if k},
                })
                continue
            data = parse_date_us(raw.get("Date") or "")
            ticker = (raw.get("Symbol") or "").strip().upper()
            quantity = _dec(raw.get("Quantity"), "Quantity")
            price = _dec(raw.get("Price"), "Price")
            amount = abs(_dec(raw.get("Amount"), "Amount"))
            fees = _dec(raw.get("Fees"), "Fees")
            rows.append({
                "line": line_no, "event_type": etype, "ticker": ticker,
                "trade_date": data, "quantity": quantity, "price": price,
                "amount": amount, "fees": fees, "status": "OK",
            })
        return rows

    def import_csv(self, text: str, acknowledge_pending: bool = False) -> ImportBatch:
        """Importa o extrato. Linhas com ação não suportada viram ImportIssue
        PENDING; a importação só conclui se o usuário reconhecer as pendências
        explicitamente (acknowledge_pending=True)."""
        from django.db import transaction

        file_hash = self.file_hash(text)
        if self.already_imported(file_hash):
            batch = ImportBatch.objects.filter(file_hash=file_hash).first()
            if batch is None:  # hash colide com lote de outra conta
                raise StatementImportError("arquivo já importado em outra conta")
            batch.events_created = 0  # idempotente: nada novo
            return batch
        rows = self._rows(text)
        # todas as linhas contam, inclusive as não suportadas
        source_rows = len(rows)
        created = 0
        with transaction.atomic():
            batch = ImportBatch.objects.create(
                account=self.account, source=self.source, file_hash=file_hash,
                rows_total=source_rows, rows_source=source_rows,
            )
            pending = [r for r in rows if r["status"] != "OK"]
            if pending and not acknowledge_pending:
                resumo = ", ".join(
                    f"linha {r['line']} ({r['raw_action'] or 'ação vazia'})" for r in pending[:5]
                )
                raise StatementImportError(
                    f"{len(pending)} linha(s) com ação não suportada "
                    f"({resumo}{'…' if len(pending) > 5 else ''}). "
                    "Reconheça as pendências na prévia para importar o restante."
                )
            service = EventService()
            for row in rows:
                if row["status"] != "OK":
                    ImportIssue.objects.create(
                        batch=batch, line_number=row["line"],
                        raw_action=row["raw_action"], raw_data=row["raw_data"],
                        severity=row["severity"], reason=row["reason"],
                    )
                    continue
                asset = Asset.objects.filter(
                    ticker=row["ticker"], active=True
                ).first()
                if asset is None:
                    raise StatementImportError(
                        f"linha {row['line']}: ativo {row['ticker']} não cadastrado — "
                        "cadastre-o explicitamente antes de importar."
                    )
                data = dict(
                    event_type=row["event_type"], account=self.account, asset=asset,
                    trade_date=row["trade_date"], quantity=row["quantity"],
                )
                if row["event_type"] in ("BUY", "SELL"):
                    data.update(price_usd=row["price"], fee_usd=row["fees"])
                else:  # DIVIDEND: amount líquido; per_share = (amount + tax)/qty
                    data.update(per_share_usd=(row["amount"] / row["quantity"]), tax_usd=Decimal(0))
                service.record(data)
                created += 1
            batch.events_created = created
            batch.rows_imported = created
            batch.rows_unsupported = len(pending)
            batch.save(update_fields=["events_created", "rows_imported", "rows_unsupported"])
            assert batch.reconciled, "conciliação do lote violada"
        return batch


def _dec(value, field: str) -> Decimal:
    from ledger.importers.base import StatementImportError as _E
    try:
        return Decimal(str(value or "0").replace("$", "").replace(",", "").strip())
    except Exception as e:
        raise _E(f"valor inválido em {field}: {value!r}") from e
