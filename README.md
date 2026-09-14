# Otimizador de Investimentos

Aplicação web (FastAPI + página HTML) que **aloca capital entre ativos de retorno fixo**
considerando taxas por período, imposto de renda, taxas administrativas e o **custo de
oportunidade** (TMA), calculando índices de desempenho como ROI, VPL, TIR, payback e índice de
lucratividade.

## Visão geral

O problema: dado um **capital disponível** hoje e (opcionalmente) uma **disponibilidade mensal**,
distribuir o dinheiro entre ativos com diferentes características para maximizar o **patrimônio
líquido final** (após imposto e taxas administrativas).

Matematicamente é um problema de programação linear com limites, pois a renda real é
**proporcional ao capital**. A solução ótima é obtida por **seleção otimizada**: aplica-se primeiro
nos ativos de maior **retorno líquido anualizado** (após deduções), respeitando os limites mínimo
e máximo de cada ativo. O capital que sobra, ou que não alcança a TMA, fica em uma **reserva** que
rende exatamente a taxa mínima.

```
max Σ Lᵢ(xᵢ)          Lᵢ = patrimônio líquido final do ativo i
s.a. Σ xᵢ ≤ B         capital inicial disponível
     Σ pᵢ ≤ B_mensal  aportes mensais disponíveis
     ℓᵢ ≤ xᵢ ≤ uᵢ     limites por ativo
```

## Caracterização dos ativos

Cada ativo é definido por:

- **Nome** e capital **mínimo/máximo** (inicial) e **máximo mensal**;
- **Taxa** do período com **base**:
  - *Efetiva*: taxa do próprio período (composta). Ex.: 1% a.m. ≈ 12,68% a.a.
  - *Nominal*: taxa anual dividida pelo período. Ex.: 13% a.a. nominal com capitalização mensal
    usa 13%/12 = 1,083% a.m.
- **Período de capitalização**: anual, semestral, trimestral, bimestral, mensal (semanal, diária);
- **Prazo até o resgate** (meses);
- **Imposto** sobre o rendimento: isento, percentual fixo ou **tabela regressiva do IR** de renda
  fixa brasileira (22,5% até 180 dias; 20% até 360; 17,5% até 720; 15% acima);
- **Taxa administrativa**: sobre o aporte, **% a.a. sobre o patrimônio** (taxa de administração de
  fundos) ou sobre o rendimento (performance fee).

Há dois fluxos de aporte, por ativo e combináveis:

- **Aporte inicial único** — alocação do capital disponível hoje;
- **Aporte mensal recorrente** (postecipado) — série uniforme até o resgate.

## Taxa mínima de atratividade (TMA)

A TMA é o **custo de oportunidade** do capital. Pode ser:

- informada manualmente; ou
- calculada como **juro real**: `TMA = (1 + SELIC)/(1 + IPCA) - 1`.

Ela é usada como:
- taxa de desconto do **VPL**;
- benchmark do **alfa** (excesso de retorno sobre a TMA);
- taxa da **reserva** (o que sobra rende a TMA);
- base do cálculo de **payback descontado** e da comparação "lucro vs. TMA".

## Índices de desempenho

Calculados **por ativo** e **para a carteira**:

| Índice | Definição |
|--------|-----------|
| **ROI** | `lucro líquido / capital aplicado` (retorno do período) |
| **ROI anualizado** | retorno equivalente por ano (CAGR/TIR), comparável entre prazos |
| **Retorno real** | retorno anual líquido descontado da inflação (IPCA) |
| **VPL** | valor presente do fluxo descontado na TMA (`> 0` agrega valor) |
| **TIR** | taxa por ano que zera o VPL (`>` TMA é desejável) |
| **Payback** | mês em que o resgate recupera o capital (simples e descontado) |
| **IL** | `VPL / capital + 1` (`> 1` paga o custo de oportunidade) |
| **Alfa** | `ROI anual - TMA` (excesso sobre o custo de oportunidade) |
| **Lucro na TMA** | o que o mesmo fluxo de aportes renderia na taxa mínima |
| **Ganho adicional** | `lucro da carteira - lucro na TMA` |

## Execução

```bash
pip install -r requirements.txt
uvicorn server:app --reload
```

(ou `python server.py`, que abre o navegador em `http://localhost:8000`).

Na página, configure o cenário (capital, TMA e recursos mensais), edite a lista de ativos (ou
carregue a carteira exemplo) e clique em **Otimizar alocação**. Os resultados chegam por
`POST /api/otimizar`; os gráficos são gerados no servidor (matplotlib) como PNG embutido no JSON.

## Capturas de tela

### Cenário e Taxa mínima de atratividade (TMA)

<img width="1343" height="399" alt="Cenário e TMA" src="https://github.com/user-attachments/assets/2a5a1383-dd2f-434d-b950-983723221e87" />

### Ativos — exemplo: CDB 13% a.a. (nominal, capitalização mensal)

<img width="1051" height="487" alt="Ativos — CDB 13% a.a." src="https://github.com/user-attachments/assets/5fba7a3d-3420-4bac-a28a-eecc32d814ef" />

### Exemplo: Tesouro SELIC (IR tabela)

<img width="1063" height="353" alt="Tesouro SELIC (IR tabela)" src="https://github.com/user-attachments/assets/6c816376-662e-49ed-ad94-87cafbd923ea" />

### Exemplo: LCI isenta 9,5% a.a.

<img width="1062" height="346" alt="LCI isenta 9,5% a.a." src="https://github.com/user-attachments/assets/8a560d7a-6269-411d-a06e-794cb4b05552" />

### Exemplo: Fundo RF (taxa adm. 1,5% a.a.)

<img width="1068" height="376" alt="Fundo RF (taxa adm. 1,5% a.a.)" src="https://github.com/user-attachments/assets/bc38357f-c34d-4e50-b31c-3a6fe8a4f544" />

## Demonstração

![Demonstração do Otimizador de Investimentos](/videos/demo.mp4)

> 3,1 MB (comprimido: 1280×720, H.264). Se não carregar, veja `videos/demo.mp4` no repositório.

## API

| Rota | Método | Descrição |
|------|--------|-----------|
| `/` | GET | Página HTML (front-end único) |
| `/api/exemplos` | GET | Carteira de exemplo para o formulário (`ativos[]`) |
| `/api/otimizar` | POST | Recebe `{capital, usar_mensal, aporte_mensal, tma_modo, selic_pct, ipca_pct, tma_manual_pct, inflacao_pct, ativos[]}` e devolve alocação, índices por ativo, carteira e gráficos |

O payload de ativo espelha o formulário: `nome`, `taxa_pct`, `periodo`, `base`, `prazo_meses`,
`imposto_modo`/`imposto_pct`, `admin_modo`/`admin_pct`, `inicial_min`/`inicial_max`,
`usa_mensal`/`mensal_max`. Documentação interativa em `/docs` (OpenAPI).

`POST /api/otimizar` responde:

- **carteira**: agregados por ativo (`montante_liquido`, `roi`, `vpl`, `tir_anual`, `payback`,
  `il`, `alfa`) e totais da carteira (`capital_aplicado`, `reserva`, `roi`, `roi_anualizado`,
  `vpl`, `lucro_tma`);
- **indicadores**: linha por ativo (inclui a reserva da TMA) com a projeção mensal;
- **uso**: capital inicial aplicado, aportes mensais, reserva e ganho adicional vs. TMA;
- **graficos**: 3 imagens PNG em base64 (`alocacao`, `patrimonio`, `lucro_tma`);
- **avisos**: alertas de validação (ex.: sem capital, mínimos excedem o capital).

Erros de negócio e de validação retornam `422` com `{"erro": ...}`.

## Estrutura do projeto

```
matrix-optimization/
├── server.py                      # API FastAPI (GET /, /api/exemplos, POST /api/otimizar)
├── requirements.txt              # Dependências
├── videos/
│   └── demo.mp4                  # Demonstração da página (3,1 MB, 1280×720)
├── src/
│   ├── math_finance.py           # Conversão de taxas, capitalização, séries, TIR, TMA
│   ├── tax.py                    # Impostos (fixo/tabela IR) e taxas administrativas
│   ├── instruments.py            # Modelo de ativo (bruto → líquido) e projeção mensal
│   ├── performance.py            # Índices: ROI, VPL, TIR, payback, IL, alfa
│   └── portfolio_optimizer.py    # Alocação ótima (guloso) + reserva na TMA
├── web/
│   ├── __init__.py               # Pacote vazio
│   ├── schema.py                 # Contrato da API (pydantic) e carteira de exemplo
│   ├── graficos.py               # Gráficos matplotlib → PNG base64
│   └── static/index.html         # Front-end (HTML/JS puro, sem CDN)
└── tests/
    ├── test_math_finance.py      # Taxas, capitalização, séries, TIR, TMA
    ├── test_tax.py               # Imposto e taxas administrativas
    ├── test_performance.py       # Indicadores por ativo e carteira
    ├── test_optimizer.py         # Alocação com limites, reserva e aportes mensais
    └── test_server.py            # API: exemplos, otimização e erros (422)
```

## Testes

```bash
python -m unittest discover tests -v
```

Suíte com 45 testes cobrindo o núcleo de cálculo (taxas, impostos, séries, TIR, TMA),
a alocação (limites, reserva, aportes mensais) e a camada de API via `TestClient`
(carteira exemplo, TMA manual e erros `422`).

## Tecnologias

- Python 3.12
- NumPy / SciPy (`brentq` para TIR)
- FastAPI + Uvicorn (servidor HTTP)
- Matplotlib (gráficos em PNG)
- Front-end em HTML/CSS/JS puro (sem framework, sem CDN)