from fractions import Fraction
from typing import List, Optional, Sequence, Tuple, Union

NumberGrid = List[List[Fraction]]


def parse_flex_fraction(value: str) -> Optional[Fraction]:
    """Converte texto em Fraction aceitando inteiros, fracoes e decimais.

    Exemplos validos: '2', '1/3', '-5/7', '1.5', '0.25'.
    Retorna None se o valor for invalido.
    """
    v = value.strip()
    if not v:
        return None
    try:
        if "/" in v:
            num, den = v.split("/", 1)
            return Fraction(int(num.strip()), int(den.strip()))
        if any(ch in v for ch in ".,eE"):
            return Fraction(float(v)).limit_denominator(10**9)
        return Fraction(v)
    except (ValueError, ZeroDivisionError, OverflowError):
        return None


def parse_grid(
    texts: Sequence[Sequence[str]], rows: int, cols: int
) -> Tuple[Optional[NumberGrid], str]:
    """Converte uma grade de textos em matriz de Fraction.

    Retorna (matriz, erro). Se erro nao vazio, matriz e None.
    """
    if rows != len(texts) or any(len(row) != cols for row in texts):
        return None, "Dimensao da grade nao confere com m x n informados."
    grid = []
    for i in range(rows):
        row = []
        for j in range(cols):
            val = parse_flex_fraction(texts[i][j])
            if val is None:
                return None, (
                    f"Valor invalido na celula ({i + 1}x{j + 1}): "
                    f"'{texts[i][j]}'. Use inteiros, fracoes (ex: 1/3) ou decimais."
                )
            row.append(val)
        grid.append(row)
    return grid, ""


def parse_vector(
    texts: Sequence[Union[str, int, float]], size: int
) -> Tuple[Optional[List[Fraction]], str]:
    flat = [str(t) if not isinstance(t, (int, float)) else t for t in texts]
    vec = []
    for v in flat:
        val = parse_flex_fraction(str(v))
        if val is None:
            return None, f"Valor invalido: '{v}'. Use inteiros, fracoes ou decimais."
        vec.append(val)
    if len(vec) != size:
        return None, f"Esperado {size} valores, recebido {len(vec)}."
    return vec, ""


def parse_float_value(
    value: str, allow_inf: bool = True, allow_empty_none: bool = False
) -> Optional[float]:
    """Converte texto em float; '' vira None se allow_empty_none.

    Aceita 'inf', '-inf' se allow_inf.
    """
    v = value.strip().lower()
    if not v:
        return None if allow_empty_none else None
    if allow_inf and v in ("inf", "+inf"):
        return float("inf")
    if allow_inf and v == "-inf":
        return float("-inf")
    try:
        return float(v)
    except ValueError:
        return None


def parse_float_sequence(text: str, size: int) -> Tuple[Optional[List[float]], str]:
    """Converte um texto 'a b c' em lista de float com exatamente `size` itens."""
    raw = text.split()
    if len(raw) != size:
        return None, f"Esperado {size} valores separados por espaco, recebido {len(raw)}."
    out = []
    for v in raw:
        val = parse_float_value(v, allow_empty_none=False)
        if val is None:
            return None, f"Valor invalido: '{v}'."
        out.append(val)
    return out, ""


def parse_bounds(
    lower_texts: Sequence[str], upper_texts: Sequence[str], n: int
) -> Tuple[Optional[List[Tuple[Optional[float], Optional[float]]]], str]:
    """Converte textos de limites superior/inferior em bounds.

    Campo vazio ou 'inf' significa sem limite (None).
    Retorna (bounds, erro).
    """
    def to_bound(text: str) -> Tuple[Optional[float], bool]:
        v = text.strip().lower()
        if not v or v in ("inf", "+inf"):
            return None, True
        if v == "-inf":
            return None, True
        try:
            return float(v), True
        except ValueError:
            return None, False

    bounds = []
    for i in range(n):
        lb, lb_ok = to_bound(lower_texts[i])
        ub, ub_ok = to_bound(upper_texts[i])
        if not lb_ok:
            return None, f"Limite inferior invalido para x{i + 1}: '{lower_texts[i]}'."
        if not ub_ok:
            return None, f"Limite superior invalido para x{i + 1}: '{upper_texts[i]}'."
        bounds.append((lb, ub))
    return bounds, ""