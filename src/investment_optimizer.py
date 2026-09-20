"""Generic nonlinear resource allocation across investments.

Maximizes the total return:
    R(x) = sum(f_i(x_i))
subject to:
    sum(x_i) = budget            (total resource available)
    lower_i <= x_i <= upper_i    (per-investment bounds, x_i >= 0)

For maximum accuracy, return functions may provide an analytic
gradient; otherwise the gradient is estimated by complex-step
differentiation.
"""

from typing import Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np
from scipy.optimize import LinearConstraint, minimize


def make_log_return(a: float, c: float = 1.0) -> Dict:
    base = float(a)
    shift = float(c)
    func = lambda x: base * np.log(x + shift)
    grad = lambda x: base / (x + shift)
    label = f"Logarithmic: {_fmt(a)} * ln(x + {_fmt(c)})"
    return {"label": label, "type": "log", "func": func, "grad": grad}


def make_exp_return(a: float, b: float) -> Dict:
    base = float(a)
    rate = float(b)
    func = lambda x: base * (1.0 - np.exp(-rate * x))
    grad = lambda x: base * rate * np.exp(-rate * x)
    label = f"Exponential: {_fmt(a)} * (1 - e^(-{_fmt(b)}x))"
    return {"label": label, "type": "exp", "func": func, "grad": grad}


def make_power_return(a: float, p: float) -> Dict:
    base = float(a)
    power = float(p)
    func = lambda x: base * np.power(np.maximum(x, 0.0), power)
    grad = lambda x: base * power * np.power(np.maximum(x, 0.0), power - 1.0)
    label = f"Power: {_fmt(a)} * x^{_fmt(p)}"
    return {"label": label, "type": "power", "func": func, "grad": grad}


def make_quad_return(a: float, b: float) -> Dict:
    lin = float(a)
    quad = float(b)
    func = lambda x: lin * x - quad * x ** 2
    grad = lambda x: lin - 2.0 * quad * x
    label = f"Quadratic: {_fmt(a)}x - {_fmt(b)}x^2"
    return {"label": label, "type": "quad", "func": func, "grad": grad}


def _fmt(v: float) -> str:
    return f"{v:.6g}"


def _complex_step_gradient(func: Callable[[float], float], x: float, h: float = 1e-20) -> float:
    """Complex-step derivative of a scalar function at x."""
    return float(np.imag(func(complex(x, h))) / h)


class InvestmentOptimizer:
    """Optimal allocation of resources across investments.

    Maximizes the total return:
        R(x) = sum(f_i(x_i))
    subject to:
        sum(x_i) = budget            (total resource available)
        lower_i <= x_i <= upper_i    (per-investment bounds, x_i >= 0)

    Return functions may supply an analytic gradient; otherwise the
    gradient is estimated with a complex step.
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
        self.iterations: int = 0
        self.status: str = "unsolved"
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
                grad[i] = _complex_step_gradient(single, float(x[i]))
        return grad

    def solve(self) -> Tuple[str, Optional[np.ndarray]]:
        n = self.n
        hint = self.budget / n

        bounds = list(zip(self.lower, self.upper))
        constraints = [
            LinearConstraint(
                np.ones((1, n)),
                lb=self.budget,
                ub=self.budget,
            )
        ]

        result = minimize(
            fun=lambda x: -self._objective(x),
            x0=np.full(n, hint),
            jac=lambda x: -self._gradient(x),
            bounds=bounds,
            constraints=constraints,
            method=self.method,
            tol=self.tol,
            options={"ftol": self.tol},
        )
        self.iterations = int(getattr(result, "nit", 0) or 0)

        if result.success:
            self.status = "optimal"
            self.solution = np.asarray(result.x, dtype=float)
        else:
            self.status = f"not_optimal: {result.message}"
            self.solution = np.asarray(result.x, dtype=float) if result.x is not None else None

        if self.solution is not None:
            self.allocation = self.solution
            self.optimal_return = self._objective(self.solution)
            self.marginal_returns = self._gradient(self.solution)

        return self.status, self.solution

    def get_display(self) -> str:
        lines = ["Investment allocation optimization:"]
        lines.append(f"  Total budget: {self.budget:.6g}")
        lines.append(f"  Number of investments: {self.n}")
        for i, f in enumerate(self.funcs):
            lb = self.lower[i]
            ub = self.upper[i]
            lines.append(f"    [{i + 1}] {f['label']}  (bounds: {lb:.6g} to {ub:.6g})")

        if self.allocation is not None:
            lines.append("\n  Optimal allocation (share of budget):")
            for i, (val, f) in enumerate(zip(self.allocation, self.funcs)):
                pct = val / self.budget * 100 if self.budget > 0 else 0.0
                marg = self.marginal_returns[i] if self.marginal_returns is not None else 0.0
                lines.append(
                    f"    x{i + 1} = {val:.6g}  ({pct:.2f}%)  marginal return = {marg:.6g}"
                )
            if self.optimal_return is not None:
                lines.append(f"\n  Optimal total return: R* = {self.optimal_return:.10g}")
            lines.append(f"  Iterations: {self.iterations}")
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
        make_log_return(a=40.0, c=1.0),
        make_exp_return(a=60.0, b=0.05),
        make_quad_return(a=0.08, b=2e-5),
        make_log_return(a=25.0, c=0.5),
    ]
