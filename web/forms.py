from typing import List, Optional

import streamlit as st


def number_field(
    label: str,
    key: str,
    min_value: int = 1,
    max_value: int = 20,
    default: int = 2,
    step: int = 1,
    help: Optional[str] = None,
) -> int:
    kwargs = {
        "label": label,
        "min_value": min_value,
        "max_value": max_value,
        "key": key,
        "step": step,
        "help": help,
    }
    if key not in st.session_state:
        kwargs["value"] = default
    return int(st.number_input(**kwargs))


def select_dim(
    label: str, key: str, min_value: int = 1, default: int = 2, max_value: int = 20
) -> int:
    return number_field(label, key, min_value, max_value, default)


def grid_cells(
    prefix: str,
    rows: int,
    cols: int,
    default: str = "0",
) -> List[List[str]]:
    """Grade dinamica de celulas de texto para matrizes (linha x coluna)."""
    cells = []
    for i in range(rows):
        line = st.columns(cols)
        row_cells = []
        for j in range(cols):
            key = f"{prefix}_{i}_{j}"
            kwargs = {
                "label": f"({i + 1}x{j + 1})",
                "key": key,
                "label_visibility": "collapsed",
                "placeholder": default,
            }
            if key not in st.session_state:
                kwargs["value"] = default
            row_cells.append(line[j].text_input(**kwargs))
        cells.append(row_cells)
    return cells


def vector_cells(
    prefix: str,
    size: int,
    default: str = "0",
    label_hint: Optional[str] = None,
) -> List[str]:
    """Vetor como linha de campos de texto."""
    if label_hint:
        st.caption(label_hint)
    line = st.columns(size)
    cells = []
    for j in range(size):
        key = f"{prefix}_{j}"
        kwargs = {
            "label": f"v{j + 1}",
            "key": key,
            "label_visibility": "collapsed",
            "placeholder": default,
        }
        if key not in st.session_state:
            kwargs["value"] = default
        cells.append(line[j].text_input(**kwargs))
    return cells


def bounds_fields(
    prefix: str,
    n: int,
) -> tuple:
    """Campos de limite inferior/superior por variavel ('' = sem limite)."""
    st.markdown("**Limites por variavel** (deixe em branco para sem limite):")
    lo = st.columns(2)[0]
    lo_cols = st.columns(n)
    low = []
    for j in range(n):
        low.append(
            lo_cols[j].text_input(
                label=f"inf x{j + 1}",
                value="",
                key=f"{prefix}_lo_{j}",
                label_visibility="collapsed",
                placeholder=f"x{j + 1} inf",
            )
        )
    up_cols = st.columns(n)
    up = []
    for j in range(n):
        up.append(
            up_cols[j].text_input(
                label=f"sup x{j + 1}",
                value="",
                key=f"{prefix}_up_{j}",
                label_visibility="collapsed",
                placeholder=f"x{j + 1} sup",
            )
        )
    return low, up


def expression_fields(prefix: str, count: int, label: str = "Expressao") -> List[str]:
    exprs = []
    for i in range(count):
        exprs.append(
            st.text_input(
                f"{label} {i + 1}",
                value="",
                key=f"{prefix}_expr_{i}",
                placeholder="ex: x1 + x2 - 3",
            )
        )
    return exprs


def text_field(label: str, key: str, default: str = "", help: Optional[str] = None) -> str:
    return st.text_input(label, value=default, key=key, help=help)