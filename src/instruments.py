"""Modelo de ativo de investimento e calculo bruto -> liquido.

Um `Ativo` e caracterizado pela taxa (com periodo e base), prazo ate o
resgate, imposto e taxa administrativa. A renda e modelada como
serie de aportes:

- aporte inicial unico A (alocacao de capital hoje);
- aporte mensal P (recorrente, postecipado, ao fim de cada mes).

A funcao de lucro liquido final e linear em A e em P, o que permite
alocacao otima por selecao gulosa (energia economica: aplicar primeiro
onde o retorno liquido anualizado e maior).
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from . import math_finance as mf
from . import tax

#: Modos aceitos para base da taxa e tipos de imposto/taxa.
BASES_TAXA = ["efetiva", "nominal"]


@dataclass(frozen=True)
class Ativo:
    nome: str
    taxa: float = 0.10
    periodo: str = "anual"
    base: str = "efetiva"
    prazo_meses: int = 12
    imposto_modo: str = "isento"
    imposto_percentual: float = 0.0
    admin_modo: str = "nenhuma"
    admin_percentual: float = 0.0
    aporte_inicial_min: float = 0.0
    aporte_inicial_max: Optional[float] = None
    usa_aporte_mensal: bool = False
    aporte_mensal_max: Optional[float] = None

    @property
    def taxa_anual(self) -> float:
        return mf.taxa_anual_efetiva(self.taxa, self.periodo, self.base)

    @property
    def taxa_mensal(self) -> float:
        return mf.taxa_mensal_equivalente(self.taxa_anual)

    @property
    def aliquota_imposto(self) -> float:
        return tax.aliquota_imposto(self.imposto_modo, self.prazo_meses, self.imposto_percentual)

    def __post_init__(self):
        if not self.nome:
            raise ValueError("Ativo sem nome.")
        if self.prazo_meses <= 0:
            raise ValueError(f"Prazo invalido para o ativo {self.nome!r}: {self.prazo_meses}.")
        if self.taxa <= -1.0:
            raise ValueError(f"Taxa invalida para o ativo {self.nome!r}.")

    def label(self) -> str:
        taxa_pct = self.taxa * 100
        base = "ef." if self.base == "efetiva" else "nom."
        resumo = f"{self.nome} | {taxa_pct:.3g}% a.{self._sigla_periodo(self.periodo)} ({base})"
        resumo += f" | {self.prazo_meses} meses"
        if self.imposto_modo == "ir_tabela":
            resumo += f" | IR tabela ({tax.rotulo_ir_tabela(self.prazo_meses * 30)})"
        elif self.imposto_modo == "fixo":
            resumo += f" | IR {self.imposto_percentual * 100:.2g}%"
        elif self.imposto_modo == "isento":
            resumo += " | isento"
        if self.admin_modo != "nenhuma":
            resumo += f" | adm {self.admin_percentual * 100:.2g}%/{self.admin_modo}"
        return resumo

    @staticmethod
    def _sigla_periodo(periodo: str) -> str:
        return {"anual": "a", "semestral": "s", "trimestral": "t", "bimestral": "b",
                "mensal": "m", "semanal": "sem", "diaria": "d"}.get(periodo, "a")


def montante_aporte_unico(ativo: Ativo, valor: float) -> float:
    """Valor bruto acumulado de um aporte unico ate o resgate."""
    if valor <= 0.0:
        return 0.0
    return mf.montante_aporte_unico(float(valor), ativo.taxa_anual, ativo.prazo_meses)


def montante_serie_mensal(ativo: Ativo, pmt: float) -> float:
    """Valor bruto acumulado de aportes mensais postecipados (pmt) ateh o resgate."""
    if pmt <= 0.0:
        return 0.0
    return mf.montante_serie_postecipada(float(pmt), ativo.taxa_mensal, ativo.prazo_meses)


def deducoes(ativo: Ativo, montante_bruto: float, rendimento_bruto: float, aportado: float) -> Dict[str, float]:
    """Deducoes em R$ de imposto e taxa administrativa."""
    imposto = tax.imposto_sobre_taxa(ativo.aliquota_imposto, rendimento_bruto)
    admin = tax.taxa_admin_em_reais(
        ativo.admin_modo,
        ativo.admin_percentual,
        montante_bruto,
        rendimento_bruto,
        aportado,
        ativo.prazo_meses,
    )
    return {"imposto": imposto, "admin": admin}


def resumo_ativo(ativo: Ativo, aporte_inicial: float, aporte_mensal: float) -> Dict:
    """Resumo do investimento no ativo dados os aportes (valores do fluxo real)."""
    a = float(aporte_inicial)
    p = float(aporte_mensal)
    m = ativo.prazo_meses

    f_total = montante_aporte_unico(ativo, a) + montante_serie_mensal(ativo, p)
    aportado = a + p * m
    rend_bruto = f_total - aportado

    ded = deducoes(ativo, f_total, rend_bruto, aportado)
    montante_liquido = f_total - ded["imposto"] - ded["admin"]
    lucro = montante_liquido - aportado

    return {
        "aporte_inicial": a,
        "aporte_mensal": p,
        "aportado_total": aportado,
        "montante_bruto": f_total,
        "rendimento_bruto": rend_bruto,
        "imposto": ded["imposto"],
        "admin": ded["admin"],
        "aliquota_imposto": ativo.aliquota_imposto,
        "montante_liquido": montante_liquido,
        "lucro_liquido": lucro,
    }


def projecao_mensal(ativo: Ativo, aporte_inicial: float, aporte_mensal: float) -> List[Dict]:
    """Projecao mes a mes do montante liquido e do capital aportado.

    Ilustrativa: as deducoes (imposto e taxa administrativa) que so
    ocorrem no resgate sao distribuidas linearmente ao longo do prazo,
    de modo que no mes final a projecao coincide exatamente com o
    resumo real. Usada para payback e graficos.
    """
    a = float(aporte_inicial)
    p = float(aporte_mensal)
    m = ativo.prazo_meses
    r_ano = ativo.taxa_anual
    i_m = ativo.taxa_mensal

    resumo = resumo_ativo(ativo, a, p)
    ded_total = resumo["imposto"] + resumo["admin"]

    pts = []
    for t in range(0, m + 1):
        if t == 0:
            f = a
        else:
            f = a * (1.0 + r_ano) ** (t / 12.0)
            f += p * mf.fator_serie_postecipada(i_m, t)
        fracao = t / m if m else 1.0
        ml = max(f - ded_total * fracao, 0.0)
        pts.append({"mes": t, "montante_liquido": ml, "aportado": a + p * t})
    return pts


def taxa_liquida_anualizada(ativo: Ativo) -> float:
    """Retorno liquido anualizado do ativo (base para o ranking de alocacao).

    Calculado com aporte unico unitario (a funcao e linear em A, logo a
    taxa nao depende do valor). Le em conta imposto e taxa administrativa.
    """
    resumo = resumo_ativo(ativo, 1.0, 0.0)
    ml = resumo["montante_liquido"]
    if ml <= 0.0:
        return float("-inf")
    return (ml) ** (12.0 / ativo.prazo_meses) - 1.0