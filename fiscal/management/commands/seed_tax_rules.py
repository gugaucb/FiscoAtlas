from django.core.management.base import BaseCommand
from fiscal.models import TaxRule

BRACKETS = [
    {"limit_brl": "6000.00", "rate": "0.00"},        # isenção até 6 mil
    {"limit_brl": "50000.00", "rate": "0.15"},       # 15% de 6 mil a 50 mil
    {"limit_brl": None, "rate": "0.225"},            # 22,5% acima de 50 mil
]


class Command(BaseCommand):
    help = "Seed das regras tributárias 2024-2026 (a confirmar com contador)"

    def handle(self, *args, **options):
        for year in (2024, 2025, 2026):
            TaxRule.objects.get_or_create(
                tax_year=year,
                rule_version="V1",
                defaults={
                    "brackets": BRACKETS,
                    "foreign_tax_credit_enabled": True,
                    "loss_carryforward_enabled": True,
                    "fx_cash_policy": {"non_bearing_cash_exempt": True},
                    "quote_type": "VENDA",
                    "date_rule": "INCOME_RECEIPT_DATE",
                    "confirmed": False,
                    "effective_from": f"{year}-01-01",
                    "effective_until": f"{year}-12-31",
                    "notes": "Histórico: tabela progressiva antiga (errada p/ aplicações financeiras)",
                },
            )
            TaxRule.objects.get_or_create(
                tax_year=year,
                rule_version="V2",
                defaults={
                    "brackets": [{"limit_brl": None, "rate": "0.15"}],
                    "foreign_tax_credit_enabled": True,
                    "loss_carryforward_enabled": True,
                    "fx_cash_policy": {"non_bearing_cash_exempt": True},
                    "quote_type": "VENDA",
                    "date_rule": "INCOME_RECEIPT_DATE",
                    "confirmed": True,
                    "effective_from": f"{year}-01-01",
                    "effective_until": f"{year}-12-31",
                    "notes": "Lei 14.754/2023 — ver ADR-0003",
                },
            )
        self.stdout.write(self.style.SUCCESS("Regras 2024-2026 (V1 e V2) criadas (confirmed=False)"))
