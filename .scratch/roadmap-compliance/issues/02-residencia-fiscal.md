# 02: Perfil fiscal do contribuinte, residência e titularidade (Parte 2 — P0)

**What to build:** Perfil com condição de residência fiscal (BRAZIL_RESIDENT/NON_RESIDENT/PART_YEAR_RESIDENT/UNKNOWN) e datas de mudança (DSDP). TaxEngine bloqueia apuração se não residente pleno ou perfil não configurado. Contas conjuntas com ownership_type/ownership_share e relatório proporcional.

**Requisitos:** RF-PER-001..005, RF-VAL-001.
**Branch:** `fix/tax-residency-profile`.

**Blocked by:** None (can start immediately).
**Status:** resolved

- [x] Profile com tax_residency_status (4 opções) + residency_start_date, residency_end_date, has_dsdp
- [x] TaxEngine.compute levanta ValidationError("Contribuinte não qualificado como residente fiscal pleno no Brasil.") se status != BRAZIL_RESIDENT ou Profile ausente
- [x] BrokerAccount com ownership_type (INDIVIDUAL/JOINT/THIRD_PARTY) e ownership_share (0.01–100.00)
- [x] Conta conjunta 50%: relatório demonstra saldos/rendimentos proporcionais
- [x] Form/views de perfil atualizados
- [x] Suíte completa verde
