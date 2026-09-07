"""Importador de extratos Charles Schwab / Avenue (RF-IMP-001..004).

Colunas: Date,Action,Symbol,Description,Quantity,Price,Amount,Fees
Ações suportadas: Buy → BUY; Dividend/Reinvest Dividend → DIVIDEND.
Deduplicação: hash SHA-256 do arquivo (CT-030) — reimport não cria eventos.
"""
from decimal import Decimal

from ledger.importers.base import StatementImportError, StatementImporter, parse_date_us
from ledger.models import Asset, ImportBatch
from ledger.service import EventService

ACTION_MAP = {
    "buy": "BUY",
    "dividend": "DIVIDEND",
    "reinvest dividend": "DIVIDEND",
}


class SchwabStatementImporter(StatementImporter):
    source = "SCHWAB"

    def preview(self, text: str) -> list[dict]:
        """Linhas normalizadas sem gravar (tela de pré-visualização)."""
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
                continue  # linha não suportada (ex.: Sell/Transfer) — ignorada
            data = parse_date_us(raw.get("Date") or "")
            ticker = (raw.get("Symbol") or "").strip().upper()
            quantity = _dec(raw.get("Quantity"), "Quantity")
            price = _dec(raw.get("Price"), "Price")
            amount = abs(_dec(raw.get("Amount"), "Amount"))
            fees = _dec(raw.get("Fees"), "Fees")
            rows.append({
                "line": line_no, "event_type": etype, "ticker": ticker,
                "trade_date": data, "quantity": quantity, "price": price,
                "amount": amount, "fees": fees,
            })
        return rows

    def import_csv(self, text: str) -> ImportBatch:
        from django.db import transaction

        file_hash = self.file_hash(text)
        if self.already_imported(file_hash):
            batch = ImportBatch.objects.filter(file_hash=file_hash).first()
            if batch is None:  # hash colide com lote de outra conta
                raise StatementImportError("arquivo já importado em outra conta")
            batch.events_created = 0  # idempotente: nada novo
            return batch
        rows = self._rows(text)
        created = 0
        with transaction.atomic():
            batch = ImportBatch.objects.create(
                account=self.account, source=self.source, file_hash=file_hash,
                rows_total=len(rows),
            )
            service = EventService()
            for row in rows:
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
                if row["event_type"] == "BUY":
                    data.update(price_usd=row["price"], fee_usd=row["fees"])
                else:  # DIVIDEND: amount líquido; per_share = (amount + tax)/qty
                    data.update(per_share_usd=(row["amount"] / row["quantity"]), tax_usd=Decimal(0))
                service.record(data)
                created += 1
            batch.events_created = created
            batch.save(update_fields=["events_created"])
        return batch


def _dec(value, field: str) -> Decimal:
    from ledger.importers.base import StatementImportError as _E
    try:
        return Decimal(str(value or "0").replace("$", "").replace(",", "").strip())
    except Exception as e:
        raise _E(f"valor inválido em {field}: {value!r}") from e
