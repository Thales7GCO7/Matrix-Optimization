from typing import Callable, List, Optional, Sequence, Tuple, Union

import numpy as np
from scipy.optimize import minimize

TVector = Union[float, Sequence[float]]


def _as_array(x: TVector) -> np.ndarray:
    return np.atleast_1d(np.asarray(x, dtype=float))


def numerical_gradient(func: Callable, x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    h_cs = np.cbrt(np.finfo(float).eps)

    grad_cs = np.zeros_like(x, dtype=float)
    complex_ok = True
    for j in range(x.size):
        step = np.zeros_like(x, dtype=complex)
        step[j] = h_cs * 1j
        try:
            fj = func(x.astype(complex) + step)
        except Exception:
            complex_ok = False
            break
        if not np.iscomplexobj(fj):
            complex_ok = False
            break
        grad_cs[j] = np.asarray(fj).imag / h_cs

    h = np.sqrt(np.finfo(float).eps) * (1.0 + np.abs(x))
    grad_cd = np.zeros_like(x, dtype=float)
    for j in range(x.size):
        xp = x.copy()
        xm = x.copy()
        xp[j] += h[j]
        xm[j] -= h[j]
        grad_cd[j] = (func(xp) - func(xm)) / (2.0 * h[j])

    if complex_ok and np.all(np.isfinite(grad_cs)):
        scale = np.linalg.norm(grad_cd)
        diff = np.linalg.norm(grad_cs - grad_cd)
        if scale == 0.0 or diff <= 1e-3 * max(scale, 1e-12):
            return grad_cs
    return grad_cd


def numerical_hessian(func: Callable, x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    n = x.size
    hess = np.zeros((n, n))
    h = np.cbrt(np.finfo(float).eps) ** 0.75 * (1.0 + np.abs(x))
    for i in range(n):
        for j in range(n):
            xpp = x.copy()
            xpp[i] += h[i]
            xpp[j] += h[j]
            xpm = x.copy()
            xpm[i] += h[i]
            xpm[j] -= h[j]
            xmp = x.copy()
            xmp[i] -= h[i]
            xmp[j] += h[j]
            xmm = x.copy()
            xmm[i] -= h[i]
            xmm[j] -= h[j]
            if i == j:
                hess[i, j] = (
                    func(xpp) + func(xmm) - 2.0 * func(x)
                ) / (4.0 * h[i] * h[j])
            else:
                hess[i, j] = (
                    func(xpp) - func(xpm) - func(xmp) + func(xmm)
                ) / (4.0 * h[i] * h[j])
    return hess


def _objective_wrapper(func: Callable, maximize: bool) -> Callable:
    sign = -1.0 if maximize else 1.0
    return lambda x: sign * float(func(x))


class NonlinearOptimizer:
    """Otimizacao nao linear via SciPy (com ou sem restricoes).

    Maximiza ou minimiza uma funcao objetivo escalar sujeita a:
      - restricoes de igualdade: g(x) = 0
      - restricoes de desigualdade: g(x) <= 0 (tipo 'ineq' => g(x) >= 0)
      - limites por variavel (bounds)

    Gradientes e Hessianas sao obtidos por diferenciacao complex-step,
    fornecendo precisao de maquina, ou podem ser passados analiticamente.
    """

    def __init__(
        self,
        objective: Callable,
        x0: TVector,
        gradient: Optional[Callable] = None,
        hessian: Optional[Callable] = None,
        bounds: Optional[Sequence[Tuple[float, float]]] = None,
        constraints: Optional[
            List[Union[dict, "scipy.optimize.NonlinearConstraint"]]
        ] = None,
        maximize: bool = True,
        method: Optional[str] = None,
        tol: float = 1e-10,
        options: Optional[dict] = None,
    ):
        self.objective = objective
        self.x0 = _as_array(x0)
        self.gradient = gradient
        self.hessian = hessian
        self.bounds = bounds
        self.constraints = constraints
        self.maximize = maximize
        self.method = method
        self.tol = tol
        self.options = options or {}

        self.opt = None
        self.status: str = "nao_resolvido"
        self.solution: Optional[np.ndarray] = None
        self.optimal_value: Optional[float] = None
        self.iterations: int = 0
        self.message: str = ""

    def _choose_method(self) -> str:
        if self.method:
            return self.method
        if self.constraints or self.bounds is not None:
            return "SLSQP"
        return "BFGS"

    def solve(self) -> Tuple[str, Optional[np.ndarray]]:
        sign = -1.0 if self.maximize else 1.0
        wrapped = _objective_wrapper(self.objective, self.maximize)

        if self.gradient is not None:
            jac = lambda x: sign * np.asarray(self.gradient(x), dtype=float)
        else:
            jac = lambda x: sign * numerical_gradient(self.objective, _as_array(x))

        hess = None
        if self.hessian is not None:
            hess = lambda x: sign * np.asarray(self.hessian(x), dtype=float)

        method = self._choose_method()
        default_opts = {"maxiter": 500}
        if method == "SLSQP":
            default_opts.update({"ftol": self.tol, "disp": False})
        elif method == "trust-constr":
            default_opts.update({"gtol": self.tol})
        else:
            default_opts.update({"gtol": self.tol, "maxiter": 500})
        default_opts.update(self.options)

        try:
            self.opt = minimize(
                fun=wrapped,
                x0=self.x0,
                jac=jac,
                hess=hess,
                bounds=self.bounds,
                constraints=self.constraints,
                method=method,
                tol=self.tol,
                options=default_opts,
            )
        except Exception as exc:
            self.status = f"erro: {exc}"
            self.message = str(exc)
            return self.status, None

        self.status = "otimo" if self.opt.success or self.opt.status in (1, 4) else "falhou"
        self.message = str(self.opt.message)
        self.iterations = int(getattr(self.opt, "nit", 0)) or int(
            getattr(self.opt, "iterations", 0)
        )
        if self.opt.x is not None:
            self.solution = np.asarray(self.opt.x, dtype=float)
            if self.opt.fun is not None and np.isfinite(self.opt.fun):
                self.optimal_value = float(sign * self.opt.fun)
        return self.status, self.solution

    def get_display(self) -> str:
        lines = ["Otimizacao nao linear (SciPy):"]
        lines.append(
            f"  Objetivo: {'maximizar' if self.maximize else 'minimizar'}"
        )
        lines.append(f"  Metodo: {self._choose_method()}")
        lines.append(f"  Ponto inicial: {self._fmt(self.x0)}")

        if self.solution is not None:
            if self.solution.size == 1:
                lines.append(f"  Solucao: x = {self.solution[0]:.10g}")
            else:
                names = ", ".join(
                    f"x{i + 1} = {val:.10g}"
                    for i, val in enumerate(self.solution)
                )
                lines.append(f"  Solucao: {names}")
            if self.optimal_value is not None:
                lines.append(f"  Valor otimo: z* = {self.optimal_value:.10g}")
            if self.iterations:
                lines.append(f"  Iteracoes: {self.iterations}")
        else:
            lines.append(f"  Status: {self.status}")
        if self.message:
            lines.append(f"  Mensagem: {self.message}")
        return "\n".join(lines)

    @staticmethod
    def _fmt(v) -> str:
        v = np.atleast_1d(np.asarray(v, dtype=float))
        return "[" + ", ".join(f"{val:.6g}" for val in v) + "]"


def optimize_unconstrained(
    objective: Callable,
    x0: TVector,
    gradient: Optional[Callable] = None,
    hessian: Optional[Callable] = None,
    maximize: bool = True,
    tol: float = 1e-10,
) -> Tuple[str, Optional[np.ndarray]]:
    return NonlinearOptimizer(
        objective=objective,
        x0=x0,
        gradient=gradient,
        hessian=hessian,
        maximize=maximize,
        tol=tol,
    ).solve()