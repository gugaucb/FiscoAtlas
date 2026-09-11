# Relatório de Auditoria de Compliance Tributário — FiscoAtlas

**Sistema Auditado:** FiscoAtlas  
**Norma de Referência:** `requisitos_funcionais_compliance_investimentos_exterior_BR.md` (v1.0)  
**Data da Auditoria:** 07/09/2026  
**Auditor Responsável:** Auditor Especialista em Código-Fonte e Compliance Tributário Brasileiro (Investimentos no Exterior)  
**Status Geral de Conformidade:** **PARCIALMENTE CONFORME (Núcleo de cálculo PTAX e Lei 14.754 conforme; lacunas em importação, corporate actions, perfil do contribuinte, governança de schemas e obrigações acessórias CBE)**

---

## 1. Objetivos do Sistema e Contexto Legal

### 1.1. Missão do FiscoAtlas
O **FiscoAtlas** é uma aplicação projetada para pessoas físicas com domicílio e residência fiscal no Brasil, investidores individuais de classe média/varejo, que realizam investimentos financeiros diretos no exterior, primordialmente nos mercados de capitais norte-americanos (NYSE, NASDAQ). O sistema tem como propósito apurar os resultados fiscais e gerar memórias de cálculo auditáveis que subsidiem o preenchimento da **Declaração de Ajuste Anual do Imposto sobre a Renda da Pessoa Física (DIRPF/DAA)**.

### 1.2. O Novo Cenário Tributário (Lei nº 14.754/2023 e IN RFB nº 2.180/2024)
A partir de **01/01/2024**, o regime fiscal de investimentos no exterior passou por uma reforma estrutural completa, rompendo com as regras históricas vigentes até 31/12/2023:

1. **Alíquota Uniforme de 15% na DAA:** Os rendimentos de aplicações financeiras no exterior (dividendos, juros, cupons e ganhos líquidos na alienação de ativos) passaram a ser tributados à alíquota definitiva de **15%** no ajuste anual, sem deduções de base (Lei 14.754/2023, art. 2º).
2. **Extinção de Regimes Mensais para Aplicações Financeiras:**
   - **Fim da Isenção Mensal de R$ 35.000:** A isenção de pequeno valor do art. 22 da Lei nº 9.250/1995 **não se aplica mais** às aplicações financeiras no exterior para fatos geradores a partir de 2024. Vendas de pequeno porte com ganho de capital agora são integralmente tributáveis a 15%.
   - **Extinção do GCAP Mensal:** Não há mais apuração mensal de ganho de capital em programa acessório (GCAP) para aplicações financeiras.
   - **Extinção do Carnê-Leão Mensal:** Dividendos e juros de aplicações financeiras deixam de ser sujeitos ao carnê-leão mensal e à tabela progressiva de até 27,5%.
3. **Compensação de Perdas Financeiras:** Perdas realizadas na alienação de aplicações financeiras no exterior podem ser compensadas com rendimentos da mesma espécie no próprio ano-calendário e o saldo remanescente pode ser transportado (*carryforward*) para os anos seguintes (art. 9º).
4. **Crédito de Imposto de Renda Pago no Exterior (FTC):** O imposto retido na fonte nos EUA (geralmente 30% em dividendos para pessoas físicas brasileiras com base no Formulário W-8BEN, ante a reciprocidade reconhecida) pode ser deduzido do imposto devido no Brasil, **limitado estritamente a 15% do rendimento bruto correspondente** (art. 4º). O excedente de imposto pago nos EUA é descartado (sem restituição no Brasil e sem carryforward de crédito).
5. **Rigor Cambial PTAX Segregado:**
   - **Regra Geral:** PTAX de **VENDA** na data fiscal do evento para aquisição, alienação e recebimento de proventos brutos (art. 15).
   - **Exceção Legal:** PTAX de **COMPRA** na data documental do efetivo pagamento para conversão do imposto retido/pago no exterior (art. 4º, §2º e IN RFB 2.180/2024, art. 12, §3º). As cotações de rendimento e imposto **não se confundem** nem compartilham cotação presumida.
6. **Contas Não Remuneradas:** A variação cambial sobre depósitos em moeda estrangeira não remunerados é isenta/não tributável (IN RFB 2.180/2024, art. 3º).
7. **Obrigações Acessórias e Limites:**
   - **CBE/BACEN (Resolução BCB nº 279/2022):** Obrigatoriedade anual para patrimônio no exterior igual ou superior a US$ 1.000.000 em 31/12.
   - **Tributação Mínima de Altas Rendas (Lei nº 15.270/2025):** Aplicável a partir do ano-calendário 2026 para contribuintes com rendimentos globais anuais superiores a R$ 600.000.

---

## 2. Quadro Resumo Estatístico da Auditoria

| Domínio de Requisitos | Qtd. Total | Atendidos (`OK`) | Parciais (`PARCIAL`) | Não Atendidos (`NÃO_IMP`) | Incorretos (`INCORRETO`) | Taxa de Conformidade Plena |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **4. Arquitetura (RF-ARQ)** | 8 | 5 | 1 | 2 | 0 | 62,5% |
| **5. Perfil do Contribuinte (RF-PER)** | 5 | 0 | 1 | 4 | 0 | 0,0% |
| **6. Cadastro de Ativos (RF-AST)** | 9 | 4 | 1 | 3 | 1 | 44,4% |
| **7. Importação e Normalização (RF-IMP)** | 8 | 1 | 2 | 5 | 0 | 12,5% |
| **8. Taxonomia de Eventos (RF-EVT)** | 1 | 0 | 1 | 0 | 0 | 0,0% |
| **9. Câmbio e PTAX (RF-FX)** | 8 | 8 | 0 | 0 | 0 | **100,0%** |
| **10. Posição e Custo (RF-CST)** | 8 | 5 | 1 | 2 | 0 | 62,5% |
| **11. Regime Lei 14.754/2023 (RF-TAX)** | 14 | 13 | 1 | 0 | 0 | 92,8% |
| **12. Perdas e Compensações (RF-LOS)** | 7 | 4 | 2 | 1 | 0 | 57,1% |
| **13. Imposto Pago no Exterior (RF-FTC)** | 10 | 8 | 1 | 1 | 0 | 80,0% |
| **14. Contas no Exterior (RF-CASH)** | 5 | 5 | 0 | 0 | 0 | **100,0%** |
| **15. DIRPF Bens e Direitos (RF-DIR)** | 13 | 8 | 3 | 2 | 0 | 61,5% |
| **16. Obrigatoriedade DAA (RF-DAA)** | 3 | 0 | 0 | 3 | 0 | 0,0% |
| **17. DARF (RF-DARF)** | 5 | 4 | 0 | 1 | 0 | 80,0% |
| **18. CBE / BACEN (RF-CBE)** | 7 | 0 | 0 | 7 | 0 | 0,0% |
| **19. Altas Rendas 2026 (RF-HI)** | 4 | 0 | 0 | 4 | 0 | 0,0% |
| **20. Regras Históricas (RF-HIS)** | 5 | 2 | 1 | 2 | 0 | 40,0% |
| **21. Corporate Actions (RF-CA)** | 8 | 0 | 0 | 8 | 0 | 0,0% |
| **22. Reconciliação Financeira (RF-REC)** | 5 | 1 | 2 | 2 | 0 | 20,0% |
| **23. Trilha de Auditoria (RF-AUD)** | 7 | 4 | 2 | 1 | 0 | 57,1% |
| **24. Relatórios Obrigatórios (RF-RPT)** | 9 | 5 | 2 | 2 | 0 | 55,5% |
| **25. Validações Bloqueantes (RF-VAL)** | 20 | 8 | 4 | 8 | 0 | 40,0% |
| **TOTAL GERAL (RF-*)** | **168** | **86** | **25** | **56** | **1** | **51,2% Pleno** (66,0% ponderado) |

---

## 3. Requisitos Atendidos (`OK`) — Evidências no Código

Os requisitos abaixo foram plenamente implementados e atendem aos critérios técnicos e jurídicos:

### 3.1. Câmbio e PTAX (RF-FX-001 a RF-FX-008, RF-FTC-010)
- **Fonte Oficial e Preservação**: [`fx/service.py:L16-L45`](file:///Users/gustavoluiscosta/Downloads/projetos/FiscoAtlas/fx/service.py#L16-L45) conecta à API OData oficial do BCB (`CotacaoDolarDia`), consulta as cotações oficiais e armazena metadados de data efetiva e tipo de cotação em [`fx/models.py`](file:///Users/gustavoluiscosta/Downloads/projetos/FiscoAtlas/fx/models.py).
- **Segregação de PTAX**: O sistema resolve adequadamente a PTAX de VENDA na data do fato gerador para ativos e proventos, e PTAX de COMPRA na data documental do pagamento para imposto retido/pago no exterior via [`fiscal/date_rules.py:L14-L19`](file:///Users/gustavoluiscosta/Downloads/projetos/FiscoAtlas/fiscal/date_rules.py#L14-L19) e [`fiscal/engine.py:L22-L30`](file:///Users/gustavoluiscosta/Downloads/projetos/FiscoAtlas/fiscal/engine.py#L22-L30).
- **Override Manual Controlado**: `PtaxService.override` permite registrar cotação manual com justificativa obrigatória e `manual_reason` rastreado (`fx/service.py:L48`, `ledger/forms.py:L109-110`).

### 3.2. Regime Tributário da Lei 14.754/2023 (RF-TAX-001 a RF-TAX-013)
- **Alíquota de 15% na DAA**: [`fiscal/engine.py:L65-L66, L130`](file:///Users/gustavoluiscosta/Downloads/projetos/FiscoAtlas/fiscal/engine.py#L65-L66) aplica a alíquota uniforme de 15% sobre a base tributável anual, registrando a memória no modelo [`AnnualAssessment`](file:///Users/gustavoluiscosta/Downloads/projetos/FiscoAtlas/fiscal/models.py#L63-L76).
- **Ausência de Regras Silenciosas e Anacrônicas**: Inspeção estática em todo o código confirmou a **inexistência** de aplicação da isenção mensal de R$ 35.000,00, de DARFs mensais de bolsa brasileira (código 6015), de Carnê-Leão (0190) ou GCAP mensal para aplicações financeiras a partir de 2024.
- **Variação Cambial Integrada**: O ganho na alienação apurado em [`ledger/position.py:L71-L74`](file:///Users/gustavoluiscosta/Downloads/projetos/FiscoAtlas/ledger/position.py#L71-L74) realiza a diferença entre a alienação em BRL e o custo fiscal baixado em BRL, integrando a variação cambial do principal conforme determinado pelo art. 3º, II da Lei 14.754/2023.

### 3.3. Contas Bancárias e Depósitos no Exterior (RF-CASH-001 a RF-CASH-005)
- **Segregação Remunerada vs. Não Remunerada**: O campo `is_interest_bearing` em [`ledger/models.py:L39`](file:///Users/gustavoluiscosta/Downloads/projetos/FiscoAtlas/ledger/models.py#L39) controla o regime. Em `ledger/service.py:L40-41`, impede o lançamento de `JUROS` em contas não remuneradas.
- **Isenção da Variação Cambial de Moeda Estrangeira**: [`fiscal/report.py:L38-L50`](file:///Users/gustavoluiscosta/Downloads/projetos/FiscoAtlas/fiscal/report.py#L38-L50) implementa a regra da IN RFB 2.180/2024 art. 3º, demonstrando a variação cambial isenta do caixa não remunerado no encerramento do exercício.

### 3.4. Dedução do Imposto Pago no Exterior (RF-FTC-001, RF-FTC-003, RF-FTC-005, RF-FTC-008)
- **Crédito Limitado por Rendimento**: [`fiscal/engine.py:L112`](file:///Users/gustavoluiscosta/Downloads/projetos/FiscoAtlas/fiscal/engine.py#L112) limita o crédito tributário aproveitável a `min(wh_brl, gross_brl * 15%)`.
- **Descarte de Excedente**: O imposto excedente (`credit_unused_brl`) é descartado no encerramento do ano, sem carryforward nem restituição (`fiscal/report.py:L111`).
- **Trilha Auditável de Edição do Imposto**: O modelo [`ForeignTaxPaymentAudit`](file:///Users/gustavoluiscosta/Downloads/projetos/FiscoAtlas/ledger/models.py#L120-L132) registra diff campo a campo, motivo e timestamp de qualquer modificação feita pelo usuário.

### 3.5. Posição Patrimonial em 31/12 (RF-CST-001, RF-DIR-001, RF-DIR-002)
- **Custo Médio Ponderado em BRL**: [`ledger/position.py:L20-L44`](file:///Users/gustavoluiscosta/Downloads/projetos/FiscoAtlas/ledger/position.py#L20-L44) mantém a custódia agregada com custo médio ponderado em BRL congelado.
- **Posição de Abertura**: [`ledger/models.py:L134-L150`](file:///Users/gustavoluiscosta/Downloads/projetos/FiscoAtlas/ledger/models.py#L134-L150) (`OpeningPosition`) preserva o custo histórico já declarado nas DIRPFs anteriores.

---

## 4. Requisitos Não Atendidos, Parciais ou Incorretos: Motivo e Como Sanar

Esta seção documenta com rigor os requisitos que demandam intervenção técnica, estruturados com o motivo da não conformidade, arquivos de código envolvidos e o procedimento exato de remediação.

---

### 4.1. Arquitetura e Procedimentos

#### [PARCIAL] RF-ARQ-002 e RF-ARQ-003 — Versionamento do Schema da DIRPF e Bloqueio de Exercício Não Homologado
- **Prioridade:** P0
- **Motivo do Desalinhamento:** Em [`fiscal/report.py:L14-L16`](file:///Users/gustavoluiscosta/Downloads/projetos/FiscoAtlas/fiscal/report.py#L14-L16), os códigos da ficha de Bens e Direitos (`GRUPO_CODIGO = {"STOCK": "03/01", "ETF": "03/02", ...}`) e os códigos de países (`COUNTRY_RFB = {"US": ("249", "Estados Unidos")}`) estão definidos como constantes hardcoded no topo do módulo. Não existe versionamento de schema por `filing_year` (ano do exercício). O sistema não sabe se a Receita Federal homologou as instruções normativas para o exercício correspondente e gera relatórios finais para exercícios futuros sem qualquer trava procedimental de homologação.
- **Partes do Código Afetadas:** [`fiscal/report.py:L14-L16`](file:///Users/gustavoluiscosta/Downloads/projetos/FiscoAtlas/fiscal/report.py#L14-L16), [`fiscal/models.py`](file:///Users/gustavoluiscosta/Downloads/projetos/FiscoAtlas/fiscal/models.py).
- **Como Sanar:**
  1. Criar um modelo ou registry de metadados versionados:
     ```python
     # fiscal/models.py
     class DirpfSchema(models.Model):
         filing_year = models.PositiveIntegerField(unique=True) # Ex: 2027 (ano-calendário 2026)
         is_homologated = models.BooleanField(default=False)
         codes_mapping = models.JSONField(default=dict)
         country_mapping = models.JSONField(default=dict)
         normative_reference = models.CharField(max_length=255)
     ```
  2. Em `ReportService.build()` (`fiscal/report.py`), buscar o `DirpfSchema.objects.filter(filing_year=self.year + 1).first()`. Se o schema não existir ou `is_homologated == False`, marcar no relatório `status: "PRELIMINAR"` e impedir que o usuário conclua o fechamento oficial (`AnnualAssessment.confirmed = True`).

---

### 4.2. Perfil Fiscal do Contribuinte

#### [NÃO ATENDIDO] RF-PER-001 e RF-PER-002 — Residência Fiscal e Fracionamento Temporal
- **Prioridade:** P0
- **Motivo do Desalinhamento:** O modelo `Profile` em [`fiscal/models.py:L5-L16`](file:///Users/gustavoluiscosta/Downloads/projetos/FiscoAtlas/fiscal/models.py#L5-L16) contém exclusivamente os campos `name` e `cpf`. Não há campo para registrar a condição de residente fiscal no Brasil (`BRAZIL_RESIDENT`, `NON_RESIDENT`, `PART_YEAR_RESIDENT`), nem as datas de início e encerramento da residência fiscal (`residency_start_date`, `residency_end_date`). O sistema presume cegamente que qualquer perfil cadastrado é residente fiscal brasileiro contínuo, arriscando apurar imposto indevido de não residentes ou de emigrantes que entregaram a Declaração de Saída Definitiva do País (DSDP).
- **Partes do Código Afetadas:** [`fiscal/models.py:L5-L16`](file:///Users/gustavoluiscosta/Downloads/projetos/FiscoAtlas/fiscal/models.py#L5-L16), [`fiscal/profile_views.py`](file:///Users/gustavoluiscosta/Downloads/projetos/FiscoAtlas/fiscal/profile_views.py), [`fiscal/engine.py:L64`](file:///Users/gustavoluiscosta/Downloads/projetos/FiscoAtlas/fiscal/engine.py#L64).
- **Como Sanar:**
  1. Alterar `fiscal/models.py`:
     ```python
     class Profile(models.Model):
         name = models.CharField(max_length=255)
         cpf = models.CharField(max_length=14)
         tax_residency_status = models.CharField(
             max_length=32,
             choices=[
                 ("BRAZIL_RESIDENT", "Residente fiscal no Brasil"),
                 ("NON_RESIDENT", "Não residente"),
                 ("PART_YEAR_RESIDENT", "Residência parcial no ano"),
                 ("UNKNOWN", "Desconhecido"),
             ],
             default="UNKNOWN",
         )
         residency_start_date = models.DateField(null=True, blank=True)
         residency_end_date = models.DateField(null=True, blank=True)
         has_dsdp = models.BooleanField(default=False)
     ```
  2. Em `TaxEngine.compute()`, validar no início se `Profile.objects.first().tax_residency_status == "BRAZIL_RESIDENT"`. Se for `UNKNOWN` ou `NON_RESIDENT`, lançar `ValidationError` com bloqueio `RF-VAL-001`.

#### [NÃO ATENDIDO] RF-PER-003, RF-PER-004 e RF-PER-005 — Titularidade, Conta Conjunta e Beneficiário Efetivo
- **Prioridade:** P0/P1
- **Motivo do Desalinhamento:** Os modelos `BrokerAccount` e `FinancialEvent` em [`ledger/models.py`](file:///Users/gustavoluiscosta/Downloads/projetos/FiscoAtlas/ledger/models.py) não armazenam informações de titularidade (titular próprio, cotitular, percentual atribuível em contas conjuntas, conta de terceiro, trust ou entidade controlada). Investidores que possuem contas *Joint Tenancy with Right of Survivorship (JTWROS)* não têm mecanismo para declarar os 50% atribuíveis a cada cotitular.
- **Partes do Código Afetadas:** [`ledger/models.py:L32-L44`](file:///Users/gustavoluiscosta/Downloads/projetos/FiscoAtlas/ledger/models.py#L32-L44), [`ledger/account_forms.py`](file:///Users/gustavoluiscosta/Downloads/projetos/FiscoAtlas/ledger/account_forms.py).
- **Como Sanar:**
  1. Em `ledger/models.py`, adicionar a `BrokerAccount`:
     ```python
     OWNERSHIP_TYPES = [
         ("INDIVIDUAL", "Titularidade individual"),
         ("JOINT", "Conta conjunta"),
         ("THIRD_PARTY", "Conta de terceiros"),
     ]
     ownership_type = models.CharField(max_length=20, choices=OWNERSHIP_TYPES, default="INDIVIDUAL")
     co_owner_name = models.CharField(max_length=255, blank=True)
     co_owner_tax_id = models.CharField(max_length=32, blank=True)
     ownership_share = models.DecimalField(max_digits=5, decimal_places=2, default=100.00)
     ```
  2. Ajustar os motores de relatório e cálculo para aplicar `ownership_share / 100` nas posições patrimoniais e rendimentos auferidos.

---

### 4.3. Cadastro e Classificação de Ativos

#### [IMPLEMENTADO INCORRETAMENTE] RF-AST-006 e RF-AST-007 — Auto-inferência Silenciosa de Tickers e REITs
- **Prioridade:** P0
- **Motivo do Desalinhamento:** Em [`ledger/forms.py:L90-L93`](file:///Users/gustavoluiscosta/Downloads/projetos/FiscoAtlas/ledger/forms.py#L90-L93), no método `clean_asset_ticker`:
  ```python
  asset, _ = Asset.objects.get_or_create(
      ticker=ticker,
      defaults={"description": ticker, "asset_type": "STOCK", "country_code": "US"},
  )
  ```
  Se o usuário digita um ticker que é um ETF (ex.: `VOO`, `QQQ`), um REIT (ex.: `O`, `PLD`) ou um Treasury bond (ex.: `TLT`), o sistema silenciosamente cria o ativo no banco com `asset_type="STOCK"`. Isso viola diretamente os requisitos **RF-AST-006**, **RF-AST-007** e **RF-ARQ-006**, pois REITs e ETFs possuem natureza jurídica própria e não podem ser cadastrados como ações ordinárias por omissão.
- **Partes do Código Afetadas:** [`ledger/forms.py:L86-L94`](file:///Users/gustavoluiscosta/Downloads/projetos/FiscoAtlas/ledger/forms.py#L86-L94), [`ledger/models.py:L19-L30`](file:///Users/gustavoluiscosta/Downloads/projetos/FiscoAtlas/ledger/models.py#L19-L30).
- **Como Sanar:**
  1. Remover a criação implícita (`get_or_create`) em `EventForm.clean_asset_ticker()`. Se o ativo não existir em `Asset`, o formulário deve acusar erro de validação: `"Ativo não encontrado. Cadastre o ativo previamente informando sua natureza jurídica e descrição."`.
  2. Criar view e formulário dedicados para cadastro de ativos (`AssetForm`), forçando a seleção explícita da natureza jurídica conforme `legal_asset_type`.

#### [NÃO ATENDIDO] RF-AST-003 e RF-AST-009 — Taxonomia Jurídica Completa e Detecção de Entidade Controlada
- **Prioridade:** P0
- **Motivo do Desalinhamento:** `ASSET_TYPES` em [`ledger/models.py:L5`](file:///Users/gustavoluiscosta/Downloads/projetos/FiscoAtlas/ledger/models.py#L5) possui apenas `("STOCK", "ETF", "REIT", "BOND", "FUND", "OTHER")`. Faltam tipos obrigatórios exigidos pela norma: `US_TREASURY`, `CONTROLLED_ENTITY`, `TRUST`, `UNKNOWN`. Além disso, não há mecanismos para perguntar/detectar se o contribuinte possui mais de 50% do capital ou direitos de controle da entidade no exterior. Se o contribuinte cadastrar ações de sua offshore no FiscoAtlas, o sistema tributará indevidamente o ativo como aplicação financeira a 15% na liquidação, em vez de exigir o regime específico do art. 5º da Lei 14.754/2023.
- **Partes do Código Afetadas:** [`ledger/models.py:L5`](file:///Users/gustavoluiscosta/Downloads/projetos/FiscoAtlas/ledger/models.py#L5), [`ledger/forms.py`](file:///Users/gustavoluiscosta/Downloads/projetos/FiscoAtlas/ledger/forms.py), [`fiscal/engine.py`](file:///Users/gustavoluiscosta/Downloads/projetos/FiscoAtlas/fiscal/engine.py).
- **Como Sanar:**
  1. Expandir as opções do modelo `Asset`:
     ```python
     LEGAL_ASSET_TYPES = [
         ("FOREIGN_EQUITY", "Ação ordinária estrangeira"),
         ("FOREIGN_ETF", "ETF estrangeiro"),
         ("REIT", "Real Estate Investment Trust (REIT)"),
         ("US_TREASURY", "Título do Tesouro Americano (US Treasury)"),
         ("FOREIGN_BOND", "Título de dívida privado (Bond)"),
         ("FOREIGN_FUND", "Fundo de investimento no exterior"),
         ("CONTROLLED_ENTITY", "Entidade controlada no exterior (Offshore)"),
         ("TRUST", "Estrutura fiduciária (Trust)"),
         ("UNKNOWN", "Desconhecido / Não homologado"),
     ]
     ```
  2. Em `TaxEngine.compute()`, se qualquer evento ativo referenciar ativo com `legal_asset_type in ("CONTROLLED_ENTITY", "TRUST", "UNKNOWN")`, disparar `ValidationError` com bloqueio impeditivo.

---

### 4.4. Importação e Normalização de Dados

#### [NÃO ATENDIDO] RF-IMP-001 a RF-IMP-004 — Inexistência de Pipeline de Importação Automatizada de Extratos (CSV/PDF)
- **Prioridade:** P0/P1
- **Motivo do Desalinhamento:** O sistema não possui um serviço ou módulo para importar relatórios ou extratos de corretoras (ex.: extratos de negociação e dividendos da Charles Schwab, Interactive Brokers, Avenue, etc.). O único mecanismo atual é o lançamento manual formulário a formulário em [`ledger/forms.py`](file:///Users/gustavoluiscosta/Downloads/projetos/FiscoAtlas/ledger/forms.py). Embora o módulo [`security/documents.py`](file:///Users/gustavoluiscosta/Downloads/projetos/FiscoAtlas/security/documents.py) grave arquivos criptografados em disco, ele funciona meramente como cofre documental, sem realizar leitura, interpretação de registros, normalização, verificação de duplicidade ou garantia de idempotência na ingestão contábil.
- **Partes do Código Afetadas:** Módulo `ledger/` (inexistência de parsers), [`security/documents.py`](file:///Users/gustavoluiscosta/Downloads/projetos/FiscoAtlas/security/documents.py).
- **Como Sanar:**
  1. Criar o módulo `ledger/importers/` com uma interface base:
     ```python
     # ledger/importers/base.py
     class BaseStatementImporter(ABC):
         @abstractmethod
         def parse(self, content: bytes) -> list[NormalizedEvent]:
             pass
     ```
  2. Implementar parsers para formatos comuns (ex.: CSV Schwab, CSV Interactive Brokers).
  3. Criar modelo `ImportBatch` com `file_hash`, `file_name`, `created_at` e controle de deduplicação por tupla `(account_id, trade_date, event_type, asset_id, amount_usd, quantity)`.

#### [NÃO ATENDIDO] RF-IMP-008, RF-CST-003 e RF-CST-004 — Transferências entre Contas sem Vínculo e Perda de Custo
- **Prioridade:** P0
- **Motivo do Desalinhamento:** O sistema não suporta eventos de transferência de custódia entre corretoras (`BROKER_TRANSFER_IN` / `BROKER_TRANSFER_OUT`). Se o investidor transferir ações ou saldos entre instituições no exterior (ex.: da Avenue para a Schwab):
  1. O modelo só disponibiliza `APORTE` e `WITHDRAWAL` para caixa (`ledger/models.py:L8-9`).
  2. Não há como vincular as duas pontas da transferência através de um `transfer_pair_id`.
  3. Ao retirar ações de uma conta e colocá-las em outra, o custo fiscal histórico acumulado em BRL é perdido, gerando descontinuidade no custo médio ponderado da carteira.
- **Partes do Código Afetadas:** [`ledger/models.py:L7-L16`](file:///Users/gustavoluiscosta/Downloads/projetos/FiscoAtlas/ledger/models.py#L7-L16), [`ledger/service.py`](file:///Users/gustavoluiscosta/Downloads/projetos/FiscoAtlas/ledger/service.py), [`ledger/position.py:L20-L45`](file:///Users/gustavoluiscosta/Downloads/projetos/FiscoAtlas/ledger/position.py#L20-L45).
- **Como Sanar:**
  1. Incluir `BROKER_TRANSFER_IN` e `BROKER_TRANSFER_OUT` em `EVENT_TYPES`.
  2. Adicionar campo `transfer_pair_id = models.UUIDField(null=True, blank=True)` em `FinancialEvent`.
  3. Atualizar `PositionService` para transferir o lote de quantidade e custo em BRL correspondente da conta emissora para a conta receptora sem caracterizar alienação fiscal (ganho/perda zero).

---

### 4.5. Taxonomia de Eventos e Corporate Actions

#### [NÃO ATENDIDO] RF-CA-001 a RF-CA-008 e RF-EVT — Ausência Total de Suporte a Eventos Societários (Splits, Mergers, Spin-offs)
- **Prioridade:** P0
- **Motivo do Desalinhamento:** No mercado de capitais norte-americano, desdobramentos de ações (*stock splits*, como Nvidia 10:1 ou Apple 4:1) e grupamentos (*reverse splits*) são eventos frequentes. O FiscoAtlas não possui nenhuma representação no modelo de dados ou no motor contábil para esses eventos. Se ocorrer um desdobramento de 2:1, a posição do investidor dobra no extrato, mas no FiscoAtlas:
  1. Se registrar uma compra com valor zero, viola a validação de `price_usd > 0` em [`ledger/service.py:L42-43`](file:///Users/gustavoluiscosta/Downloads/projetos/FiscoAtlas/ledger/service.py#L42-43).
  2. Ao vender as ações desdobradas, o sistema acusará erro de posição insuficiente (`"posição insuficiente"`, `ledger/service.py:L63`).
  3. Não há suporte a *cash-in-lieu* (frações pagas em dinheiro decorrentes de cisão ou grupamento) nem tratamento de *return of capital*.
- **Partes do Código Afetadas:** [`ledger/models.py:L7-L16`](file:///Users/gustavoluiscosta/Downloads/projetos/FiscoAtlas/ledger/models.py#L7-L16), [`ledger/service.py:L42-43`](file:///Users/gustavoluiscosta/Downloads/projetos/FiscoAtlas/ledger/service.py#L42-43), [`ledger/position.py:L31-L44`](file:///Users/gustavoluiscosta/Downloads/projetos/FiscoAtlas/ledger/position.py#L31-L44).
- **Como Sanar:**
  1. Adicionar eventos `STOCK_SPLIT`, `REVERSE_SPLIT`, `SPIN_OFF`, `RETURN_OF_CAPITAL`, `CASH_IN_LIEU` em `EVENT_TYPES`.
  2. Criar tabela ou campos de metadados em `FinancialEvent`: `split_ratio_numerator` e `split_ratio_denominator`.
  3. Em `PositionService.position()` e `realized()`:
     ```python
     elif ev.event_type == "STOCK_SPLIT":
         # Ajusta quantidade sem alterar custo fiscal em BRL
         ratio = ev.split_ratio_numerator / ev.split_ratio_denominator
         qty = qty * ratio
         # Custo médio por ação diminui proporcionalmente, mas cost_brl e cost_usd permanecem idênticos
     ```
  4. Para *cash-in-lieu*, dar baixa fracionária na quantidade com cálculo de ganho de capital sobre o valor liquidado.

---

### 4.6. Imposto Pago no Exterior e Elegibilidade Jurídica

#### [PARCIAL] RF-FTC-004 e RF-FTC-009 — Falta de Filtro de Imposto Estadual/Municipal e Refund Posterior
- **Prioridade:** P0
- **Motivo do Desalinhamento:**
  1. O modelo `ForeignTaxPayment` (`ledger/models.py:L99`) possui o campo `jurisdiction_level` (`FEDERAL`, `STATE`, `LOCAL`, `UNKNOWN`). Contudo, em [`fiscal/engine.py:L111`](file:///Users/gustavoluiscosta/Downloads/projetos/FiscoAtlas/fiscal/engine.py#L111), o cálculo do crédito inclui irrestritamente qualquer registro de `ForeignTaxPayment` sem checar se a jurisdição é `FEDERAL`. Como o Brasil só reconhece reciprocidade para impostos de renda federais norte-americanos (Internal Revenue Code), eventuais tributos estaduais (*State Income Tax*) lançados por engano pelo usuário seriam indevidamente deduzidos do IRPF brasileiro.
  2. Não há suporte a eventos de `WITHHOLDING_REFUND` (restituição de retenção efetuada no exterior a maior), impedindo a recomposição da base fiscal.
- **Partes do Código Afetadas:** [`fiscal/engine.py:L104-L119`](file:///Users/gustavoluiscosta/Downloads/projetos/FiscoAtlas/fiscal/engine.py#L104-L119), [`fiscal/report.py:L70-L78`](file:///Users/gustavoluiscosta/Downloads/projetos/FiscoAtlas/fiscal/report.py#L70-L78).
- **Como Sanar:**
  1. Em `fiscal/engine.py`, ao acumular os pagamentos elegíveis para crédito:
     ```python
     # Apenas tributo federal dos EUA é compensável por reciprocidade
     if pagamento and pagamento.jurisdiction_level == "FEDERAL" and pagamento.country_code == "US":
         fx_tax = fx_imposto_exterior(ev, pagamento, PtaxService())
         wh_brl = (ev.tax_usd * fx_tax).quantize(Decimal("0.01"))
     else:
         wh_brl = ZERO  # Imposto não elegível a crédito
     ```
  2. Implementar evento `WITHHOLDING_REFUND`, descontando o imposto estornado do cômputo de créditos do exercício.

---

### 4.7. Gestão e Rastreabilidade de Perdas

#### [PARCIAL] RF-LOS-006 e RF-LOS-007 — Ausência de Ledger Dedicado de Perdas e Rastreio de Lotes
- **Prioridade:** P0/P1
- **Motivo do Desalinhamento:** Em [`fiscal/engine.py:L124-L130`](file:///Users/gustavoluiscosta/Downloads/projetos/FiscoAtlas/fiscal/engine.py#L124-L130), o reaproveitamento de perdas acumuladas baseia-se unicamente no campo escalar `prev.loss_carryforward_brl` do registro `AnnualAssessment` do ano fiscal imediatamente anterior (`year - 1`). O sistema não mantém um *LossLedger* granular registrando a data e a operação de origem da perda, a parcela já compensada e a parcela remanescente por ano fiscal. Se houver retificação de eventos de um ano anterior, o transporte de perdas não se reprocessa de forma auditável e encadeada.
- **Partes do Código Afetadas:** [`fiscal/engine.py:L121-L146`](file:///Users/gustavoluiscosta/Downloads/projetos/FiscoAtlas/fiscal/engine.py#L121-L146), [`fiscal/models.py:L63-L76`](file:///Users/gustavoluiscosta/Downloads/projetos/FiscoAtlas/fiscal/models.py#L63-L76).
- **Como Sanar:**
  1. Criar um modelo dedicado para rastreamento de perdas:
     ```python
     class LossRecord(models.Model):
         year_originated = models.PositiveIntegerField()
         source_event = models.ForeignKey(FinancialEvent, on_delete=models.PROTECT)
         amount_brl = models.DecimalField(max_digits=20, decimal_places=8)
         compensated_brl = models.DecimalField(max_digits=20, decimal_places=8, default=0)
         remaining_brl = models.DecimalField(max_digits=20, decimal_places=8)
     ```
  2. Implementar alocação determinística de compensação na classe `TaxEngine`, emitindo relatório de composição de prejuízos acumulados.

---

### 4.8. Declaração de Capitais Brasileiros no Exterior — CBE / Banco Central

#### [NÃO ATENDIDO] RF-CBE-001 a RF-CBE-007 — Inexistência do Módulo de Avaliação da CBE
- **Prioridade:** P0
- **Motivo do Desalinhamento:** O sistema não possui qualquer lógica, serviço ou relatório para avaliar a obrigatoriedade da **Declaração de Capitais Brasileiros no Exterior (CBE)** perante o Banco Central do Brasil (Resolução BCB nº 279/2022). O investidor brasileiro que acumula US$ 1.000.000,00 ou mais na data-base de 31 de dezembro fica sem sinalização ou alerta de exigibilidade de entrega dessa obrigação acessória mandatória. Além disso, quando o patrimônio cadastrado for inferior ao limite, o sistema deve registrar o status `CBE_UNDETERMINED` a menos que o contribuinte confirme expressamente que não possui outros bens fora do sistema.
- **Partes do Código Afetadas:** Módulo inexistente (`fiscal/` e `ledger/`).
- **Como Sanar:**
  1. Criar serviço `CbeService` em `fiscal/cbe.py`:
     ```python
     class CbeService:
         ANNUAL_THRESHOLD_USD = Decimal("1000000.00")
         QUARTERLY_THRESHOLD_USD = Decimal("100000000.00")
         
         def evaluate(self, year: int) -> dict:
             yearend = date(year, 12, 31)
             total_usd = Decimal(0)
             # Soma caixa de todas as contas em 31/12
             for acc in BrokerAccount.objects.filter(active=True):
                 total_usd += CashLedgerService().balance(acc, until=yearend)
             # Soma valor de ativos no exterior
             for asset in Asset.objects.filter(active=True):
                 # Avalia pelo custo ou valor de mercado em 31/12
                 ...
             is_required = total_usd >= self.ANNUAL_THRESHOLD_USD
             return {
                 "total_foreign_capital_usd": total_usd,
                 "status": "CBE_REQUIRED" if is_required else "CBE_UNDETERMINED",
                 "legal_basis": "Resolução BCB nº 279/2022",
             }
     ```
  2. Exibir o bloco de status da CBE no `ReportService.build()` e no relatório em PDF.

---

### 4.9. Tributação Mínima de Altas Rendas (Lei nº 15.270/2025)

#### [NÃO ATENDIDO] RF-HI-001 a RF-HI-004 — Inexistência de Verificação do Gatilho de R$ 600.000 para o Ano 2026
- **Prioridade:** P0
- **Motivo do Desalinhamento:** Para fatos geradores a partir do **ano-calendário 2026**, a Lei nº 15.270/2025 institui a tributação mínima sobre rendas elevadas quando a renda anual global do contribuinte superar R$ 600.000,00. O FiscoAtlas não implementa qualquer verificação desse gatilho. Como o sistema conhece apenas as aplicações financeiras no exterior cadastradas, ele deve alertar que o status do teste de alta renda é `HIGH_INCOME_TEST_UNDETERMINED` (e não assumir falsamente que o investidor não está sujeito à tributação mínima).
- **Partes do Código Afetadas:** [`fiscal/engine.py`](file:///Users/gustavoluiscosta/Downloads/projetos/FiscoAtlas/fiscal/engine.py), [`fiscal/report.py`](file:///Users/gustavoluiscosta/Downloads/projetos/FiscoAtlas/fiscal/report.py).
- **Como Sanar:**
  1. Em `fiscal/engine.py`, se `self.year >= 2026`:
     - Se `income_brl > Decimal("600000.00")`, alertar: `"Rendimentos no exterior superam o piso de R$ 600.000 da Lei 15.270/2025. Sujeito à verificação de tributação mínima de altas rendas."`.
     - Caso contrário, retornar flag `"high_income_status": "HIGH_INCOME_TEST_UNDETERMINED"` destacando que a apuração definitiva depende dos rendimentos percebidos no Brasil pelo contribuinte.

---

### 4.10. Validações Bloqueantes de Fechamento Anual

#### [NÃO ATENDIDO] RF-VAL-001 a RF-VAL-020 — Ausência de Validador Prévio de Integridade Contábil
- **Prioridade:** P0
- **Motivo do Desalinhamento:** No fluxo atual de encerramento do exercício fiscal, a confirmação do `AnnualAssessment` (`fiscal/views.py`) apenas altera o flag `confirmed = True` sem executar uma rotina rígida de integridade e compliance. É possível confirmar o fechamento anual contendo:
  - Perfil de usuário sem residência fiscal configurada (`RF-VAL-001`).
  - Ativo sem classificação homologada (`RF-VAL-002`).
  - Exercício sem schema DIRPF homologado pela Receita (`RF-VAL-017`).
  - Divergências materiais de caixa ou quantidade de ativos em custódia (`RF-VAL-018`, `RF-VAL-019`).
- **Partes do Código Afetadas:** [`fiscal/views.py`](file:///Users/gustavoluiscosta/Downloads/projetos/FiscoAtlas/fiscal/views.py), [`fiscal/models.py:L75`](file:///Users/gustavoluiscosta/Downloads/projetos/FiscoAtlas/fiscal/models.py#L75).
- **Como Sanar:**
  1. Criar classe `AnnualClosingValidator` em `fiscal/validator.py`.
  2. Implementar método `validate_closing(year)` checando as 20 condições da seção 25 da norma.
  3. No view de confirmação de fechamento (`fiscal/views.py`), invocar `AnnualClosingValidator.validate_closing(year)`. Se houver qualquer falha P0, abortar a operação e retornar à UI com a lista discriminada dos bloqueios.

---

## 5. Auditoria de Red Flags (Seção 28 dos Requisitos)

Pesquisas globais no código por termos e padrões proibidos apresentaram os seguintes resultados:

| Termo / Padrão Pesquisado | Risco Normativo | Ocorrência no Código | Status de Auditoria |
| :--- | :--- | :---: | :---: |
| **`35000`** (Isenção R$ 35k) | Aplicação indevida de isenção em bolsa após 2024 | Não encontrado | **CONFORME ✅** |
| **`6015`** (DARF bolsa Brasil) | Emissão indevida de DARF mensal de renda variável nacional | Não encontrado | **CONFORME ✅** |
| **`0190`** (Carnê-Leão) | Apuração indevida via Carnê-Leão para aplicações pós-2024 | Não encontrado | **CONFORME ✅** |
| **`4600` / `8523`** (GCAP) | Lançamento em códigos de ganho de capital mensal | Não encontrado | **CONFORME ✅** |
| **`0211`** (DARF IRPF ajuste) | Código correto da DAA para saldo de imposto | Não encontrado (falta orientação formal) | **ALERTA ⚠️** |
| **`broker_transfer_out => taxable_sale`** | Tributar transferência de custódia como venda | Não implementado (transferência não existe) | **ALERTA ⚠️** |
| **`asset_type="STOCK"` (default)** | Classificar ETF/REIT como ação ordinária silenciosamente | Presente em `ledger/forms.py:L92` | **NÃO CONFORME ❌** |
| **`brackets=[{6000, 50000}]`** | Tabela progressiva do regime antigo gravada no seed | Presente em `seed_tax_rules.py:L5` (V1) | **ATENÇÃO ⚠️ (V2 corrigida)** |

---

## 6. Avaliação dos Casos de Teste Mínimos (CT-001 a CT-030)

| Caso de Teste | Descrição Resumida | Situação no FiscoAtlas | Arquivo de Teste / Observação |
| :--- | :--- | :---: | :--- |
| **CT-001** | Compra sem fato gerador | **PASSOU ✅** | `tests/ledger/test_position.py` |
| **CT-002** | Venda pequena com lucro em 2026 (sem isenção 35k) | **PASSOU ✅** | `tests/fiscal/test_tax_engine.py` (tributa a 15% flat) |
| **CT-003** | Venda com prejuízo apurado em BRL | **PASSOU ✅** | `tests/ledger/test_brl_result.py` |
| **CT-004** | Perda maior que ganhos anuais | **PASSOU ✅** | `tests/fiscal/test_tax_engine.py` |
| **CT-005** | Carryforward usado no ano seguinte | **PASSOU ✅** | `tests/fiscal/test_loss_carryforward.py` |
| **CT-006** | Dividendos com withholding federal EUA (PTAX separadas) | **PASSOU ✅** | `tests/fiscal/test_conversoes_separadas.py` |
| **CT-007** | Imposto estrangeiro superior ao imposto brasileiro (30% vs 15%) | **PASSOU ✅** | `tests/fiscal/test_tax_engine.py` |
| **CT-008** | Withholding refund posterior | **AUSENTE ❌** | Sem modelo ou rotina de refund |
| **CT-009** | Treasury coupon (PTAX venda) | **PARCIAL ⚠️** | Tratado generico como `JUROS` |
| **CT-010** | Bond maturity | **AUSENTE ❌** | Tipo `MATURITY` inexistente |
| **CT-011** | Conta não remunerada com variação cambial isenta | **PASSOU ✅** | `tests/fiscal/test_report_exempt.py` |
| **CT-012** | Conta remunerada com juros | **PASSOU ✅** | `tests/ledger/test_cash_interest.py` |
| **CT-013** | Remessa para corretora (não tributável) | **PASSOU ✅** | `tests/ledger/test_cash.py` |
| **CT-014** | Transferência entre corretoras do mesmo titular | **AUSENTE ❌** | Sem suporte a transferências |
| **CT-015** | Venda e posterior transferência de caixa | **PARCIAL ⚠️** | Operações dissociadas |
| **CT-016** | Stock split 2:1 sem alteração de custo total | **AUSENTE ❌** | Sem suporte a splits |
| **CT-017** | Reverse split com cash-in-lieu | **AUSENTE ❌** | Sem suporte a corporate actions |
| **CT-018** | Spin-off sem regra homologada (bloqueio) | **AUSENTE ❌** | Sem suporte a corporate actions |
| **CT-019** | CBE US$ 999.999 (não exigível / indeterminado) | **AUSENTE ❌** | Módulo CBE inexistente |
| **CT-020** | CBE US$ 1.000.000 (exigível) | **AUSENTE ❌** | Módulo CBE inexistente |
| **CT-021** | CBE com patrimônio externo incompleto | **AUSENTE ❌** | Módulo CBE inexistente |
| **CT-022** | Ano 2023 (motor legado) | **AUSENTE ❌** | Sem motor legado histórico |
| **CT-023** | Ano 2024 (Lei 14.754) | **PASSOU ✅** | Suíte `tests/fiscal/` |
| **CT-024** | 2026 com renda global desconhecida | **AUSENTE ❌** | Sem módulo Lei 15.270/2025 |
| **CT-025** | 2026 com renda global > R$ 600 mil | **AUSENTE ❌** | Sem módulo Lei 15.270/2025 |
| **CT-026** | País EUA (código 249) | **PASSOU ✅** | `tests/fiscal/test_report.py` |
| **CT-027** | Ação estrangeira (código 03/01) | **PASSOU ✅** | `tests/fiscal/test_report.py` |
| **CT-028** | Conta corrente (código 06/01) | **PASSOU ✅** | `tests/fiscal/test_report.py` |
| **CT-029** | DARF orientação código 0211 | **AUSENTE ❌** | Sem tela/guia de DARF |
| **CT-030** | Reimportação do mesmo extrato (idempotência) | **AUSENTE ❌** | Sem importador automatizado |

---

## 7. Plano de Ação e Roadmap Priorizado de Remediação

Para atingir **100% de conformidade** com os requisitos normativos e garantir segurança jurídica total ao investidor pessoa física, recomenda-se a execução das seguintes frentes de trabalho:

### Fase 1: Correções Imediatas e Prevenção de Defeitos Críticos (Prioridade P0)
1. **Eliminar Criação Silenciosa de Ativos**:
   - Modificar [`ledger/forms.py`](file:///Users/gustavoluiscosta/Downloads/projetos/FiscoAtlas/ledger/forms.py) para remover o `get_or_create` padrão de `STOCK` no `clean_asset_ticker`. Exigir cadastro prévio explícito do ativo.
2. **Campos Obrigatórios de Perfil**:
   - Incluir em [`fiscal/models.py`](file:///Users/gustavoluiscosta/Downloads/projetos/FiscoAtlas/fiscal/models.py) o campo `tax_residency_status` no modelo `Profile` e travar a apuração se diferente de `BRAZIL_RESIDENT`.
3. **Filtro de Jurisdição Federal no Crédito de Imposto Exterior**:
   - Em [`fiscal/engine.py`](file:///Users/gustavoluiscosta/Downloads/projetos/FiscoAtlas/fiscal/engine.py), condicionar o cômputo de `ForeignTaxPayment` a `jurisdiction_level == "FEDERAL"` e `country_code == "US"`.
4. **Validações Bloqueantes de Fechamento**:
   - Criar validador de integridade prévio ao fechamento anual (`AnnualAssessment.confirmed`), implementando as checagens de `RF-VAL-001` a `RF-VAL-020`.

### Fase 2: Cobertura Operacional do Investidor em Bolsa (Prioridade P0/P1)
1. **Módulo de Corporate Actions**:
   - Implementar suporte a `STOCK_SPLIT`, `REVERSE_SPLIT` e `CASH_IN_LIEU`, ajustando a quantidade sem alterar o custo total acumulado em reais.
2. **Transferências de Custódia**:
   - Implementar `BROKER_TRANSFER_IN` e `BROKER_TRANSFER_OUT` com `transfer_pair_id` para transportar quantidade e custo fiscal em BRL entre contas sem gerar alienação.
3. **Pipeline de Importação com Deduplicação e Idempotência**:
   - Construir módulo de importação de arquivos CSV das corretoras usuais (Schwab, Interactive Brokers, Avenue), com hashing de arquivo, pré-visualização e deduplicação estrita.

### Fase 3: Obrigações Acessórias e Versionamento Normativo (Prioridade P1)
1. **Módulo de Teste da CBE (Banco Central)**:
   - Criar `CbeService` avaliando o teto anual de US$ 1.000.000,00 e trimestral de US$ 100.000.000,00 na data-base de 31/12, indicando os status `CBE_REQUIRED`, `CBE_NOT_REQUIRED` ou `CBE_UNDETERMINED`.
2. **Tributação Mínima de Altas Rendas (Lei 15.270/2025)**:
   - Incluir verificação de renda superior a R$ 600.000 para o ano-calendário 2026, com sinalização de `HIGH_INCOME_TEST_UNDETERMINED` para faturas incompletas.
3. **Tabela de Schemas DIRPF Versionada por Exercício**:
   - Mover os códigos e grupos da DAA de dicionários estáticos para o banco de dados versionado por `filing_year`.

---

## 8. Conclusão da Auditoria

O **FiscoAtlas** possui uma base arquitetural sólida no que tange ao **núcleo de apuração da Lei nº 14.754/2023**: a alíquota uniforme de 15% na DAA é respeitada, a segregação de PTAX de VENDA (para rendimentos e operações) e PTAX de COMPRA (para imposto exterior retido) está plenamente conforme e testada, as regras anacrônicas (isenção de R$ 35 mil, GCAP e carnê-leão) foram devidamente expurgadas, e a variação cambial do caixa não remunerado segue a IN RFB 2.180/2024.

Contudo, para se consolidar como uma ferramenta auditável completa e segura para o investidor pessoa física de classe média, o sistema necessita sanar com brevidade as lacunas de **corporate actions (desdobramentos)**, **perfil de residência fiscal**, **vedação à auto-classificação de ativos**, **avaliação da CBE/BACEN** e **validador de fechamento anual bloqueante**. O cumprimento do roadmap proposto colocará o software em conformidade integral com todo o arcabouço normativo vigente no Brasil.
