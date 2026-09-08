from typing import Callable, List, Optional, Sequence, Tuple, Union

import numpy as np

TScalarOrVector = Union[float, Sequence[float]]


def _as_array(x: TScalarOrVector) -> np.ndarray:
    return np.asarray(x, dtype=float)


def numerical_jacobian(func: Callable, x: np.ndarray) -> np.ndarray:
    n = x.size
    jac = np.zeros((n, n))
    h_cs = np.cbrt(np.finfo(float).eps)

    complex_ok = True
    for j in range(n):
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
        jac[:, j] = np.atleast_1d(fj).imag / h_cs

    if complex_ok and np.all(np.isfinite(jac)) and np.any(jac != 0.0):
        return jac

    tol = np.finfo(float).eps
    h = np.sqrt(tol) * (1.0 + np.abs(x))
    jac = np.zeros((n, n))
    for j in range(n):
        xp = x.copy()
        xm = x.copy()
        xp[j] += h[j]
        xm[j] -= h[j]
        jac[:, j] = (func(xp) - func(xm)) / (2.0 * h[j])
    return jac


class NewtonRaphson:
    """Resolver equacoes nao lineares pelo metodo de Newton-Raphson.

    Suporta equacoes escalares f(x) = 0 e sistemas F(x) = 0.
    O Jacobiano e calculado por diferenciacao numerica (complex step
    quando possivel) ou fornecido pelo usuario.

    Utiliza Newton amortecido (backtracking line search) para melhorar
    a convergencia global.
    """

    def __init__(
        self,
        func: Callable,
        x0: TScalarOrVector,
        jac: Optional[Callable] = None,
        tol: float = 1e-12,
        max_iter: int = 200,
        line_search: bool = True,
    ):
        self.func = func
        self.x0 = _as_array(x0)
        self.n = self.x0.size
        self.is_scalar = self.n == 1
        self.jac = jac
        self.tol = tol
        self.max_iter = max_iter
        self.line_search = line_search
        self.steps: List[str] = []
        self.status: str = "nao_resolvido"
        self.solution: Optional[np.ndarray] = None
        self.iterations: int = 0
        self.residual: Optional[float] = None
        self.norms: List[float] = []

    def _f(self, x: np.ndarray) -> np.ndarray:
        out = np.asarray(self.func(x))
        return out.reshape(-1) if out.ndim > 0 else np.array([out])

    def _eval_jac(self, x: np.ndarray) -> np.ndarray:
        if self.jac is not None:
            J = np.asarray(self.jac(x), dtype=float)
            return np.atleast_2d(J).reshape(self.n, self.n)
        return numerical_jacobian(self._f, x)

    def solve(self) -> Tuple[str, Optional[np.ndarray]]:
        self.steps = []
        self.norms = []
        x = self.x0.astype(float)
        f = self._f(x)

        self.steps.append(
            f"Chute inicial: x = {self._fmt_vec(x)}, F(x) = {self._fmt_vec(f)}"
        )

        for it in range(1, self.max_iter + 1):
            self.iterations = it
            norm_f = np.linalg.norm(f)
            self.norms.append(float(norm_f))
            if norm_f <= self.tol:
                self.status = "convergiu"
                self.residual = norm_f
                self.solution = x
                self.steps.append(
                    f"Iteracao {it}: ||F(x)|| = {norm_f:.3e} <= tol ({self.tol})"
                )
                self.steps.append(f"Solucao convergida: x = {self._fmt_vec(x)}")
                return self.status, self.solution

            J = self._eval_jac(x)

            if (
                self.is_scalar
                and abs(float(np.linalg.det(J.reshape(1, 1)))) < 100.0 * self.tol
            ):
                self.status = "jacobiano_singular"
                self.steps.append(
                    f"Iteracao {it}: derivada ~0 em x = {self._fmt_vec(x)}."
                )
                return self.status, None

            try:
                delta = np.linalg.solve(J, -f)
            except np.linalg.LinAlgError:
                self.status = "jacobiano_singular"
                self.steps.append(
                    f"Iteracao {it}: Jacobiano singular, solucao do sistema falhou."
                )
                return self.status, None

            if not np.all(np.isfinite(delta)):
                self.status = "divergente"
                self.steps.append(
                    f"Iteracao {it}: passo produziu valores nao finitos (divergencia)."
                )
                return self.status, None

            if self.line_search:
                alpha = self._backtrack(x, f, delta)
            else:
                alpha = 1.0

            x_new = x + alpha * delta
            f_new = self._f(x_new)
            norm_old = np.linalg.norm(f)
            norm_new = np.linalg.norm(f_new)

            self.steps.append(
                f"Iteracao {it}: x = {self._fmt_vec(x)} -> {self._fmt_vec(x_new)}, "
                f"||F|| = {norm_old:.3e} -> {norm_new:.3e}"
            )

            x = x_new
            f = f_new

        self.status = "max_iteracoes"
        self.residual = np.linalg.norm(f)
        self.steps.append(
            f"Numero maximo de iteracoes atingido ({self.max_iter}). "
            f"Residuo final: {np.linalg.norm(f):.3e}"
        )
        return self.status, None

    def _backtrack(
        self, x: np.ndarray, f: np.ndarray, delta: np.ndarray
    ) -> float:
        alpha = 1.0
        beta = 0.5
        base_norm = np.linalg.norm(f)
        for _ in range(40):
            x_trial = x + alpha * delta
            f_trial = self._f(x_trial)
            if np.all(np.isfinite(x_trial)) and np.linalg.norm(f_trial) < base_norm:
                return alpha
            alpha *= beta
        return alpha

    @staticmethod
    def _fmt_vec(v) -> str:
        v = np.atleast_1d(np.asarray(v, dtype=float))
        return "[" + ", ".join(f"{val:.10g}" for val in v) + "]"

    def get_display(self) -> str:
        lines = ["Resolucao de equacoes nao lineares (Newton-Raphson):"]
        lines.append(f"  Ponto inicial: {self._fmt_vec(self.x0)}")
        lines.append(f"  Metodo: {'Newton amortecido' if self.line_search else 'Newton clasico'}")
        lines.append(f"  Iteracoes: {self.iterations}")

        if self.solution is not None:
            if self.is_scalar:
                lines.append(
                    f"  Solucao: x = {self.solution[0]:.10g}"
                )
            else:
                names = ", ".join(
                    f"x{i + 1} = {val:.10g}"
                    for i, val in enumerate(self.solution)
                )
                lines.append(f"  Solucao: {names}")
            if self.residual is not None:
                lines.append(f"  Residuo final ||F(x)|| = {self.residual:.3e}")
        else:
            lines.append(f"  Status: {self.status}")
        return "\n".join(lines)


def solve_scalar(
    func: Callable,
    x0: float,
    deriv: Optional[Callable] = None,
    tol: float = 1e-12,
    max_iter: int = 200,
) -> Tuple[str, Optional[float]]:
    solver = NewtonRaphson(
        func=func,
        x0=[x0],
        jac=(lambda x: np.array([deriv(x[0])])) if deriv is not None else None,
        tol=tol,
        max_iter=max_iter,
    )
    status, solution = solver.solve()
    if solution is not None:
        return status, float(solution[0])
    return status, None