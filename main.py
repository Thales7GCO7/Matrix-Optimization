import sys
from fractions import Fraction
from src.gaussian_elimination import GaussJordan
from src.simplex import SimplexSolver
from src.utils import parse_fraction, format_fraction


def menu_principal():
    print("=" * 50)
    print("  SISTEMA DE ALGEBRA LINEAR E OTIMIZACAO")
    print("=" * 50)
    print("  1. Resolver sistema de equacoes (Gauss-Jordan)")
    print("  2. Otimizar problema linear (Simplex)")
    print("  3. Sair")
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


def main():
    while True:
        menu_principal()
        opcao = input("\nEscolha uma opcao: ").strip()

        if opcao == "1":
            resolver_sistema()
        elif opcao == "2":
            otimizar_simplex()
        elif opcao == "3":
            print("Ate logo!")
            sys.exit(0)
        else:
            print("Opcao invalida.")


if __name__ == "__main__":
    main()
