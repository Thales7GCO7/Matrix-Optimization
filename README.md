# Otimizador de Investimentos

Aplicação web (FastAPI + página HTML) que **aloca capital entre ativos de
retorno fixo** considerando taxas por período, imposto de renda, taxas de
administração e o **custo de oportunidade** (taxa mínima de atratividade),
calculando métricas de desempenho como ROI, VPL, TIR, payback e índice de
lucratividade.

## Visão geral

O problema: dado o **capital disponível** hoje e (opcionalmente) um **orçamento
mensal**, distribuir o dinheiro entre ativos com características diferentes para
maximizar a **riqueza final líquida** (após impostos e taxas de administração).

Matematicamente é um problema de programação linear com limites, pois o
rendimento real é **proporcional ao capital**. A solução ótima é encontrada por
**seleção gulosa**: investir primeiro nos ativos com maior **retorno líquido
anualizado** (após deduções), respeitando os limites mínimo e máximo de cada
ativo. O capital excedente, ou o capital que nenhum ativo consegue alocar acima
da taxa mínima, permanece em uma **reserva** rendendo exatamente a taxa mínima.

```
max Σ Lᵢ(xᵢ)          Lᵢ = riqueza final líquida do ativo i
s.t. Σ xᵢ ≤ B         capital inicial disponível
     Σ pᵢ ≤ B_mensal  aportes mensais disponíveis
     ℓᵢ ≤ xᵢ ≤ uᵢ     limites por ativo
```

## Modelo de ativos

Cada ativo é definido por:

- **Nome** e **mínimo/máximo** (inicial) de capital, além de um **máximo mensal**;
- **Taxa** do período com uma **base**:
  - *Efetiva*: a taxa do próprio período (composta). Ex.: 1% ao mês ≈ 12,68% a.a.
  - *Nominal*: taxa anual repartida pelo período. Ex.: 13% a.a. nominal com
    capitalização mensal usa 13%/12 = 1,083% ao mês.
- **Período de capitalização**: anual, semestral, trimestral, bimestral, mensal
  (semanal, diária);
- **Prazo até o resgate** (meses);
- **Imposto de renda** sobre os ganhos (alíquota genérica informada por ativo):
  `isento` (isento — ex. LCI/LCA, CRI/CRA, debêntures incentivadas) ou `fixo`
  (percentual fixo — ex. tabela regressiva do IR: 22,5%/20%/17,5%/15%
  conforme o prazo);
- **Taxa de administração**: sobre aportes, **% a.a. dos ativos** (taxa de gestão
  do fundo) ou sobre os ganhos (taxa de performance).

Há dois fluxos de aporte, combináveis por ativo:

- **Aporte inicial único** — alocação do capital disponível hoje;
- **Aporte mensal recorrente** (postecipado) — série uniforme até o resgate.

## Taxa mínima de atratividade

A taxa mínima é o **custo de oportunidade** do capital. Ela pode ser:

- informada manualmente; ou
- calculada como **taxa real**: `taxa_minima = (1 + taxa_livre_risco)/(1 + inflacao) - 1`,
  usando como padrão Selic + IPCA (benchmarks editáveis).

Ela é usada como:

- taxa de desconto do **VPL**;
- benchmark do **alpha** (excesso de retorno sobre a taxa mínima);
- taxa da **reserva** (o excedente rende a taxa mínima);
- base do **payback descontado** e da comparação "lucro vs. taxa mínima".

## Métricas de desempenho

Calculadas **por ativo** e **para a carteira**:

| Métrica | Definição |
|--------|-----------|
| **ROI** | `lucro líquido / capital investido` (retorno do período) |
| **ROI anualizado** | retorno equivalente por ano (CAGR/TIR), comparável entre prazos |
| **Retorno real** | retorno líquido anual descontado pela inflação (IPCA) |
| **VPL** | valor presente do fluxo de caixa descontado pela taxa mínima (`> 0` agrega valor) |
| **TIR** | taxa anual que zera o VPL (`>` taxa mínima é desejável) |
| **Payback** | mês em que o resgate recupera o capital (simples e descontado) |
| **IL** | `VPL / capital + 1` (`> 1` supera o custo de oportunidade) |
| **Alpha** | `ROI anual - taxa mínima` (excesso sobre o custo de oportunidade) |
| **Lucro na taxa mínima** | quanto o mesmo fluxo de aportes renderia à taxa mínima |
| **Lucro excedente** | `lucro da carteira - lucro na taxa mínima` |

## Como executar

```bash
pip install -r requirements.txt
uvicorn servidor:app --reload
```

(ou `python servidor.py`, que abre o navegador em `http://localhost:8000`).

Na página, configure o cenário (capital, taxa mínima, orçamento mensal), edite a
lista de ativos (ou carregue a carteira de exemplo) e clique em **Otimizar & ver painel**.
Os resultados chegam via `POST /api/otimizar`; os gráficos são renderizados no
servidor (matplotlib) como PNGs embutidos no JSON.

## Capturas de tela

> As capturas abaixo mostram versões anteriores em inglês; a interface atual é
> uma app de duas páginas em português voltada ao mercado brasileiro (painel +
> página de ativos). Continuam válidas como referência de layout.

### Cenário e taxa mínima

<img width="1343" height="399" alt="Cenário e taxa mínima" src="https://github.com/user-attachments/assets/2a5a1383-dd2f-434d-b950-983723221e87" />

### Ativos — exemplo: CD bancário 13% a.a. (nominal, capitalização mensal)

<img width="1051" height="487" alt="Ativos — CD bancário 13% a.a." src="https://github.com/user-attachments/assets/5fba7a3d-3420-4bac-a28a-eecc32d814ef" />

### Exemplo: título público SELIC (tabela de IR)

<img width="1063" height="353" alt="Título público SELIC (tabela de IR)" src="https://github.com/user-attachments/assets/6c816376-662e-49ed-ad94-87cafbd923ea" />

### Exemplo: título isento 9,5% a.a.

<img width="1062" height="346" alt="Título isento 9,5% a.a." src="https://github.com/user-attachments/assets/8a560d7a-6269-411d-a06e-794cb4b05552" />

### Exemplo: fundo de renda fixa (taxa de administração 1,5% a.a.)

<img width="1068" height="376" alt="Fundo de renda fixa (taxa de administração 1,5% a.a.)" src="https://github.com/user-attachments/assets/bc38357f-c34d-4e50-b31c-3a6fe8a4f544" />

## Demonstração

![Demonstração do Otimizador de Investimentos](/videos/demo.mp4)

> 3,1 MB (comprimido: 1280×720, H.264). Se não carregar, veja `videos/demo.mp4` no repositório.

## API

| Rota | Método | Descrição |
|------|--------|-----------|
| `/` | GET | Painel (página principal: KPIs, gráficos de pizza/barras/linhas, tabelas) |
| `/ativos` | GET | Entrada de dados dos ativos + página de cenário (executa a otimização) |
| `/api/exemplos` | GET | Carteira de exemplo para o formulário (`ativos[]`) |
| `/api/otimizar` | POST | Recebe `{capital_inicial, usar_mensal, aporte_mensal, modo_taxa_minima, taxa_livre_risco_pct, inflacao_pct, taxa_minima_manual_pct, ativos[]}` e retorna alocação, métricas por ativo, carteira e gráficos |

O payload do ativo espelha o formulário: `nome`, `rentabilidade_pct`, `periodo`
(`anual`, `semestral`, `trimestral`, `bimestral`, `mensal`, `semanal`, `diaria`),
`base` (`efetiva`, `nominal`), `prazo_meses`, `modo_imposto` (`isento`, `fixo`) /
`imposto_pct`, `modo_taxa` (`nenhuma`, `aporte`, `patrimonio`, `ganho`) / `taxa_pct`,
`minimo_inicial`/`maximo_inicial`, `usa_mensal`/`maximo_mensal`. Documentação
interativa em `/docs` (OpenAPI).

O `POST /api/otimizar` responde com:

- **carteira**: agregados por ativo (`valor_liquido`, `roi`, `vpl`, `tir_anual`,
  `payback`, `indice_lucratividade`, `alpha`) e totais da carteira
  (`capital_investido`, `reserva`, `roi`, `roi_anualizado`, `vpl`,
  `lucro_taxa_minima`);
- **metricas**: uma linha por ativo (inclui a reserva da taxa mínima) com a
  projeção mensal;
- **uso**: capital inicial investido, aportes mensais, reserva e lucro
  excedente vs. taxa mínima;
- **graficos**: 5 imagens PNG em base64 (`alocacao`, `alocacao_pizza`, `evolucao`,
  `lucro_vs_taxa_minima`, `pl_max`);
- **modelo_pl**: projeção do PL de 2 ativos — objetivo (`máx Z = c1*x1 + c2*x2`),
  fórmulas de lucro por ativo, retas de restrição, vértices com valores de Z,
  reta tangente, ótimo, alocação efetiva e passos de resolução;
- **avisos**: alertas de validação (ex.: sem capital, mínimos acima do capital).

Erros de negócio e de validação retornam `422` com `{"erro": ...}`.

## Estrutura do projeto

```
otimizador-investimentos/
├── servidor.py                   # API FastAPI (GET /, /api/exemplos, POST /api/otimizar)
├── requirements.txt              # Dependências
├── videos/
│   └── demo.mp4                  # Demonstração da página (3,1 MB, 1280×720)
├── src/
│   ├── matematica_financeira.py  # Conversão de taxas, capitalização, séries, TIR, taxa mínima
│   ├── impostos.py               # Lógica líquida genérica (calcular_valor_liquido/explicar) + impostos/taxas
│   ├── instrumentos.py           # Modelo de ativo (bruto → líquido) e projeção mensal
│   ├── desempenho.py             # Métricas: ROI, VPL, TIR, payback, IL, alpha
│   ├── otimizador_carteira.py    # Alocação ótima (gulosa) + reserva na taxa mínima
│   ├── geometria_pl.py           # Plano do PL de 2 ativos (restrições, vértices, ótimo, tangente)
│   └── otimizador_investimentos.py # Alocação não linear genérica (scipy SLSQP)
├── web/
│   ├── __init__.py               # Pacote vazio
│   ├── esquema.py                # Contrato da API (pydantic) e carteira de exemplo
│   ├── graficos.py               # Gráficos Matplotlib → PNG em base64
│   └── static/                   # Front-end (HTML/JS puro, sem CDN):
│       ├── index.html            # Painel (KPIs, gráficos de pizza/barras/linhas, tabelas)
│       ├── assets.html           # Entrada de ativos + formulário de cenário
│       └── app.js                # Utilitários, chamadas à API e renderização dos resultados
└── testes/
    ├── teste_matematica_financeira.py # Taxas, capitalização, séries, TIR, taxa mínima
    ├── teste_impostos.py         # Imposto de renda e taxas de administração
    ├── teste_geometria_pl.py     # Plano do PL: vértices, ótimo, tangente, gráfico
    ├── teste_desempenho.py       # Métricas por ativo e da carteira
    ├── teste_otimizador.py       # Alocação com limites, reserva, aportes mensais
    └── teste_servidor.py         # API: exemplos, otimização e erros (422)
```

## Testes

```bash
python -m unittest discover testes -v
```

Suíte com 71 testes cobrindo o núcleo de cálculo (taxas, impostos, séries, TIR,
taxa mínima), o plano do PL (vértices, ótimo, tangente, gráfico), a alocação
(limites, reserva, aportes mensais) e a camada de API via `TestClient`
(carteira de exemplo, taxa mínima manual e erros `422`).

## Stack tecnológica

- Python 3.12
- NumPy / SciPy (`brentq` para a TIR)
- FastAPI + Uvicorn (servidor HTTP)
- Matplotlib (gráficos PNG)
- Front-end em HTML/CSS/JS puro (sem framework, sem CDN)
