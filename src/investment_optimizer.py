from typing import Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np
from scipy.optimize import LinearConstraint

from .nonlinear_optimizer import NonlinearOptimizer, numerical_gradient


def make_logreturn(a: float, c: float = 1.0) -> Dict:
    base = float(a)
    shift = float(c)
    func = lambda x: base * np.log(x + shift)
    grad = lambda x: base / (x + shift)
    label = f"Logaritmica: {_fmt(a)} * ln(x + {_fmt(c)})"
    return {"label": label, "type": "log", "func": func, "grad": grad}


def make_expreturn(a: float, b: float) -> Dict:
    base = float(a)
    rate = float(b)
    func = lambda x: base * (1.0 - np.exp(-rate * x))
    grad = lambda x: base * rate * np.exp(-rate * x)
    label = f"Exponencial: {_fmt(a)} * (1 - e^(-{_fmt(b)}x))"
    return {"label": label, "type": "exp", "func": func, "grad": grad}


def make_powerreturn(a: float, p: float) -> Dict:
    base = float(a)
    power = float(p)
    func = lambda x: base * np.power(np.maximum(x, 0.0), power)
    grad = lambda x: base * power * np.power(np.maximum(x, 0.0), power - 1.0)
    label = f"Potencia: {_fmt(a)} * x^{_fmt(p)}"
    return {"label": label, "type": "power", "func": func, "grad": grad}


def make_quadreturn(a: float, b: float) -> Dict:
    lin = float(a)
    quad = float(b)
    func = lambda x: lin * x - quad * x ** 2
    grad = lambda x: lin - 2.0 * quad * x
    label = f"Quadratica: {_fmt(a)}x - {_fmt(b)}x^2"
    return {"label": label, "type": "quad", "func": func, "grad": grad}


def _fmt(v: float) -> str:
    return f"{v:.6g}"


class InvestmentOptimizer:
    """Otimizacao da alocacao de recursos entre investimentos.

    Maximiza o retorno total:
        R(x) = sum(f_i(x_i))
    sujeito a:
        sum(x_i) = budget            (recurso total disponivel)
        lower_i <= x_i <= upper_i    (limites individuais, x_i >= 0)

    Para maxima precisao, as funcoes de retorno podem fornecer o
    gradiente analitico; caso contrario, o gradiente e obtido por
    complex-step.
    """

    def __init__(
        self,
        return_functions: Sequence[Dict],
        budget: float,
        lower_bounds: Optional[Sequence[float]] = None,
        upper_bounds: Optional[Sequence[float]] = None,
        tol: float = 1e-10,
        method: str = "SLSQP",
    ):
        self.funcs = list(return_functions)
        self.n = len(self.funcs)
        self.budget = float(budget)
        self.lower = (
            [float(v) for v in lower_bounds]
            if lower_bounds is not None
            else [0.0] * self.n
        )
        self.upper = (
            [float(v) for v in upper_bounds]
            if upper_bounds is not None
            else [self.budget] * self.n
        )
        self.tol = tol
        self.method = method
        self.optimizer: Optional[NonlinearOptimizer] = None
        self.status: str = "nao_resolvido"
        self.solution: Optional[np.ndarray] = None
        self.optimal_return: Optional[float] = None
        self.allocation: Optional[np.ndarray] = None
        self.marginal_returns: Optional[np.ndarray] = None

    def _objective(self, x) -> float:
        x = np.asarray(x, dtype=float)
        return float(sum(f["func"](np.float64(x[i])) for i, f in enumerate(self.funcs)))

    def _gradient(self, x) -> np.ndarray:
        x = np.asarray(x, dtype=float)
        grad = np.zeros(self.n)
        for i, f in enumerate(self.funcs):
            if "grad" in f:
                grad[i] = f["grad"](np.float64(x[i]))
            else:
                single = lambda xi, ii=i: self.funcs[ii]["func"](np.float64(xi))
                grad[i] = numerical_gradient(single, np.array([x[i]]))[0]
        return grad

    def solve(self) -> Tuple[str, Optional[np.ndarray]]:
        n = self.n
        hint = self.budget / n

        bounds = list(zip(self.lower, self.upper))
        cons = [
            LinearConstraint(
                np.ones((1, n)),
                lb=self.budget,
                ub=self.budget,
            )
        ]

        self.optimizer = NonlinearOptimizer(
            objective=self._objective,
            x0=np.full(n, hint),
            gradient=self._gradient,
            bounds=bounds,
            constraints=cons,
            maximize=True,
            method=self.method,
            tol=self.tol,
            options={"ftol": self.tol},
        )

        self.status, self.solution = self.optimizer.solve()

        if self.solution is not None:
            self.allocation = self.solution
            self.optimal_return = self.optimizer.optimal_value
            self.marginal_returns = self._gradient(self.solution)

        return self.status, self.solution

    def get_display(self) -> str:
        lines = ["Otimizacao de alocacao de investimentos:"]
        lines.append(f"  Orcamento total: {self.budget:.6g}")
        lines.append(f"  Numero de investimentos: {self.n}")
        for i, f in enumerate(self.funcs):
            lb = self.lower[i]
            ub = self.upper[i]
            lines.append(f"    [{i + 1}] {f['label']}  (limite: {lb:.6g} a {ub:.6g})")

        if self.allocation is not None:
            lines.append(f"\n  Alocacao otima (percentual do orcamento):")
            for i, (val, f) in enumerate(zip(self.allocation, self.funcs)):
                pct = val / self.budget * 100 if self.budget > 0 else 0.0
                marg = self.marginal_returns[i] if self.marginal_returns is not None else 0.0
                lines.append(
                    f"    x{i + 1} = {val:.6g}  ({pct:.2f}%)  retorno marginal = {marg:.6g}"
                )
            if self.optimal_return is not None:
                lines.append(f"\n  Retorno total otimo: R* = {self.optimal_return:.10g}")
            if self.optimizer is not None:
                lines.append(f"  Iteracoes: {self.optimizer.iterations}")
        else:
            lines.append(f"\n  Status: {self.status}")
        return "\n".join(lines)

    def get_return_decomposition(self) -> List[float]:
        if self.allocation is None:
            return []
        return [
            float(self.funcs[i]["func"](np.float64(self.allocation[i])))
            for i in range(self.n)
        ]


def default_portfolio() -> List[Dict]:
    return [
        make_logreturn(a=40.0, c=1.0),
        make_expreturn(a=60.0, b=0.05),
        make_quadreturn(a=0.08, b=2e-5),
        make_logreturn(a=25.0, c=0.5),
    ]