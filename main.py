import sys
from fractions import Fraction

from src.gaussian_elimination import GaussJordan
from src.simplex import SimplexSolver
from src.utils import parse_fraction, format_fraction
from src.nonlinear_solver import NewtonRaphson
from src.nonlinear_optimizer import NonlinearOptimizer
from src.investment_optimizer import (
    InvestmentOptimizer,
    default_portfolio,
    make_logreturn,
    make_expreturn,
    make_powerreturn,
    make_quadreturn,
)
from src.expression_parser import parse_expression, parse_multiple_expressions

EXEMPLOS_SISTEMAS_NAO_LINEARES = {
    "1": {
        "nome": "x^2 - 2 = 0  (raiz = sqrt(2))",
        "exprs": ["x**2 - 2"],
        "x0": [1.0],
    },
    "2": {
        "nome": "x^3 - x - 2 = 0",
        "exprs": ["x**3 - x - 2"],
        "x0": [1.5],
    },
    "3": {
        "nome": "x1 + x2 - 3 = 0, x1^2 + x2^2 - 5 = 0  (raiz = [1, 2])",
        "exprs": ["x1 + x2 - 3", "x1**2 + x2**2 - 5"],
        "x0": [0.5, 3.0],
    },
    "4": {
        "nome": "x1^2 - 2*x1 + x2 - 4 = 0, x1^2 + x2^2 - 26 = 0  (raiz = [1, 5])",
        "exprs": ["x1**2 - 2*x1 + x2 - 4", "x1**2 + x2**2 - 26"],
        "x0": [0.0, 4.0],
    },
}

EXEMPLOS_OTIMIZACAO = {
    "1": {
        "nome": "Max f = -x1^2 - x2^2 + 4*x1 + 6*x2  (otimo = [2, 3], z = 13)",
        "objetivo": "-x1**2 - x2**2 + 4*x1 + 6*x2",
        "maximizar": True,
        "n": 2,
        "x0": [0.0, 0.0],
        "eq": [],
        "ineq": [],
        "bounds": None,
    },
    "2": {
        "nome": "Max x1*x2  sujeito a  x1 + 2*x2 = 10  (otimo = [5, 2.5], z = 12.5)",
        "objetivo": "x1*x2",
        "maximizar": True,
        "n": 2,
        "x0": [1.0, 1.0],
        "eq": ["x1 + 2*x2 - 10"],
        "ineq": [],
        "bounds": [(0, None), (0, None)],
    },
    "3": {
        "nome": "Max x1*x2  sujeito a  x1^2 + x2^2 <= 8  (otimo x = [2, 2], z = 4)",
        "objetivo": "x1*x2",
        "maximizar": True,
        "n": 2,
        "x0": [0.5, 0.5],
        "eq": [],
        "ineq": ["8 - x1**2 - x2**2"],
        "bounds": [(0, None), (0, None)],
    },
}


def menu_principal():
    print("=" * 50)
    print("  SISTEMA DE ALGEBRA LINEAR E OTIMIZACAO")
    print("=" * 50)
    print("  1. Resolver sistema de equacoes (Gauss-Jordan)")
    print("  2. Otimizar problema linear (Simplex)")
    print("  3. Resolver equacoes nao lineares (Newton-Raphson)")
    print("  4. Otimizar problema nao linear")
    print("  5. Otimizar portfolio de investimentos")
    print("  6. Sair")
    print("=" * 50)


def resolver_sistema():
    print("\n--- RESOLUCAO DE SISTEMA LINEAR ---")
    m = int(input("Numero de equacoes (linhas): "))
    n = int(input("Numero de variaveis (colunas de coeficientes): "))

    print(f"\nDigite a matriz aumentada {m}x{n + 1} (coeficientes + resultado):")
    print(f"Cada linha: {n} coeficientes seguidos do resultado, separados por espaco.")
    matrix = []
    for i in range(m):
        while True:
            line = input(f"  Linha {i + 1}: ")
            values = line.split()
            if len(values) != n + 1:
                print(f"  Erro: esperado {n + 1} valores. Tente novamente.")
                continue
            try:
                row = [parse_fraction(v) for v in values]
                matrix.append(row)
                break
            except ValueError:
                print("  Valores invalidos. Use inteiros ou fracoes (ex: 1/3).")

    gj = GaussJordan(matrix)
    status, solution = gj.solve()

    print(f"\n{gj.get_display()}")
    print(f"\nPassos:")
    for step in gj.steps:
        print(f"  -> {step}")


def otimizar_simplex():
    print("\n--- OTIMIZACAO LINEAR (SIMPLEX) ---")
    print("Maximize: c^T * x")
    print("Sujeito a: A * x <= b, x >= 0\n")

    n = int(input("Numero de variaveis: "))
    m = int(input("Numero de restricoes: "))

    print(f"\nVetor de custos c ({n} valores):")
    line = input("  c = ")
    c = [parse_fraction(v) for v in line.split()]
    if len(c) != n:
        print(f"  Erro: esperado {n} valores.")
        return

    print(f"\nMatriz A ({m}x{n}):")
    A = []
    for i in range(m):
        while True:
            line = input(f"  Restricao {i + 1} ({n} coeficientes): ")
            values = line.split()
            if len(values) != n:
                print(f"  Erro: esperado {n} valores. Tente novamente.")
                continue
            try:
                row = [parse_fraction(v) for v in values]
                A.append(row)
                break
            except ValueError:
                print("  Valores invalidos.")

    print(f"\nVetor b ({m} valores, limites das restricoes):")
    line = input("  b = ")
    b = [parse_fraction(v) for v in line.split()]
    if len(b) != m:
        print(f"  Erro: esperado {m} valores.")
        return

    solver = SimplexSolver(c, A, b)
    status, value, solution = solver.solve()

    print(f"\n{solver.get_display()}")
    print(f"\nPassos:")
    for step in solver.steps:
        print(f"  -> {step}")


def resolver_sistema_nao_linear():
    print("\n--- RESOLUCAO DE EQUACOES NAO LINEARES (NEWTON-RAPHSON) ---")
    print("Exemplos predefinidos:")
    for key, ex in EXEMPLOS_SISTEMAS_NAO_LINEARES.items():
        print(f"  [{key}] {ex['nome']}")
    print("  [C] Entrada manual de expressoes\n")

    choice = input("Escolha: ").strip().lower()
    if choice == "c":
        n = int(input("Numero de variaveis: "))
        print(f"\nDigite {n} expressoes usando x1, x2, ... (f(x) = 0).")
        print("Suporte: + - * / ** sin cos tan exp log sqrt pi e\n")
        exprs = []
        for i in range(n):
            expr = input(f"  F{i + 1}: ")
            exprs.append(expr)
        x0 = input(f"  Chute inicial ({n} valores separados por espaco): ").strip()
        x0v = [float(v) for v in x0.split()] if x0 else [1.0] * n
    else:
        ex = EXEMPLOS_SISTEMAS_NAO_LINEARES.get(choice)
        if not ex:
            print("Opcao invalida.")
            return
        exprs = ex["exprs"]
        x0v = ex["x0"]
        print(f"\n  Sistema selecionado: {ex['nome']}")

    funcs = parse_multiple_expressions(exprs, len(x0v))

    def sistema(x):
        return [f(x) for f in funcs]

    solver = NewtonRaphson(func=sistema, x0=x0v)
    status, solution = solver.solve()

    print(f"\n{solver.get_display()}")
    print(f"\nPassos:")
    for step in solver.steps:
        print(f"  -> {step}")


def otimizar_nao_linear():
    print("\n--- OTIMIZACAO NAO LINEAR ---")
    print("Exemplos predefinidos:")
    for key, ex in EXEMPLOS_OTIMIZACAO.items():
        print(f"  [{key}] {ex['nome']}")
    print("  [C] Entrada manual\n")

    choice = input("Escolha: ").strip().lower()
    if choice == "c":
        n = int(input("Numero de variaveis: "))
        print("\nFuncao objetivo usando x1, x2, ... (suporte: + - * / ** sin cos tan exp log sqrt pi e)")
        objetivo = input("  Objetivo = ")
        tipo = input("  [M]aximizar ou [m]inimizar? ").strip().lower()
        maximizar = not tipo.startswith("mi")

        n_eq = int(input("  Numero de restricoes de igualdade (g(x) = 0): "))
        eq = []
        for i in range(n_eq):
            eq.append(input(f"    Igualdade {i + 1}: "))

        n_ineq = int(input("  Numero de restricoes de desigualdade (g(x) >= 0): "))
        ineq = []
        for i in range(n_ineq):
            ineq.append(input(f"    Desigualdade {i + 1}: "))

        bounds = None
        usar_bounds = input("  Definir limites por variavel? (s/N): ").strip().lower()
        if usar_bounds.startswith("s"):
            bounds = []
            for i in range(n):
                raw = input(f"    Limite x{i + 1} (ex: 0 10, ou 'inf'): ").strip()
                parts = raw.split()
                lb = float(parts[0]) if len(parts) > 0 and parts[0] != "inf" else None
                ub = float(parts[1]) if len(parts) > 1 and parts[1] != "inf" else None
                bounds.append((lb, ub))

        x0_raw = input(f"  Chute inicial ({n} valores): ").strip()
        x0v = [float(v) for v in x0_raw.split()] if x0_raw else [1.0] * n
    else:
        ex = EXEMPLOS_OTIMIZACAO.get(choice)
        if not ex:
            print("Opcao invalida.")
            return
        objetivo, maximizar = ex["objetivo"], ex["maximizar"]
        n = ex["n"]
        eq, ineq = ex["eq"], ex["ineq"]
        bounds = ex["bounds"]
        x0v = ex["x0"]
        print(f"\n  Problema: {ex['nome']}")

    f_obj = parse_expression(objetivo, n)

    constraints = [
        {"type": "eq", "fun": lambda x, g=parse_expression(e, n): [g(x)]}
        for e in eq
    ] + [
        {"type": "ineq", "fun": lambda x, g=parse_expression(e, n): [g(x)]}
        for e in ineq
    ]

    solver = NonlinearOptimizer(
        objective=f_obj,
        x0=x0v,
        bounds=bounds,
        constraints=constraints if constraints else None,
        maximize=maximizar,
        method="SLSQP",
    )
    status, solution = solver.solve()

    print(f"\n{solver.get_display()}")
    if status != "otimo":
        print(f"  (aviso: o problema pode ser nao convexo ou mal condicionado)")


def otimizar_investimento():
    print("\n--- OTIMIZACAO DE PORTFOLIO DE INVESTIMENTOS ---")
    print("Objetivo: maximizar R(x1,...,xn) = soma das funcoes de retorno")
    print("Restricoes: soma(xi) = orcamento,  xi >= limite inferior\n")

    print("Tipos de funcao de retorno disponiveis:")
    print("  [L] Logaritmica:  a * ln(x + c)     (utilidade concava, retorno decrescente)")
    print("  [E] Exponencial:  a * (1 - e^(-b*x)) (retorno saturante)")
    print("  [P] Potencia:     a * x^p            (0 < p <= 1)")
    print("  [Q] Quadratica:   a*x - b*x^2        (concava)")
    print("  [D] Usar portfolio de exemplo (4 investimentos)\n")

    budget = float(input("Orcamento total disponivel: "))

    use_default = input("Usar portfolio de exemplo? (s/N): ").strip().lower()
    funcs = default_portfolio()
    if not use_default.startswith("s"):
        n = int(input("\nNumero de investimentos: "))
        funcs = []
        for i in range(n):
            print(f"\n  Investimento {i + 1}:")
            tipo = input("    Tipo (L/E/P/Q): ").strip().upper()
            if tipo == "L":
                a = float(input("    a: "))
                c = float(input("    c: "))
                funcs.append(make_logreturn(a, c))
            elif tipo == "E":
                a = float(input("    a: "))
                b = float(input("    b: "))
                funcs.append(make_expreturn(a, b))
            elif tipo == "P":
                a = float(input("    a: "))
                p = float(input("    p (0 < p <= 1): "))
                funcs.append(make_powerreturn(a, p))
            elif tipo == "Q":
                a = float(input("    a: "))
                b = float(input("    b: "))
                funcs.append(make_quadreturn(a, b))
            else:
                print("    Tipo invalido, usando logaritmica a=20 c=1.")
                funcs.append(make_logreturn(20.0, 1.0))

    usar_limites = input("Definir limites superiores por investimento? (s/N): ").strip().lower()
    upper = None
    if usar_limites.startswith("s"):
        upper = []
        for i in range(len(funcs)):
            raw = input(f"  limite superior x{i + 1}: ").strip()
            upper.append(float(raw) if raw else budget)

    opt = InvestmentOptimizer(
        return_functions=funcs,
        budget=budget,
        upper_bounds=upper,
        method="SLSQP",
    )
    status, solution = opt.solve()

    print(f"\n{opt.get_display()}")
    if status != "otimo":
        print(f"  (aviso: problema nao convergiu corretamente)")


def main():
    while True:
        menu_principal()
        opcao = input("\nEscolha uma opcao: ").strip()

        if opcao == "1":
            resolver_sistema()
        elif opcao == "2":
            otimizar_simplex()
        elif opcao == "3":
            resolver_sistema_nao_linear()
        elif opcao == "4":
            otimizar_nao_linear()
        elif opcao == "5":
            otimizar_investimento()
        elif opcao == "6":
            print("Ate logo!")
            sys.exit(0)
        else:
            print("Opcao invalida.")


if __name__ == "__main__":
    main()