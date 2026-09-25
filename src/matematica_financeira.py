"""Matemática financeira: conversão de taxas, juros compostos e séries de pagamentos.

Convenções usadas em todo o projeto:
- Taxas são sempre frações decimais (ex.: 0,135 = 13,5% a.a.).
- A taxa de cada ativo é cotada com um período de capitalização
  (anual, semestral etc.) e uma base "efetiva" ou "nominal".
- Internamente tudo é convertido para a taxa anual efetiva e,
  quando necessário, para a taxa mensal equivalente.
"""

from typing import Optional

#: Número de períodos por ano para cada período de capitalização.
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
    """Converte uma trinca (taxa, período, base) para a taxa anual efetiva.

    - Base "efetiva": a taxa já pertence ao próprio período
      (capitalizada). Ex.: 1% ao mês -> r_ano = (1,01)**12 - 1.
    - Base "nominal": a taxa é nominal anual; a taxa por período é
      taxa/períodos e a taxa anual efetiva decorre da capitalização.
      Ex.: 13% a.a. nominal com capitalização mensal ->
      (1 + 0,13/12)**12 - 1.
    """
    k = PERIODOS.get(periodo)
    if k is None:
        raise ValueError(f"Período de capitalização inválido: {periodo!r}")
    taxa = float(taxa)
    if base == "nominal":
        return (1.0 + taxa / k) ** k - 1.0
    return (1.0 + taxa) ** k - 1.0


def taxa_mensal_equivalente(taxa_anual: float) -> float:
    """Taxa mensal equivalente a uma dada taxa anual efetiva."""
    return (1.0 + float(taxa_anual)) ** (1.0 / 12.0) - 1.0


def taxa_anual_equivalente(taxa_periodo: float, periodos_por_ano: int) -> float:
    """Taxa anual efetiva equivalente a uma taxa por período (capitalizada)."""
    return (1.0 + float(taxa_periodo)) ** periodos_por_ano - 1.0


def taxa_periodica_efetiva(taxa_anual: float, periodos_por_ano: int) -> float:
    """Taxa efetiva por período equivalente a uma taxa anual efetiva."""
    return (1.0 + float(taxa_anual)) ** (1.0 / periodos_por_ano) - 1.0


def valor_futuro_aporte_unico(principal: float, taxa_anual: float, prazo_meses: int) -> float:
    """Valor futuro de um aporte único capitalizado ao longo de prazo_meses."""
    return float(principal) * (1.0 + float(taxa_anual)) ** (float(prazo_meses) / 12.0)


def fator_serie_postecipada(taxa_mensal: float, n_meses: int) -> float:
    """Fator de acumulação de uma série uniforme postecipada de n aportes.

    Soma (1+i)^t para t = 0 .. n-1. O último aporte não rende juros.
    """
    if abs(float(taxa_mensal)) < 1e-14:
        return float(n_meses)
    return ((1.0 + taxa_mensal) ** n_meses - 1.0) / taxa_mensal


def valor_futuro_serie_postecipada(pmt: float, taxa_mensal: float, n_meses: int) -> float:
    """Valor futuro de aportes mensais iguais (postecipados) ao longo de n meses."""
    return float(pmt) * fator_serie_postecipada(taxa_mensal, n_meses)


def fator_serie_descontada(taxa_mensal: float, n_meses: int) -> float:
    """Soma de (1+i)^(-t) para t = 1 .. n (fator de desconto em série)."""
    if abs(float(taxa_mensal)) < 1e-14:
        return float(n_meses)
    q = 1.0 / (1.0 + taxa_mensal)
    return q * (1.0 - q ** n_meses) / (1.0 - q)


def tir_fluxo_caixa(
    fluxos,
    minimo: float = -0.9999,
    maximo: float = 10.0,
    pontos: int = 6000,
) -> Optional[float]:
    """Taxa interna de retorno (por período) de uma série de fluxos de caixa.

    Retorna a taxa por período que zera o VPL. Prefere a raiz positiva
    (o retorno econômico do investimento); quando não há raiz positiva,
    retorna a raiz negativa mais próxima de zero, se existir.
    Retorna None quando não há raiz no intervalo.
    """
    import numpy as np

    fluxos = np.asarray(fluxos, dtype=float)
    if fluxos.size < 2:
        return None

    def vpl(r):
        t = np.arange(fluxos.size)
        return float(np.sum(fluxos / (1.0 + r) ** t))

    from scipy.optimize import brentq

    def _achar(inf_r, sup_r):
        xs = np.linspace(inf_r, sup_r, pontos)
        ys = np.array([vpl(x) for x in xs])
        for i in range(1, len(xs)):
            if ys[i - 1] == 0.0:
                return float(xs[i - 1])
            if ys[i - 1] * ys[i] < 0.0:
                try:
                    raiz = brentq(vpl, xs[i - 1], xs[i], xtol=1e-12, rtol=1e-12)
                except Exception:
                    return None
                if np.isfinite(raiz):
                    return float(raiz)
        return None

    raiz_positiva = _achar(0.0, maximo)
    if raiz_positiva is not None:
        return raiz_positiva
    return _achar(max(minimo, -1.0 + 1e-6), 0.0)


def taxa_minima_por_indicadores(taxa_livre_risco: float, inflacao: float) -> float:
    """Taxa mínima de atratividade como taxa real: (1+livre_risco)/(1+inflação) - 1.

    Use a taxa básica livre de risco e a inflação ao consumidor, ex.
    a taxa Selic + IPCA.
    """
    inflacao = float(inflacao)
    if (1.0 + inflacao) <= 0.0:
        raise ValueError("Inflação inválida.")
    return (1.0 + float(taxa_livre_risco)) / (1.0 + inflacao) - 1.0
