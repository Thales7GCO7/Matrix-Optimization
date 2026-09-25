"""Modelo de ativos de investimento e cálculo de bruto para líquido.

Um `Ativo` caracteriza-se por sua taxa (com período e base), seu prazo
até o resgate, o imposto de renda e uma taxa administrativa. A renda é
modelada como uma série de aportes:

- um aporte inicial único A (capital alocado hoje);
- um aporte mensal P (recorrente, postecipado, no fim de cada mês).

A função de lucro líquido final é linear em A e em P, o que permite uma
alocação ótima por seleção gulosa (intuição econômica: investir primeiro
onde o retorno líquido anualizado é maior).
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from . import matematica_financeira as mf
from . import impostos
from . import matriz

#: Bases de taxa e modos de imposto/taxa aceitos.
BASES_TAXA = ["efetiva", "nominal"]


@dataclass(frozen=True)
class Ativo:
    nome: str
    taxa: float = 0.10
    periodo: str = "anual"
    base: str = "efetiva"
    prazo_meses: int = 12
    modo_imposto: str = "isento"
    imposto_pct: float = 0.0
    tabela_imposto: Optional[Tuple[Tuple[float, float], ...]] = None
    chave_tabela: str = "prazo"
    modo_taxa: str = "nenhuma"
    taxa_pct: float = 0.0
    minimo_inicial: float = 0.0
    maximo_inicial: Optional[float] = None
    usa_mensal: bool = False
    maximo_mensal: Optional[float] = None

    @property
    def taxa_anual(self) -> float:
        return mf.taxa_anual_efetiva(self.taxa, self.periodo, self.base)

    @property
    def taxa_mensal(self) -> float:
        return mf.taxa_mensal_equivalente(self.taxa_anual)

    @property
    def aliquota(self) -> float:
        consulta = float(self.prazo_meses) if self.chave_tabela == "prazo" else 0.0
        return impostos.resolver_aliquota(
            self.modo_imposto, self.imposto_pct, self.tabela_imposto,
            self.chave_tabela, consulta,
        )

    def __post_init__(self):
        if not self.nome:
            raise ValueError("Ativo sem nome.")
        if self.prazo_meses <= 0:
            raise ValueError(f"Prazo inválido para o ativo {self.nome!r}: {self.prazo_meses}.")
        if self.taxa <= -1.0:
            raise ValueError(f"Taxa inválida para o ativo {self.nome!r}.")

    def rotulo(self) -> str:
        taxa_pct = self.taxa * 100
        base = "ef." if self.base == "efetiva" else "nom."
        resumo = f"{self.nome} | {taxa_pct:.3g}% a.a.-{self._abrev_periodo(self.periodo)} ({base})"
        resumo += f" | {self.prazo_meses} meses"
        if self.modo_imposto == "fixo":
            resumo += f" | IR {self.imposto_pct * 100:.2g}%"
        elif self.modo_imposto == "tabela":
            resumo += " | tabela de IR"
        elif self.modo_imposto == "isento":
            resumo += " | isento"
        if self.modo_taxa != "nenhuma":
            resumo += f" | taxa {self.taxa_pct * 100:.2g}%/{self.modo_taxa}"
        return resumo

    @staticmethod
    def _abrev_periodo(periodo: str) -> str:
        return {"anual": "a", "semestral": "s", "trimestral": "t", "bimestral": "b",
                "mensal": "m", "semanal": "s", "diaria": "d"}.get(periodo, "a")


def bruto_aporte_unico(ativo: Ativo, principal: float) -> float:
    """Valor bruto acumulado de um aporte único mantido até o resgate."""
    if principal <= 0.0:
        return 0.0
    return mf.valor_futuro_aporte_unico(float(principal), ativo.taxa_anual, ativo.prazo_meses)


def bruto_serie_mensal(ativo: Ativo, pmt: float) -> float:
    """Valor bruto acumulado de aportes mensais postecipados (pmt) até o resgate."""
    if pmt <= 0.0:
        return 0.0
    return mf.valor_futuro_serie_postecipada(float(pmt), ativo.taxa_mensal, ativo.prazo_meses)


def deducoes(ativo: Ativo, valor_bruto: float, ganho_bruto: float, aportado: float) -> Dict[str, float]:
    """Deduções de imposto de renda e taxa administrativa em moeda.

    Delega para a função genérica :func:`impostos.calcular_valor_liquido`, de modo que
    todo tipo de investimento compartilhe uma única lógica de valor líquido.
    """
    res = impostos.calcular_valor_liquido(
        valor_bruto, aportado, ativo.modo_imposto, ativo.imposto_pct,
        ativo.modo_taxa, ativo.taxa_pct, ativo.prazo_meses,
        getattr(ativo, "tabela_imposto", None),
        getattr(ativo, "chave_tabela", "prazo"),
    )
    return {"imposto": res["imposto"], "taxa": res["taxa"]}


def resumo_ativo(ativo: Ativo, aporte_inicial: float, aporte_mensal: float) -> Dict:
    """Resumo do investimento no ativo dados seus aportes (valores efetivos de caixa).

    Pipeline genérica compartilhada por todo tipo de investimento: primeiro a
    capitalização bruta, depois :func:`impostos.calcular_valor_liquido` (imposto + taxa -> líquido).
    """
    a = float(aporte_inicial)
    p = float(aporte_mensal)
    m = ativo.prazo_meses

    bruto_total = bruto_aporte_unico(ativo, a) + bruto_serie_mensal(ativo, p)
    aportado = a + p * m

    liquido = impostos.calcular_valor_liquido(
        bruto_total, aportado, ativo.modo_imposto, ativo.imposto_pct,
        ativo.modo_taxa, ativo.taxa_pct, m,
        ativo.tabela_imposto, ativo.chave_tabela,
    )

    return {
        "aporte_inicial": a,
        "aporte_mensal": p,
        "total_aportado": aportado,
        "valor_bruto": bruto_total,
        "ganho_bruto": liquido["ganho_bruto"],
        "imposto": liquido["imposto"],
        "taxa": liquido["taxa"],
        "aliquota": liquido["aliquota"],
        "valor_liquido": liquido["valor_liquido"],
        "lucro_liquido": liquido["lucro_liquido"],
    }


def projecao_mensal(ativo: Ativo, aporte_inicial: float, aporte_mensal: float) -> List[Dict]:
    """Projeção mês a mês do valor líquido e do capital aportado.

    Ilustrativa: as deduções (imposto de renda e taxas) que só ocorrem no
    resgate são distribuídas linearmente ao longo do prazo, de modo que o mês
    final da projeção coincide exatamente com o resumo efetivo. Usada no payback
    e nos gráficos.
    """
    a = float(aporte_inicial)
    p = float(aporte_mensal)
    m = ativo.prazo_meses
    taxa_a = ativo.taxa_anual
    taxa_m = ativo.taxa_mensal

    resumo = resumo_ativo(ativo, a, p)
    total_ded = resumo["imposto"] + resumo["taxa"]

    pontos = []
    for t in range(0, m + 1):
        if t == 0:
            f = a
        else:
            f = a * (1.0 + taxa_a) ** (t / 12.0)
            f += p * mf.fator_serie_postecipada(taxa_m, t)
        fracao = t / m if m else 1.0
        liquido = max(f - total_ded * fracao, 0.0)
        pontos.append({"mes": t, "valor_liquido": liquido, "aportado": a + p * t})
    return pontos


def retorno_liquido_anualizado(ativo: Ativo) -> float:
    """Retorno líquido anualizado do ativo (base do ranking de alocação).

    Calculado com um aporte único unitário (a função é linear em A, logo a
    taxa não depende do valor). Considera imposto de renda e taxas
    administrativas.
    """
    resumo = resumo_ativo(ativo, 1.0, 0.0)
    liquido = resumo["valor_liquido"]
    if liquido <= 0.0:
        return float("-inf")
    return (liquido) ** (12.0 / ativo.prazo_meses) - 1.0


def vetor_retornos_liquidos(ativos: List[Ativo]) -> np.ndarray:
    """Invólucro de matriz.vetor_retornos_liquidos."""
    return matriz.vetor_retornos_liquidos(ativos)
