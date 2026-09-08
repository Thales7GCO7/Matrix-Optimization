from typing import Callable, List, Sequence

import numpy as np

_SAFE_BUILTINS = {}
_SAFE_NAMESPACE = {
    "np": np,
    "sin": np.sin,
    "cos": np.cos,
    "tan": np.tan,
    "asin": np.arcsin,
    "acos": np.arccos,
    "atan": np.arctan,
    "sinh": np.sinh,
    "cosh": np.cosh,
    "tanh": np.tanh,
    "exp": np.exp,
    "log": np.log,
    "log10": np.log10,
    "log2": np.log2,
    "sqrt": np.sqrt,
    "abs": np.abs,
    "floor": np.floor,
    "ceil": np.ceil,
    "sign": np.sign,
    "pi": np.pi,
    "e": np.e,
    "min": np.minimum,
    "max": np.maximum,
    "power": np.power,
}


def parse_expression(expr: str, n_vars: int = 1) -> Callable:
    code = compile(expr.strip(), "<expr>", "eval")

    if n_vars == 1:
        namespace = dict(_SAFE_NAMESPACE)

        def func(x):
            namespace["x"] = x
            return eval(code, {"__builtins__": _SAFE_BUILTINS}, namespace)

    else:
        namespace = dict(_SAFE_NAMESPACE)

        def func(x):
            xv = np.asarray(x)
            locals_ns = {
                f"x{i + 1}": xv[i] if xv.size > i else 0.0
                for i in range(n_vars)
            }
            return eval(code, {"__builtins__": _SAFE_BUILTINS}, {**namespace, **locals_ns})

    return func


def parse_multiple_expressions(exprs: Sequence[str], n_vars: int) -> List[Callable]:
    funcs = []
    for expr in exprs:
        try:
            funcs.append(parse_expression(expr, n_vars))
        except SyntaxError as exc:
            raise ValueError(f"Expressao invalida: {expr!r} ({exc})") from exc
    return funcs