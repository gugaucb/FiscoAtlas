# 03: Marcação legislativa nas telas de caixa

**What to build:** As telas comunicam o tratamento fiscal do caixa: a tela de Caixa marca contas não remuneradas como "caixa não remunerado — variação cambial isenta (IN RFB 2180/2024, art. 3º)" e o formulário de lançamento impede/avisa JUROS em conta não remunerada com mensagem amigável (a validação já existe no EventService; o objetivo é torná-la visível e clara na UI, sem mudar regra fiscal).

**Blocked by:** 01 (depende das telas/da marcação de remuneração na UI).

**Status:** resolved

- [ ] Tela de Caixa exibe selo textual "variação cambial isenta" para contas não remuneradas
- [ ] Tela de Caixa indica contas remuneradas (JUROS permitidos)
- [ ] POST de JUROS em conta não remunerada re-renderiza o formulário com mensagem clara (sem stack de erro), preservando os dados informados
- [ ] Nenhuma mudança no motor fiscal — apenas apresentação e mensagens
- [ ] Testes cobrem a mensagem de JUROS inválido via formulário e a exibição dos selos na tela de Caixa
