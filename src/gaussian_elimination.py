from fractions import Fraction
from typing import List, Optional, Tuple
from .utils import format_fraction


class GaussJordan:
    """Eliminacao de Gauss-Jordan para resolver sistemas de equacoes lineares.

    Implementa a logica de pivo descrita:
      - Coluna i: elemento (i,i) = 1, demais elementos da coluna = 0
    """

    def __init__(self, matrix: List[List[Fraction]]):
        self.matrix = [row[:] for row in matrix]
        self.rows = len(matrix)
        self.cols = len(matrix[0]) if matrix else 0
        self.steps: List[str] = []
        self.solution: Optional[List[Fraction]] = None
        self.status: str = "nao_resolvido"

    def solve(self) -> Tuple[str, Optional[List[Fraction]]]:
        self.steps = []
        self._forward_elimination()
        self._backward_elimination()
        self._extract_solution()
        return self.status, self.solution

    def _forward_elimination(self):
        pivot_row = 0
        pivot_cols = []
        for col in range(self.cols - 1):
            if pivot_row >= self.rows:
                break
            target_row = self._find_pivot(pivot_row, col)
            if target_row is None:
                continue
            if target_row != pivot_row:
                self._swap_rows(pivot_row, target_row, col)
            self._scale_pivot(pivot_row, col)
            self._eliminate_column(pivot_row, col, above=False)
            pivot_cols.append(col)
            pivot_row += 1
        self._pivot_cols = pivot_cols

    def _backward_elimination(self):
        if not hasattr(self, "_pivot_cols"):
            return
        for col in reversed(self._pivot_cols):
            pivot_row = None
            for i in range(self.rows):
                if self.matrix[i][col] == Fraction(1):
                    pivot_row = i
                    break
            if pivot_row is None:
                continue
            self._eliminate_column(pivot_row, col, above=True)

    def _find_pivot(self, start_row: int, col: int) -> Optional[int]:
        max_val = Fraction(0)
        target = None
        for i in range(start_row, self.rows):
            if self.matrix[i][col] != Fraction(0):
                if target is None or abs(self.matrix[i][col]) > max_val:
                    max_val = abs(self.matrix[i][col])
                    target = i
        return target

    def _swap_rows(self, row1: int, row2: int, col: int):
        self.matrix[row1], self.matrix[row2] = self.matrix[row2], self.matrix[row1]
        self.steps.append(
            f"Troca L{row1 + 1} <-> L{row2 + 1}"
        )

    def _scale_pivot(self, row: int, col: int):
        pivot_val = self.matrix[row][col]
        if pivot_val == Fraction(1):
            return
        factor = Fraction(1) / pivot_val
        self.matrix[row] = [val * factor for val in self.matrix[row]]
        self.steps.append(
            f"L{row + 1} <- ({format_fraction(factor)}) * L{row + 1}"
        )

    def _eliminate_column(self, pivot_row: int, col: int, above: bool = False):
        if above:
            row_range = range(pivot_row - 1, -1, -1)
        else:
            row_range = range(pivot_row + 1, self.rows)

        for i in row_range:
            if self.matrix[i][col] == Fraction(0):
                continue
            factor = self.matrix[i][col]
            self.matrix[i] = [
                self.matrix[i][j] - factor * self.matrix[pivot_row][j]
                for j in range(self.cols)
            ]
            sign = "+" if factor > 0 else "-"
            self.steps.append(
                f"L{i + 1} <- L{i + 1} - ({format_fraction(factor)}) * L{pivot_row + 1}"
            )

    def _extract_solution(self):
        for i in range(self.rows):
            all_zero = all(self.matrix[i][j] == Fraction(0) for j in range(self.cols - 1))
            if all_zero and self.matrix[i][-1] != Fraction(0):
                self.status = "inconsistente"
                self.solution = None
                self.steps.append("Sistema inconsistente: 0 = constante nao nula.")
                return

        num_vars = self.cols - 1
        pivot_cols = getattr(self, "_pivot_cols", [])

        has_free = len(pivot_cols) < num_vars
        if has_free:
            self.status = "infinitas_solucoes"
            self.solution = None
            self.steps.append(
                f"Sistema com solucoes infinitas: {num_vars - len(pivot_cols)} variavel(is) livre(s)."
            )
            return

        solution = [Fraction(0)] * num_vars
        for i, col in enumerate(pivot_cols):
            if i < self.rows:
                solution[col] = self.matrix[i][-1]

        self.status = "unica"
        self.solution = solution

    def get_display(self) -> str:
        lines = ["Matriz aumentada (RREF):"]
        for i, row in enumerate(self.matrix):
            left = " ".join(format_fraction(v) for v in row[:-1])
            lines.append(f"  [{left} | {format_fraction(row[-1])}]")
        if self.solution is not None and self.status == "unica":
            lines.append("\nSolucao:")
            for i, val in enumerate(self.solution):
                lines.append(f"  x{i + 1} = {format_fraction(val)}")
        elif self.status == "inconsistente":
            lines.append("\nSistema sem solucao.")
        elif self.status == "infinitas_solucoes":
            lines.append("\nSistema com infinitas solucoes.")
        return "\n".join(lines)
