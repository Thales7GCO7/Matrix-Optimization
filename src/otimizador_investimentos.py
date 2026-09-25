"""Alocação genérica não linear de recursos entre investimentos.

Maximiza o retorno total:
    R(x) = soma(f_i(x_i))
sujeito a:
    soma(x_i) = orçamento          (recurso total disponível)
    mínimo_i <= x_i <= máximo_i    (limites por investimento, x_i >= 0)

Para máxima precisão, as funções de retorno podem fornecer gradiente
analítico; senão o gradiente é estimado por diferenciação por passo
complexo.
"""

from typing import Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np
from scipy.optimize import LinearConstraint, minimize


def criar_retorno_log(a: float, c: float = 1.0) -> Dict:
    base = float(a)
    desloc = float(c)
    func = lambda x: base * np.log(x + desloc)
    grad = lambda x: base / (x + desloc)
    rotulo = f"Logarítmica: {_fmt(a)} * ln(x + {_fmt(c)})"
    return {"rotulo": rotulo, "tipo": "log", "func": func, "grad": grad}


def criar_retorno_exp(a: float, b: float) -> Dict:
    base = float(a)
    taxa = float(b)
    func = lambda x: base * (1.0 - np.exp(-taxa * x))
    grad = lambda x: base * taxa * np.exp(-taxa * x)
    rotulo = f"Exponencial: {_fmt(a)} * (1 - e^(-{_fmt(b)}x))"
    return {"rotulo": rotulo, "tipo": "exp", "func": func, "grad": grad}


def criar_retorno_potencia(a: float, p: float) -> Dict:
    base = float(a)
    pot = float(p)
    func = lambda x: base * np.power(np.maximum(x, 0.0), pot)
    grad = lambda x: base * pot * np.power(np.maximum(x, 0.0), pot - 1.0)
    rotulo = f"Potência: {_fmt(a)} * x^{_fmt(p)}"
    return {"rotulo": rotulo, "tipo": "potencia", "func": func, "grad": grad}


def criar_retorno_quadratico(a: float, b: float) -> Dict:
    lin = float(a)
    quad = float(b)
    func = lambda x: lin * x - quad * x ** 2
    grad = lambda x: lin - 2.0 * quad * x
    rotulo = f"Quadrática: {_fmt(a)}x - {_fmt(b)}x^2"
    return {"rotulo": rotulo, "tipo": "quadratica", "func": func, "grad": grad}


def _fmt(v: float) -> str:
    return f"{v:.6g}"


def _gradiente_passo_complexo(func: Callable[[float], float], x: float, h: float = 1e-20) -> float:
    """Derivada por passo complexo de uma função escalar em x."""
    return float(np.imag(func(complex(x, h))) / h)


class OtimizadorInvestimentos:
    """Alocação ótima de recursos entre investimentos.

    Maximiza o retorno total:
        R(x) = soma(f_i(x_i))
    sujeito a:
        soma(x_i) = orçamento          (recurso total disponível)
        mínimo_i <= x_i <= máximo_i    (limites por investimento, x_i >= 0)

    As funções de retorno podem fornecer gradiente analítico; senão o
    gradiente é estimado por passo complexo.
    """

    def __init__(
        self,
        funcoes_retorno: Sequence[Dict],
        orcamento: float,
        limites_min: Optional[Sequence[float]] = None,
        limites_max: Optional[Sequence[float]] = None,
        tol: float = 1e-10,
        metodo: str = "SLSQP",
    ):
        self.funcs = list(funcoes_retorno)
        self.n = len(self.funcs)
        self.orcamento = float(orcamento)
        self.minimo = (
            [float(v) for v in limites_min]
            if limites_min is not None
            else [0.0] * self.n
        )
        self.maximo = (
            [float(v) for v in limites_max]
            if limites_max is not None
            else [self.orcamento] * self.n
        )
        self.tol = tol
        self.metodo = metodo
        self.iteracoes: int = 0
        self.status: str = "nao_resolvido"
        self.solucao: Optional[np.ndarray] = None
        self.retorno_otimo: Optional[float] = None
        self.alocacao: Optional[np.ndarray] = None
        self.retornos_marginais: Optional[np.ndarray] = None

    def _objetivo(self, x) -> float:
        x = np.asarray(x, dtype=float)
        return float(sum(f["func"](np.float64(x[i])) for i, f in enumerate(self.funcs)))

    def _gradiente(self, x) -> np.ndarray:
        x = np.asarray(x, dtype=float)
        grad = np.zeros(self.n)
        for i, f in enumerate(self.funcs):
            if "grad" in f:
                grad[i] = f["grad"](np.float64(x[i]))
            else:
                unica = lambda xi, ii=i: self.funcs[ii]["func"](np.float64(xi))
                grad[i] = _gradiente_passo_complexo(unica, float(x[i]))
        return grad

    def resolver(self) -> Tuple[str, Optional[np.ndarray]]:
        n = self.n
        palpite = self.orcamento / n

        limites = list(zip(self.minimo, self.maximo))
        restricoes = [
            LinearConstraint(
                np.ones((1, n)),
                lb=self.orcamento,
                ub=self.orcamento,
            )
        ]

        resultado = minimize(
            fun=lambda x: -self._objetivo(x),
            x0=np.full(n, palpite),
            jac=lambda x: -self._gradiente(x),
            bounds=limites,
            constraints=restricoes,
            method=self.metodo,
            tol=self.tol,
            options={"ftol": self.tol},
        )
        self.iteracoes = int(getattr(resultado, "nit", 0) or 0)

        if resultado.success:
            self.status = "otimo"
            self.solucao = np.asarray(resultado.x, dtype=float)
        else:
            self.status = f"nao_otimo: {resultado.message}"
            self.solucao = np.asarray(resultado.x, dtype=float) if resultado.x is not None else None

        if self.solucao is not None:
            self.alocacao = self.solucao
            self.retorno_otimo = self._objetivo(self.solucao)
            self.retornos_marginais = self._gradiente(self.solucao)

        return self.status, self.solucao

    def obter_exibicao(self) -> str:
        linhas = ["Otimização da alocação de investimentos:"]
        linhas.append(f"  Orçamento total: {self.orcamento:.6g}")
        linhas.append(f"  Número de investimentos: {self.n}")
        for i, f in enumerate(self.funcs):
            lb = self.minimo[i]
            ub = self.maximo[i]
            linhas.append(f"    [{i + 1}] {f['rotulo']}  (limites: {lb:.6g} a {ub:.6g})")

        if self.alocacao is not None:
            linhas.append("\n  Alocação ótima (fração do orçamento):")
            for i, (val, f) in enumerate(zip(self.alocacao, self.funcs)):
                pct = val / self.orcamento * 100 if self.orcamento > 0 else 0.0
                marg = self.retornos_marginais[i] if self.retornos_marginais is not None else 0.0
                linhas.append(
                    f"    x{i + 1} = {val:.6g}  ({pct:.2f}%)  retorno marginal = {marg:.6g}"
                )
            if self.retorno_otimo is not None:
                linhas.append(f"\n  Retorno total ótimo: R* = {self.retorno_otimo:.10g}")
            linhas.append(f"  Iterações: {self.iteracoes}")
        else:
            linhas.append(f"\n  Status: {self.status}")
        return "\n".join(linhas)

    def obter_decomposicao_retorno(self) -> List[float]:
        if self.alocacao is None:
            return []
        return [
            float(self.funcs[i]["func"](np.float64(self.alocacao[i])))
            for i in range(self.n)
        ]


def carteira_padrao() -> List[Dict]:
    return [
        criar_retorno_log(a=40.0, c=1.0),
        criar_retorno_exp(a=60.0, b=0.05),
        criar_retorno_quadratico(a=0.08, b=2e-5),
        criar_retorno_log(a=25.0, c=0.5),
    ]
