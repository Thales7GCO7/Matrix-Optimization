# Matrix Optimization

Ferramenta interativa de Álgebra Linear, Programação Linear e Otimização Não Linear implementada em Python.

## Visão Geral

O projeto resolve quatro tipos de problemas matemáticos através de duas interfaces:

- **Terminal (CLI)** — menu interativo em `main.py`
- **Web (Streamlit)** — formulários dinâmicos com explicações, passos e gráficos em `app.py`

1. **Eliminação de Gauss-Jordan** — resolve sistemas de equações lineares
2. **Método Simplex** — resolve problemas de otimização linear (programação linear)
3. **Newton-Raphson** — resolve sistemas de equações não lineares
4. **Otimização Não Linear (SciPy)** — maximiza/minimiza funções não lineares com restrições
5. **Otimização de Portfólio de Investimentos** — maximiza o retorno na alocação de recursos

## Funcionalidades

### 1. Resolver Sistemas de Equações (Gauss-Jordan)

Dado um sistema de equações lineares na forma `Ax = b`, o algoritmo aplica eliminação gaussiana com pivoteamento parcial para transformar a matriz aumentada na forma escalonada reduzida (RREF), encontrando a solução única, identificando sistemas inconsistentes ou detectando infinitas soluções.

**Exemplo de entrada:**
```
Equações: 2
Variáveis: 2
Matriz aumentada:
  Linha 1: 2 3 8
  Linha 2: 1 2 5
```
**Saída:** x₁ = 1, x₂ = 2

### 2. Otimização Linear (Simplex)

Maximiza uma função objetivo `z = c^T * x` sujeita a restrições lineares `A * x <= b`, com `x >= 0`.

O algoritmo monta um tableau simplex, itera selecionando variáveis de entrada e saída, e aplica operações de pivoteamento até encontrar a solução ótima ou detectar que o problema é ilimitado.

**Exemplo de entrada:**
```
Variáveis: 2
Restrições: 3
c = 3 5
A:
  1 0
  0 2
  3 2
b = 4 12 18
```
**Saída:** z* = 42, x₁ = 4, x₂ = 6

### 3. Resolução de Equações Não Lineares (Newton-Raphson)

Resolve sistemas de equações não lineares `F(x) = 0` pelo método de Newton-Raphson amortecido (backtracking line search), com convergência quadrática e maior robustez global.

**Características:**
- Jacobiano calculado automaticamente por complex-step ou diferenças finitas
- Suporte a Jacobiano analítico fornecido pelo usuário
- Diagnóstico de convergência, singularidade e divergência

**Exemplos predefinidos:**
- `x² - 2 = 0` → raiz = √2
- `x³ - x - 2 = 0`
- `x₁ + x₂ = 3` e `x₁² + x₂² = 5` → raiz = [1, 2]
- Entrada manual de expressões arbitrárias

### 4. Otimização Não Linear (SciPy)

Maximiza ou minimiza funções objetivo não lineares sujeitas a:
- Restrições de igualdade `g(x) = 0`
- Restrições de desigualdade `g(x) ≥ 0`
- Limites por variável (`bounds`)

**Métodos utilizados:** SLSQP, BFGS, trust-constr (auto-selecionados)

**Exemplos predefinidos:**
- Máximo de função quadrática (sem restrições)
- Máximo com restrição de igualdade (produto de variáveis com soma fixa)
- Máximo com restrição circular (desigualdade)
- Entrada manual de expressões arbitrárias

### 5. Otimização de Portfólio de Investimentos

Maximiza o retorno total ao alocar um orçamento fixo entre múltiplas opções de investimento:

```
Maximizar:  R(x₁, ..., xₙ) = Σ fᵢ(xᵢ)
Sujeito a:  x₁ + x₂ + ... + xₙ = B      (orçamento)
            xᵢ ≥ 0                      (não negatividade)
            xᵢ ≤ Uᵢ                     (limites superior opcionais)
```

**Tipos suportados para `fᵢ(x)`:**

| Tipo | Fórmula | Característica |
|------|--------|----------------|
| `L` Logaritmica | `a * ln(x + c)` | Utilidade concava, retorno marginal decrescente |
| `E` Exponencial | `a * (1 - e^(-b·x))` | Retorno saturante |
| `P` Potência | `a * x^p` | Crescimento sublinear (0 < p ≤ 1) |
| `Q` Quadrática | `a·x - b·x²` | Concava |

**Propriedade fundamental:** No ótimo, todos os retornos marginais `fᵢ'(xᵢ)` são iguais, o que garante alocação economicamente eficiente de recursos.

**Exemplo interativo:**
```
Orçamento total: 1000
[n] Investimentos: 4
Funções de retorno (logarítmica, exponencial, quadrática, logarítmica)
```

**Saída:**
```
Alocação otima (percentual do orçamento):
  x1 = 520.178  (52.02%)  retorno marginal = 0.0767492
  x2 = 73.3165  (7.33%)   retorno marginal = 0.0767492
  x3 = 81.2694  (8.13%)   retorno marginal = 0.0767492
  x4 = 325.236  (32.52%)  retorno marginal = 0.0767492

Retorno total otimo: R* = 459.7303283
```

## Front-end Web (Streamlit)

O aplicativo web (`app.py`) replica os cinco fluxos do terminal com formulários dinâmicos, explicações educativas de cada variável e fórmula (LaTeX), passos do cálculo e gráficos:

- **Gauss-Jordan** — matriz aumentada `[A|b]` em grade célula a célula (aceita frações como `1/3`), RREF em tabela e classificação da solução
- **Simplex** — vetor `c`, matriz `A` e vetor `b`; tableau, `x*`, `z*` e gráfico da região viável (2 variáveis)
- **Newton-Raphson** — expressões `F(x)=0`, chute `x₀`, tolerância e line search; gráfico de convergência do resíduo
- **Otimização não linear** — objetivo, max/min, igualdades, desigualdades, limites e chute; mapa de contorno da função
- **Investimentos** — orçamento, funções L/E/P/Q por investimento, limites superiores; barras de alocação e curvas de retorno

**Execução:**
```bash
streamlit run app.py
```

Cada tela oferece **entrada manual** e **exemplos predefinidos**, com campos que aceitam inteiros, frações e decimais.

## Estrutura do Projeto

```
matrix-optimization/
├── main.py                        # Interface CLI com menu interativo
├── app.py                         # Interface Web (Streamlit) com as 5 telas
├── requirements.txt               # Dependências
├── src/
│   ├── gaussian_elimination.py    # Eliminação de Gauss-Jordan
│   ├── simplex.py                 # Método Simplex para PL
│   ├── nonlinear_solver.py        # Newton-Raphson para sistemas não lineares
│   ├── nonlinear_optimizer.py     # Otimização não linear via SciPy (SLSQP/BFGS)
│   ├── investment_optimizer.py    # Otimização de alocação de recursos
│   ├── expression_parser.py       # Parser seguro de expressões matemáticas
│   └── utils.py                   # Funções utilitárias (parse/formatação)
├── web/                           # Front-end Streamlit
│   ├── explicacoes.py             # Textos educativos (variáveis e fórmulas)
│   ├── forms.py                   # Formulários dinâmicos (matrizes, vetores, limites)
│   ├── render.py                  # Renderização de resultados, tabelas e passos
│   ├── graficos.py                # Gráficos (região viável, convergência, alocação)
│   └── parsers.py                 # Parse de frações/células (sem dependência de UI)
├── tests/
│   ├── test_gaussian.py           # Testes unitários do Gauss-Jordan
│   ├── test_simplex.py            # Testes unitários do Simplex
│   ├── test_nonlinear.py          # Testes do Newton-Raphson
│   ├── test_optimizer.py          # Testes de otimização não linear e investimentos
│   └── test_web.py                # Testes de parse e render do front-end
└── plot_simplex.py                # Visualização gráfica da região viável (exemplo)
```

## Instalação

```bash
pip install -r requirements.txt
```

## Uso

**Terminal:**
```bash
python main.py
```

**Web:**
```bash
streamlit run app.py
```

O menu (terminal) apresenta:
1. Resolver sistema de equações (Gauss-Jordan)
2. Otimizar problema linear (Simplex)
3. Resolver equações não lineares (Newton-Raphson)
4. Otimizar problema não linear
5. Otimizar portfólio de investimentos
6. Sair

Aceita números inteiros e frações (ex: `1/3`, `-5/7`). Expressões não lineares aceitam operadores `+ - * / **`, funções `sin cos tan exp log sqrt abs`, constantes `pi e`, e variáveis `x1 x2 ...`.

## Testes

```bash
python -m unittest discover tests -v
```

## Tecnologias

- Python 3.12
- NumPy (cálculos numéricos)
- SciPy (otimização não linear)
- Matplotlib (visualização gráfica)
- Streamlit (front-end web)
- `fractions.Fraction` (aritmética exata com frações)