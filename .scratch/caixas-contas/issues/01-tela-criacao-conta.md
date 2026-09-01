# 01: Tela de criação de caixa/conta

**What to build:** O usuário cadastra um caixa (conta de corretora) pela tela, definindo: apelido do caixa (nome livre, ex.: "Corrente Avenue", "Investimento"), corretora, número da conta, tipo (Cash/Custódia) e se é remunerada. A conta criada passa a aparecer no formulário de lançamentos e na tela de Caixa, identificada pelo apelido (com corretora/número como complemento).

**Blocked by:** None (can start immediately).

**Status:** resolved

- [ ] Tela "Contas" acessível pela navegação, com formulário de criação
- [ ] Campo apelido (nome do caixa) obrigatório; corretora e número obrigatórios; tipo e remuneração com valores padrão sensatos
- [ ] Modelo persiste o apelido (migração) sem perder as contas existentes
- [ ] Após criar, a conta aparece no select de "Conta" do novo lançamento e na tela de Caixa pelo apelido
- [ ] Formulário e telas em pt-BR, no design system atual (cards, labels, btn)
- [ ] Testes cobrem criação via POST e exibição do apelido no lançamento e no caixa
