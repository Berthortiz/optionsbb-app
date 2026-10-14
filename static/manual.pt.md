# Manual do usuário · Options BB Centro de Comando

> Conteúdo educativo. Não é assessoria financeira nem fiscal. Operar ações e opções envolve risco de perda.

## 1. O que é este app
O Options BB Centro de Comando reúne em um só lugar: sinais de estratégias sobre suas ações, análise de cada ação, o módulo de **Covered Call** (calculadora e simulador), o módulo de **401(k) e aposentadoria**, o fluxo de volume para open interest das opções, rankings de estratégias, uma biblioteca de vídeos e mais. O que você vê depende do seu **plano** de assinatura.

## 2. Primeiros passos
1. **Crie sua conta**: escolha o plano com o qual quer fazer seu teste grátis (7 dias, sem cartão).
2. **Responda o questionário do Início** (4 perguntas). O app mostra um caminho com os módulos que mais combinam com você conforme seu perfil: Conservador, Moderado, Crescimento ou Ativo.
3. Quando o teste terminar, entre em **Planos** e assine para continuar usando o app. Sem assinatura ativa você só verá Planos e Conta.

## 3. O que cada plano inclui
| Módulo | Básico | Intermediário | Avançado |
|---|---|---|---|
| Início, Por onde começo?, Centro de Comando, Minhas listas, Análise | Sim | Sim | Sim |
| Covered Call | Sim | Sim | Sim |
| 401(k) e aposentadoria | Sim | Sim | Sim |
| Estratégias | 1 altista + 1 baixista | 6 + 6 | 10 + 10 |
| Meu ETF (3 ETFs Optionsbb e os seus), Dividendos, E se…? | Sim | Sim | Sim |
| Calculadora de opções | Não | Modelos | Modelos + pernas livres |
| Setores, Ranking, Desempenho | Não | Sim | Sim |
| Fluxo OI | Não | Não | Sim |
| Histórico de Earnings | Não | Não | Sim |
| Exposição gama (GEX) | Não | Não | Sim |
| Alavancados + Covered Call | Não | Não | Sim |
| Sinais de mentores | Não | Não | Sim |
| Estratégias personalizadas | Não | Não | 2 |
| Vídeos | Nível básico | Até o nível intermediário | Todos |

O menu só mostra o que seu plano inclui (assim fica mais curto e claro). O resto você vê em **Planos**.

## 4. Centro de Comando
- **Gráfico**: digite um símbolo e escolha a faixa (1D, 5D, 1M, 3M, 1Y). As setas marcam sinais recentes das estratégias escolhidas.
- **Estratégia altista / baixista**: escolha uma estratégia de cada lado. O painel central desenha o padrão e explica a regra. O número verde ou vermelho indica quantas ações têm sinal agora.
- **Listas dinâmicas**: ações com sinal agora, com preço e % de variação. Toque em um símbolo para vê-lo no gráfico.
- **Contratos com maior volume**: os contratos de opções mais negociados agora.
- **Listas de acompanhamento (Optionsbb)**: agora ficam em um menu próprio (veja a seção 4b).

## 4b. Minhas listas
Três quadros de 10 ações: **Lista Optionsbb · Baixo risco**, **Risco moderado** e **Alto risco**. Cada quadro tem duas abas: **Lista Optionsbb** (a seleção da Optionsbb) e **Minha lista** (sua, até 10 ações por nível de risco; você pode adicionar, remover ou clicar em *Copiar lista Optionsbb* para começar a partir dela). Por padrão você vê a variação de **Hoje**; marque os períodos que quiser: 7, 15, 30, 90, 180 e 360 dias. A partir de cada linha você abre a **Análise**.
Quando você adiciona uma empresa pela **Análise** (botão *+ Minha lista*), escolhe o nível de risco e o app leva você a **Minhas listas** para ver a empresa adicionada.

## 4c. Por onde começo?
Tela de boas-vindas: qual plataforma usar (**Thinkorswim da Charles Schwab**, com paperMoney para praticar sem risco), quanto dinheiro é necessário (100 ações por contrato de covered call) e o que se pode esperar de forma realista. Inclui os mitos de «fique rico em 3 semanas». No **Início** você também verá uma ilustração diferente conforme seu plano.

## 5. Análise de ação
Digite um símbolo e clique em **Analisar**. Você verá:
- **Variação** de Hoje, 7, 15, 30, 90 e 360 dias.
- **Resumo financeiro**: gráfico de 90 dias, posição na faixa de 52 semanas, distância da máxima e da mínima, volatilidade anual, maior queda do último ano, RSI, médias móveis, tendência e volume contra a média.
- **Por temporalidade** (5 min, 15 min, 30 min, 1 hora e diário): tendência, RSI e as estratégias com melhor histórico **nessa** ação. Uma etiqueta AGORA indica que a estratégia está ativa neste momento.
- Botões para ver o gráfico, adicionar à sua lista e **abrir o Covered Call com essa ação já carregada**.

> P/E, lucros, dividendos e capitalização serão adicionados ao vincular a conta Schwab. Hoje o resumo vem de preço, volume e opções.

## 6. Covered Call
Um covered call consiste em vender um contrato de opção call para cada 100 ações que você já tem. Você recebe um **prêmio** em troca de aceitar vender suas ações ao **strike** se, no vencimento, o preço o superar.

### 6.1 Calculadora
1. Digite o preço atual, seu custo por ação, o número de ações (múltiplos de 100) e as datas.
2. Cole a cadeia de **calls** do vencimento (colunas Strike, Bid, Ask e, opcionalmente, Delta, Volume e OI). No Thinkorswim: abra a cadeia, selecione as linhas de calls, copie e cole. Você também pode usar a opção **Um strike manual**.
3. Escolha qual strike vender: **1º** (o imediatamente acima do preço), **5º** ou outro número.
4. Clique em **Calcular**.

Ele mostra, em palavras: quanto você recebe, **a que preço você é exercido**, quanto subiu ou precisa subir, seu ganho máximo, o que você ganha se a ação não se mexer, o ponto de equilíbrio e um gráfico. A tabela de todos os strikes permite tocar em qualquer um para recalcular. Spread em vermelho significa que o bid e o ask estão muito afastados ou há pouco open interest: o prêmio real pode ser menor.

**Prêmio no Bid ou no ponto médio?** O Bid é o conservador. O ponto médio é o habitual ao colocar uma ordem limite, mas pode demorar a ser executado.

### 6.2 Como escolher o strike
- **Strike imediatamente superior**: você recebe mais prêmio, mas quase abre mão da alta e tem mais chance de ser exercido.
- **5º strike acima do preço**: você recebe menos, mas deixa a ação subir antes de bater no teto do seu ganho. Se você for exercido, o ganho máximo costuma ser maior.
- A calculadora compara os dois e diz **acima de que preço o 5º strike ganha**.
- Verifique se há **earnings** antes do vencimento: o preço pode saltar além de qualquer strike.

### 6.3 Simulador mensal
1. Informe a ação, as ações, o custo, a regra de strike e **por quantos meses** quer simular (1 a 36).
2. Clique em **Criar os meses**. Para cada mês digite data da venda, vencimento, preço na venda, a cadeia de calls, o strike que você vendeu (opcional) e o preço no vencimento.
3. Clique em **Simular**. Se em algum mês você for exercido, o app assume que você **recompra as ações** ao preço do mês seguinte e continua vendendo.
4. **Comparar 1º vs 5º strike** roda os dois cenários com os mesmos dados.
5. **Salvar simulação** a deixa na aba Salvas.

Resultado: ganho total, rendimento e anualizado, prêmios recebidos, vezes exercido, comparação com **apenas manter a ação**, maior queda e a alta que você deixou de ganhar.

> O exercício é avaliado apenas no vencimento. Na prática pode ocorrer antes, principalmente antes de um dividendo.

## 7. 401(k) e aposentadoria
O objetivo deste módulo é mostrar que **o dinheiro parado perde poder de compra** e comparar caminhos com seus próprios números.

- **Projeção**: compara **Dinheiro**, **Ações** e **Ações + Covered Call**, em dólares futuros ou em dólares de hoje. Se você informar seu salário e o que sua empresa contribui, ele calcula esse aporte (dinheiro grátis que não convém deixar passar).
- **Meta de aposentadoria**: dada a renda mensal que você quer (em dólares de hoje), calcula quanto você precisa poupar por mês em dinheiro e quanto investindo.
- **Taxas**: quanto custa pagar 1 % em vez de 0,1 % de taxa anual.
- **Minha carteira**: salve suas posições, veja valor e ganho, e clique em **Covered Call** em uma linha para abrir a calculadora com essa ação carregada.

Todos os rendimentos são **premissas que você edita**, não promessas. Limites do IRS para 2026: empregado em 401(k) $24,500 e IRA $7,500 (mudam a cada ano).

> Um 401(k) normal oferece um menu fixo de fundos. As opções (como o covered call) só podem ser usadas se seu plano tem uma janela de corretagem e sua corretora aprova opções. Numa IRA é mais comum. Consulte seu plano ou sua corretora.

## 7b. Meu ETF
Em cima você tem os **3 ETFs da Optionsbb** (Baixo risco, Risco moderado e Alto risco). Você escolhe um e, ao lado, vê a composição e a quantidade de ações. Esses ETFs **são fixos**: você só muda o **valor a investir** e as ações se ajustam na mesma proporção; somente o administrador pode alterar as ações deles. Para outra mistura, clique em **Criar meu ETF a partir deste**, ou crie um novo e use **Adicionar ações de outro ETF** (dos 3 da Optionsbb ou dos seus).
Monte seu próprio ETF: digite o símbolo, escolha se informa **ações** ou **dólares** e clique em *Adicionar*. Você pode ter até 5 ETFs com 20 ações cada.
- **Composição**: gráfico circular com o logo e o **% de peso** de cada ação (pelo valor atual). Se o logo não carregar, você verá as siglas.
- **Tabela de rendimento**: escolha o período (30 a 360 dias), a quantos % fora do dinheiro você vende a call e, se quiser, uma volatilidade própria. Para cada ação você verá: *sem covered call*, *covered call (renda)* e a **soma das 2**, além de se esteve **sem movimento** ou **em movimento**. Abaixo, subtotais e total do ETF.
- **Importante**: o covered call só cobre lotes de **100 ações** (se você tem 250, cobre 200). Os prêmios são estimados com um modelo; use-o para comparar, não como promessa.

## 7c. E se…? (O que teria acontecido se…)
Exemplos como **BYND** (ação que cai mês após mês) e **MSFT** (empresa sólida que fica parada ou recua): quanto o covered call teria gerado e que parte da perda teria amortecido. Os exemplos usam preços ilustrativos que **você pode trocar** pelos reais; você também pode usar o histórico de qualquer símbolo.

## 7d. Alavancados + Covered Call (Avançado)
NVDL, AMDL, TSLL, TQQQ e outros instrumentos alavancados com covered call. Inclui avisos de risco (reinício diário e decaimento por volatilidade), um simulador e uma calculadora de decaimento. São instrumentos de **alto risco**: apenas com dinheiro que você possa perder.

## 7e. Dividendos
Tabela das ações das suas listas com o rendimento anual, o pagamento por ação, a frequência e a renda anual com 100 ações. Nos planos Intermediário e Avançado você pode abrir o **histórico de pagamentos** de uma ação e seu crescimento anual. Com 100 ações você recebe o dividendo e ainda pode vender um covered call por mês: duas rendas sobre as mesmas ações. Os dados de pagamentos exigem as chaves de dados configuradas pelo administrador; no modo DEMO são simulados.

## 7f. Idioma
No canto superior direito escolha **ES**, **EN** ou **PT**. Menus, títulos, tabelas, mensagens e este manual são traduzidos. Limitações: a tradução foi feita pelo Claude sem revisão de um falante nativo; os nomes de setores e de alguns símbolos ficam em inglês; os textos que você mesmo escreve (nomes de ETFs, estratégias, vídeos) não são traduzidos.

## 7g. Indicações
Abra **Referidos** (Indicações): copie seu código ou link. Quando alguém que você indicou **paga** a assinatura, você ganha 20% de desconto no mês seguinte. 10 indicações pagas = 6 meses grátis de Avançado; 20 = um ano grátis.

## 7h. Novidades 3.1
- **Dividendos**: calcule por número de ações ou valor a investir.
- **Earnings**: últimos 12 relatórios com tendência.
- **E se…?**: escolha um caso de estudo da lista ou salve o seu.
- **Estratégia personalizada**: cruzamento dourado, rompimento de alta/baixa, doji e vela envolvente.
- **Setores**: o administrador pode adicionar ou remover empresas.

## 8. Ferramentas
### Calculadora de opções (Intermediário e Avançado)
Escolha uma estratégia (call comprada, put comprada, covered call, put vendida com dinheiro, put protetora, travas, straddle, iron condor), o símbolo ou o preço, a volatilidade e os dias até o vencimento. Você verá o **custo ou crédito**, o **ganho e a perda máximos**, os **pontos de equilíbrio**, a **probabilidade de ganhar** e as **gregas**, com um gráfico no vencimento e a curva de «hoje». No Avançado você pode montar até 6 **pernas livres** e digitar seu próprio prêmio. Os prêmios são estimados com Black-Scholes.
### Histórico de Earnings (Avançado)
Escolha uma ação e você verá como o preço se moveu em cada relatório anterior: gap de abertura, variação do dia, faixa e dia seguinte, além do movimento médio. Tudo é calculado **automaticamente** com as datas dos relatórios (Finnhub) e os preços (Schwab); nada é digitado à mão.
### Exposição gama – GEX (Avançado)
Mostra por strike a exposição gama de calls e puts para um vencimento, a **parede de calls** (possível resistência), a **parede de puts** (possível suporte), o **gamma flip** e se o regime é de gama positiva (movimentos mais contidos) ou negativa (movimentos mais amplos). É uma estimativa com uma premissa sobre a posição dos dealers.

## 8b. Mercado
### Fluxo OI (somente Avançado)
Compara o volume de opções de um dia com o open interest da manhã seguinte. Se o OI sobe muito em relação ao volume, provavelmente foram **abertas** posições novas; se cai, foram **fechadas**. Não distingue compra de venda.
### Setores
As ações-chave de cada setor com preço, % de variação, relação puts/calls e sinais.
### Ranking
Mostra as estratégias **mais eficazes por temporalidade** (5 min, 15 min, 30 min, 1 hora e diário). Cada sinal é medido pela variação do preço 5 velas depois. Você verá sinais, % de acertos, rendimento médio, fator de lucro, **em quais ações está ativa agora** e **em quais funcionou melhor**. Só entram estratégias com 20 sinais ou mais.
### Desempenho
Envie o relatório exportado do Thinkorswim (Strategy Report) e veja quão eficaz foi cada estratégia no backtest.

## 9. Sinais (Avançado)
- **Catálogo de estratégias**: estratégias por regras, com a lista de ações que as cumprem agora. Toque em **Seguir** para salvá-las.
- **Minha seleção**: reúne as estratégias que você segue (base, catálogo ou próprias) com seus sinais. Marque ou desmarque em “Escolha o que seguir”.
- **Minhas estratégias**: crie até 2 estratégias próprias com o construtor de regras: cruzamentos de médias, rompimentos, RSI, volume, cor da vela e variação de preço. Ativam-se quando **todas** as condições são cumpridas na mesma vela de 5 minutos.

## 10. Vídeos
Biblioteca de vídeos do canal do YouTube da Options BB. Filtre por categoria ou busque por título. Os vídeos de um nível superior aparecem com cadeado.

## 11. Planos e conta
- **Planos**: compare e assine. Você pode trocar de plano quando quiser.
- **Conta**: seu estado (teste, ativa, vencida), a data de renovação, gerenciar a assinatura e sair.

## 12. Para o administrador
- **Iniciar o app**: abra um console na pasta (no Explorador, clique na barra de endereços, digite `cmd` e Enter) e execute `python server.py`. Abra `http://127.0.0.1:8080`. Crie seu usuário com `python server.py create-admin voce@email.com`.
- **Usuários** (Conta): ativar dias pagos, estender o teste, revogar, trocar o plano ou tornar administrador.
- **Preços**: digite-os na tela Planos.
- **Vídeos**: adicione por link do YouTube, com categoria e plano mínimo.
- **Catálogo de sinais**: adicione as regras dos seus mentores com o nome deles.
- **Ações por setor**: envie o Excel em Conta → Dados e listas.
- **Relatório de Desempenho**: envie o arquivo exportado do Thinkorswim.
- **Dados reais**: vincule a Schwab em Conta → Conexão com a Schwab (a permissão dura 7 dias).
- **ETFs da Optionsbb**: o administrador pode alterar as ações e quantidades em Meu ETF → *Editar (administrador)*.
- **Earnings e dividendos**: configure as variáveis `FINNHUB_API_KEY` e `ALPHAVANTAGE_API_KEY` (planos gratuitos) para datas de relatórios e histórico de dividendos.
- **Taxas do banco e prêmios orientativos** das telas de boas-vindas: editam-se com o serviço de administrador `/api/admin/guide`.

## 13. Glossário
| Termo | Significado |
|---|---|
| Strike | Preço ao qual a opção pode ser exercida |
| Prêmio | Dinheiro que você recebe ao vender a opção |
| Exercida (assigned) | Compram suas ações ao strike |
| Equilíbrio | Preço abaixo do qual você começa a perder em um covered call |
| Bid / Ask | Preço ao qual compram / vendem no mercado |
| Delta | Aproximação da probabilidade de a opção terminar dentro do dinheiro |
| Open interest (OI) | Contratos em aberto |
| RSI | Indicador de força: acima de 70 sobrecomprada, abaixo de 30 sobrevendida |
| SMA | Média móvel simples |
| Fator de lucro | Ganhos totais divididos pelas perdas totais |

## 14. Problemas frequentes
- **“Windows can't find … cmd”**: não digite `cmd` com um arquivo selecionado. Clique num espaço vazio, pressione Ctrl + L, digite `cmd` e Enter.
- **O Windows bloqueia `iniciar.bat`**: abra um console na pasta e execute `python server.py`.
- **Dados simulados**: enquanto a Schwab não estiver vinculada, o app mostra dados de demonstração e avisa na barra amarela.
- **Não vejo um módulo**: tem cadeado porque é de um plano superior.
- **Uma ação não carrega**: confira o símbolo. Com dados reais, só funcionam símbolos que existam na Schwab.
