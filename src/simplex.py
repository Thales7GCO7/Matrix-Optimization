from fractions import Fraction
from typing import List, Optional, Tuple
from .utils import format_fraction


class SimplexSolver:
    """Resolvedor Simplex para Programacao Linear.

    Maximiza: c^T * x
    Sujeito a: A * x <= b, x >= 0
    """

    def __init__(
        self,
        c: List[Fraction],
        A: List[List[Fraction]],
        b: List[Fraction],
    ):
        self.c = [Fraction(x) for x in c]
        self.A = [[Fraction(x) for x in row] for row in A]
        self.b = [Fraction(x) for x in b]
        self.num_vars = len(c)
        self.num_constraints = len(A)
        self.tableau: List[List[Fraction]] = []
        self.steps: List[str] = []
        self.status: str = "nao_resolvido"
        self.optimal_value: Optional[Fraction] = None
        self.optimal_solution: Optional[List[Fraction]] = None

    def solve(self) -> Tuple[str, Optional[Fraction], Optional[List[Fraction]]]:
        self.steps = []
        self._build_tableau()
        self._run_simplex()
        return self.status, self.optimal_value, self.optimal_solution

    def _build_tableau(self):
        n = self.num_vars
        m = self.num_constraints

        for i in range(m):
            if self.b[i] < Fraction(0):
                self.b[i] = -self.b[i]
                self.A[i] = [-self.A[i][j] for j in range(n)]

        tableau = []
        for i in range(m):
            row = self.A[i][:]
            slack = [Fraction(0)] * m
            slack[i] = Fraction(1)
            row.extend(slack)
            row.append(self.b[i])
            tableau.append(row)

        obj_row = [-x for x in self.c]
        obj_row.extend([Fraction(0)] * m)
        obj_row.append(Fraction(0))
        tableau.append(obj_row)

        self.tableau = tableau
        self._var_names = [f"x{i + 1}" for i in range(n)] + [
            f"s{i + 1}" for i in range(m)
        ]
        self.steps.append("Tableau inicial construido.")
        self.steps.append(self._format_tableau())

    def _run_simplex(self):
        iteration = 0
        max_iter = 100

        while iteration < max_iter:
            iteration += 1
            pivot_col = self._find_entering()
            if pivot_col is None:
                self.status = "otimo"
                self._extract_solution()
                self.steps.append(f"Solucao otima encontrada na iteracao {iteration}.")
                return

            pivot_row = self._find_leaving(pivot_col)
            if pivot_row is None:
                self.status = "ilimitado"
                self.steps.append("Problema ilimitado: custo pode crescer indefinidamente.")
                return

            self.steps.append(
                f"Iteracao {iteration}: entra x{pivot_col + 1}, sai linha {pivot_row + 1}"
            )
            self._pivot(pivot_row, pivot_col)
            self.steps.append(self._format_tableau())

        self.status = "max_iteracoes"

    def _find_entering(self) -> Optional[int]:
        last_row = self.tableau[-1]
        min_val = Fraction(0)
        col = None
        for j in range(len(last_row) - 1):
            if last_row[j] < min_val:
                min_val = last_row[j]
                col = j
        return col

    def _find_leaving(self, pivot_col: int) -> Optional[int]:
        ratios = []
        rhs_col = len(self.tableau[0]) - 1
        for i in range(len(self.tableau) - 1):
            if self.tableau[i][pivot_col] > Fraction(0):
                ratio = self.tableau[i][rhs_col] / self.tableau[i][pivot_col]
                ratios.append((ratio, i))
        if not ratios:
            return None
        ratios.sort(key=lambda x: x[0])
        return ratios[0][1]

    def _pivot(self, pivot_row: int, pivot_col: int):
        pivot_val = self.tableau[pivot_row][pivot_col]
        factor = Fraction(1) / pivot_val
        self.tableau[pivot_row] = [val * factor for val in self.tableau[pivot_row]]

        for i in range(len(self.tableau)):
            if i == pivot_row:
                continue
            row_factor = self.tableau[i][pivot_col]
            self.tableau[i] = [
                self.tableau[i][j] - row_factor * self.tableau[pivot_row][j]
                for j in range(len(self.tableau[i]))
            ]

    def _extract_solution(self):
        n = self.num_vars
        m = self.num_constraints
        rhs_col = len(self.tableau[0]) - 1
        solution = [Fraction(0)] * n

        for j in range(n):
            col_vals = [self.tableau[i][j] for i in range(m)]
            if col_vals.count(Fraction(1)) == 1 and col_vals.count(Fraction(0)) == m - 1:
                one_row = col_vals.index(Fraction(1))
                solution[j] = self.tableau[one_row][rhs_col]

        self.optimal_solution = solution
        self.optimal_value = self.tableau[-1][rhs_col]

    def _format_tableau(self) -> str:
        header = "  ".join(
            f"{name:>8}" for name in self._var_names
        ) + "  " + f"{'RHS':>8}"
        sep = "-" * len(header)
        lines = [header, sep]
        for i, row in enumerate(self.tableau):
            label = f"z" if i == len(self.tableau) - 1 else f"s{i + 1}"
            cells = "  ".join(f"{format_fraction(v):>8}" for v in row)
            lines.append(f"{label}: {cells}")
        return "\n".join(lines)

    def get_display(self) -> str:
        lines = ["Problema de Programacao Linear (Simplex):"]
        lines.append(f"  Maximize: {' + '.join(f'{format_fraction(c)}x{i+1}' for i, c in enumerate(self.c) if c != 0)}")
        lines.append("  Sujeito a:")
        for i, row in enumerate(self.A):
            terms = " + ".join(
                f"{format_fraction(v)}x{j + 1}"
                for j, v in enumerate(row)
                if v != 0
            )
            lines.append(f"    {terms} <= {format_fraction(self.b[i])}")
        lines.append(f"  x_i >= 0 para todo i\n")

        if self.optimal_value is not None:
            lines.append(f"Valor otimo: z* = {format_fraction(self.optimal_value)}")
            lines.append("Solucao otima:")
            for i, val in enumerate(self.optimal_solution):
                lines.append(f"  x{i + 1} = {format_fraction(val)}")
        elif self.status == "ilimitado":
            lines.append("Problema ilimitado.")
        elif self.status == "inviavel":
            lines.append("Problema infactivel.")
        return "\n".join(lines)
