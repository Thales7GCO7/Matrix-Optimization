# Matrix Optimization

Ferramenta interativa de Álgebra Linear e Programação Linear implementada em Python.

## Visão Geral

O projeto resolve dois tipos de problemas matemáticos através de uma interface de linha de comando:

1. **Eliminação de Gauss-Jordan** — resolve sistemas de equações lineares
2. **Método Simplex** — resolve problemas de otimização linear (programação linear)

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

## Estrutura do Projeto

```
matrix-optimization/
├── main.py                        # Interface CLI com menu interativo
├── requirements.txt               # Dependências
├── src/
│   ├── gaussian_elimination.py    # Eliminação de Gauss-Jordan
│   ├── simplex.py                 # Método Simplex para PL
│   └── utils.py                   # Funções utilitárias (parse/formatação)
├── tests/
│   ├── test_gaussian.py           # Testes unitários do Gauss-Jordan
│   └── test_simplex.py            # Testes unitários do Simplex
└── plot_simplex.py                # Visualização gráfica da região viável
```

## Instalação

```bash
pip install -r requirements.txt
```

## Uso

```bash
python main.py
```

O menu apresenta:
1. Resolver sistema de equações (Gauss-Jordan)
2. Otimizar problema linear (Simplex)
3. Sair

Aceita números inteiros e frações (ex: `1/3`, `-5/7`).

## Testes

```bash
python -m pytest tests/ -v
```

## Tecnologias

- Python 3.12
- NumPy (cálculos numéricos)
- Matplotlib (visualização gráfica)
- `fractions.Fraction` (aritmética exata com frações)
