"""Matematica financeira: conversao de taxas, capitalizacao composta e series.

Convencoes adotadas em todo o projeto:
- Taxas sao sempre fracoes decimais (ex.: 0.135 = 13,5% a.a.).
- A taxa de cada ativo e informada com um periodo de capitalizacao
  (anual, semestral, etc.) e uma base "efetiva" ou "nominal".
- Internamente tudo e convertido para a taxa efetiva anual e, quando
  necessario, para a taxa mensal equivalente.
"""

from typing import Optional

#: Numero de periodos por ano para cada periodo de capitalizacao.
PERIODOS = {
    "anual": 1,
    "semestral": 2,
    "trimestral": 4,
    "bimestral": 6,
    "mensal": 12,
    "semanal": 52,
    "diaria": 365,
}


def taxa_anual_efetiva(taxa: float, periodo: str = "anual", base: str = "efetiva") -> float:
    """Converte (taxa, periodo, base) para a taxa efetiva anual.

    - base "efetiva": a taxa ja e do proprio periodo (composto). Ex.:
      taxa mensal 1% -> r_ano = (1.01)**12 - 1.
    - base "nominal": a taxa e nominal anual; a taxa do periodo e
      taxa/periodos e a efetiva anual resulta da composicao. Ex.:
      13% a.a. nominal com capitalizacao mensal -> (1 + 0.13/12)**12 - 1.
    """
    k = PERIODOS.get(periodo)
    if k is None:
        raise ValueError(f"Periodo de capitalizacao invalido: {periodo!r}")
    taxa = float(taxa)
    if base == "nominal":
        return (1.0 + taxa / k) ** k - 1.0
    return (1.0 + taxa) ** k - 1.0


def taxa_mensal_equivalente(taxa_anual: float) -> float:
    """Taxa mensal equivalente a uma taxa efetiva anual dada."""
    return (1.0 + float(taxa_anual)) ** (1.0 / 12.0) - 1.0


def taxa_anual_equivalente(taxa_periodo: float, periodos_ano: int) -> float:
    """Taxa efetiva anual equivalente a uma taxa do periodo (composta)."""
    return (1.0 + float(taxa_periodo)) ** periodos_ano - 1.0


def taxa_periodica_efetiva(taxa_anual: float, periodos_ano: int) -> float:
    """Taxa efetiva de um periodo equivalente a uma taxa efetiva anual."""
    return (1.0 + float(taxa_anual)) ** (1.0 / periodos_ano) - 1.0


def montante_aporte_unico(valor: float, taxa_anual: float, prazo_meses: int) -> float:
    """Valor futuro de um aporte unico com capitalizacao composta por prazo_meses."""
    return float(valor) * (1.0 + float(taxa_anual)) ** (float(prazo_meses) / 12.0)


def fator_serie_postecipada(taxa_mensal: float, n_meses: int) -> float:
    """Fator de acumulacao de uma serie uniforme postecipada de n aportes.

    Soma de (1+i)^t para t = 0 .. n-1. O ultimo aporte nao rende.
    """
    if abs(float(taxa_mensal)) < 1e-14:
        return float(n_meses)
    return ((1.0 + taxa_mensal) ** n_meses - 1.0) / taxa_mensal


def montante_serie_postecipada(pmt: float, taxa_mensal: float, n_meses: int) -> float:
    """Valor futuro de aportes mensais iguais (postecipados) por n meses."""
    return float(pmt) * fator_serie_postecipada(taxa_mensal, n_meses)


def fator_serie_descontada(taxa_mensal: float, n_meses: int) -> float:
    """Soma de (1+i)^(-t) para t = 1 .. n (fator de desconto de serie)."""
    if abs(float(taxa_mensal)) < 1e-14:
        return float(n_meses)
    q = 1.0 / (1.0 + taxa_mensal)
    return q * (1.0 - q ** n_meses) / (1.0 - q)


def tir_de_fluxo(
    fluxos,
    lo: float = -0.9999,
    hi: float = 10.0,
    pontos: int = 6000,
) -> Optional[float]:
    """Taxa interna de retorno (por periodo) de um fluxo de caixa.

    Retorna a taxa por periodo que zera o VPL. Prefere a raiz positiva
    (retorno economico do investimento); caso nao exista raiz positiva,
    retorna a raiz negativa mais proxima de zero se houver. Se nenhuma
    raiz existir no intervalo, retorna None.
    """
    import numpy as np

    fluxos = np.asarray(fluxos, dtype=float)
    if fluxos.size < 2:
        return None

    def npv(r):
        t = np.arange(fluxos.size)
        return float(np.sum(fluxos / (1.0 + r) ** t))

    from scipy.optimize import brentq

    def _achar(lo_r, hi_r):
        xs = np.linspace(lo_r, hi_r, pontos)
        ys = np.array([npv(x) for x in xs])
        for i in range(1, len(xs)):
            if ys[i - 1] == 0.0:
                return float(xs[i - 1])
            if ys[i - 1] * ys[i] < 0.0:
                try:
                    root = brentq(npv, xs[i - 1], xs[i], xtol=1e-12, rtol=1e-12)
                except Exception:
                    return None
                if np.isfinite(root):
                    return float(root)
        return None

    raiz_positiva = _achar(0.0, hi)
    if raiz_positiva is not None:
        return raiz_positiva
    return _achar(max(lo, -1.0 + 1e-6), 0.0)


def tma_por_indicadores(selic: float, ipca: float) -> float:
    """Taxa minima de atratividade como juro real: (1+selic)/(1+ipca) - 1."""
    ipca = float(ipca)
    if (1.0 + ipca) <= 0.0:
        raise ValueError("IPCA invalido.")
    return (1.0 + float(selic)) / (1.0 + ipca) - 1.0