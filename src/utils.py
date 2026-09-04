from fractions import Fraction
from typing import List


def parse_fraction(value: str) -> Fraction:
    value = value.strip()
    if "/" in value:
        num, den = value.split("/")
        return Fraction(int(num), int(den))
    return Fraction(int(value))


def parse_matrix_input(rows: int, cols: int) -> List[List[Fraction]]:
    matrix = []
    print(f"Digite a matriz {rows}x{cols} (use fracoes como 1/3 se necessario):")
    for i in range(rows):
        while True:
            line = input(f"  Linha {i + 1} ({cols} valores separados por espaco): ")
            values = line.split()
            if len(values) != cols:
                print(f"  Erro: esperado {cols} valores, recebeu {len(values)}. Tente novamente.")
                continue
            try:
                row = [parse_fraction(v) for v in values]
                matrix.append(row)
                break
            except ValueError:
                print("  Erro: valores invalidos. Use inteiros ou fracoes (ex: 1/3).")
    return matrix


def format_matrix(matrix: List[List[Fraction]]) -> str:
    if not matrix:
        return "[]"
    col_widths = []
    for j in range(len(matrix[0])):
        max_w = max(len(str(matrix[i][j])) for i in range(len(matrix)))
        col_widths.append(max_w)
    lines = []
    for row in matrix:
        cells = [str(val).rjust(col_widths[j]) for j, val in enumerate(row)]
        lines.append("[" + "  ".join(cells) + "]")
    return "\n".join(lines)


def format_fraction(val: Fraction) -> str:
    if val.denominator == 1:
        return str(val.numerator)
    return f"{val.numerator}/{val.denominator}"
