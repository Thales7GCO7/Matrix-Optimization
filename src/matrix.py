"""Operacoes matriciais para o otimizador de investimentos.

Este modulo demonstra como o problema de alocacao de capital pode ser
expresso com algebra linear: matrizes de fluxos, produto escalar para VPL,
vetorizacao de taxas, etc.
"""

import numpy as np
from typing import List, Tuple, Optional, TYPE_CHECKING
from . import math_finance as mf

if TYPE_CHECKING:
    from . import instruments
    from . import performance


def extrair_atributos_ativos(ativos: List["instruments.Ativo"]) -> np.ndarray:
    """Extrai atributos numericos dos ativos como matriz (n_ativos x n_features).

    Features por ativo:
    0: taxa_anual (efetiva)
    1: prazo_meses
    2: aliquota_imposto
    3: admin_percentual (0 se modo='nenhuma')
    4: aporte_inicial_min
    5: aporte_inicial_max (inf se None)
    6: usa_aporte_mensal (0/1)
    7: aporte_mensal_max (inf se None ou nao usa)
    """
    n = len(ativos)
    X = np.zeros((n, 8), dtype=float)
    for i, a in enumerate(ativos):
        X[i, 0] = a.taxa_anual
        X[i, 1] = a.prazo_meses
        X[i, 2] = a.aliquota_imposto
        X[i, 3] = a.admin_percentual if a.admin_modo != "nenhuma" else 0.0
        X[i, 4] = a.aporte_inicial_min if a.aporte_inicial_min is not None else 0.0
        X[i, 5] = a.aporte_inicial_max if a.aporte_inicial_max is not None else np.inf
        X[i, 6] = 1.0 if a.usa_aporte_mensal else 0.0
        X[i, 7] = a.aporte_mensal_max if a.usa_aporte_mensal and a.aporte_mensal_max is not None else np.inf
    return X


def taxas_liquidas_vetor(ativos: List["instruments.Ativo"]) -> np.ndarray:
    """Calcula taxas liquidas anualizadas de todos os ativos de forma vetorizada.

    Retorna vetor r_liq onde r_liq[i] = taxa_liquida_anualizada(ativos[i]).
    """
    from . import instruments
    n = len(ativos)
    r_liq = np.zeros(n)
    for i, a in enumerate(ativos):
        resumo = instruments.resumo_ativo(a, 1.0, 0.0)
        ml = resumo["montante_liquido"]
        if ml <= 0.0:
            r_liq[i] = -np.inf
        else:
            r_liq[i] = ml ** (12.0 / a.prazo_meses) - 1.0
    return r_liq


def construir_matriz_fluxos(
    indicadores: List["performance.IndicadoresAtivo"],
    horizonte: int
) -> np.ndarray:
    """Constrói matriz de fluxos de caixa mensais (n_ativos x H).

    Cada linha i corresponde a um ativo. A coluna t (1-indexed) contem o
    aporte mensal desse ativo no mes t, ou 0 se t > prazo do ativo.
    A coluna 0 eh sempre 0 (aporte inicial tratado separadamente).
    """
    n = len(indicadores)
    P = np.zeros((n, horizonte + 1), dtype=float)
    for i, ind in enumerate(indicadores):
        prazo = len(ind.projecao) - 1
        p_mensal = ind.aporte_mensal
        if p_mensal > 0 and prazo > 0:
            fim = min(prazo, horizonte)
            P[i, 1:fim + 1] = p_mensal
    return P


def vpl_carteira(
    outflows: np.ndarray,
    montante_liquido_h: float,
    aporte_inicial_total: float,
    tma_anual: float,
    horizonte: int
) -> float:
    """Calcula VPL da carteira usando produto escalar (dot product).

    VPL = -A0 + sum_{t=1..H} (-outflows[t]) / (1+i)^t + ML_H / (1+i)^H
    """
    i_mensal = mf.taxa_mensal_equivalente(tma_anual)
    desc = (1.0 + i_mensal) ** (-np.arange(horizonte + 1))
    vpl = -aporte_inicial_total
    vpl += float(np.dot(-outflows[1:], desc[1:]))
    vpl += montante_liquido_h * desc[horizonte]
    return vpl


def projecao_matricial(
    ativos: List["instruments.Ativo"],
    aportes_iniciais: np.ndarray,
    aportes_mensais: np.ndarray
) -> np.ndarray:
    """Calcula projecao mensal de montantes liquidos para todos os ativos.

    Retorna matriz M (n_ativos x H_max+1) onde M[i, t] = montante liquido
    do ativo i no mes t. Linhas sao preenchidas com zeros apos o prazo do ativo.
    """
    from . import instruments
    n = len(ativos)
    prazos = np.array([a.prazo_meses for a in ativos])
    H_max = int(prazos.max()) if n > 0 else 0
    M = np.zeros((n, H_max + 1), dtype=float)

    for i, a in enumerate(ativos):
        a_ini = aportes_iniciais[i]
        p_men = aportes_mensais[i]
        m = a.prazo_meses
        r_ano = a.taxa_anual
        i_m = a.taxa_mensal

        resumo = instruments.resumo_ativo(a, a_ini, p_men)
        ded_total = resumo["imposto"] + resumo["admin"]

        for t in range(0, m + 1):
            if t == 0:
                f = a_ini
            else:
                f = a_ini * (1.0 + r_ano) ** (t / 12.0)
                f += p_men * mf.fator_serie_postecipada(i_m, t)
            fracao = t / m if m else 1.0
            ml = max(f - ded_total * fracao, 0.0)
            M[i, t] = ml

    return M


def alocar_vetorizada(
    capital: float,
    taxas_liq: np.ndarray,
    mins: np.ndarray,
    maxs: np.ndarray
) -> np.ndarray:
    """Alocacao gulosa vetorizada por taxa liquida decrescente.

    Args:
        capital: Capital total disponivel
        taxas_liq: Vetor de taxas liquidas (maior = melhor)
        mins: Vetor de minimos por ativo
        maxs: Vetor de maximos por ativo (inf = sem limite)

    Returns:
        Vetor de alocacao por ativo (mesma ordem de entrada).
    """
    n = len(taxas_liq)
    ordem = np.argsort(-taxas_liq)

    mins_ord = mins[ordem]
    maxs_ord = maxs[ordem]

    aloc_ord = mins_ord.copy()
    restante = capital - mins_ord.sum()

    capacidades = maxs_ord - mins_ord
    for i in range(n):
        if restante <= 1e-9:
            break
        cap = capacidades[i]
        if cap <= 0:
            continue
        extra = min(cap, restante)
        aloc_ord[i] += extra
        restante -= extra

    aloc = np.zeros(n)
    aloc[ordem] = aloc_ord
    return aloc


def montante_aporte_unico_vetor(
    valores: np.ndarray,
    taxas_anuais: np.ndarray,
    prazos_meses: np.ndarray
) -> np.ndarray:
    """Montante de aporte unico para multiplos ativos (vetorizado).

    M[i] = valores[i] * (1 + taxas_anuais[i])^(prazos_meses[i] / 12)
    """
    return valores * (1.0 + taxas_anuais) ** (prazos_meses / 12.0)


def montante_serie_postecipada_vetor(
    pmts: np.ndarray,
    taxas_mensais: np.ndarray,
    n_meses: np.ndarray
) -> np.ndarray:
    """Montante de serie postecipada para multiplos ativos (vetorizado)."""
    resultado = np.zeros_like(pmts)
    mask = np.abs(taxas_mensais) >= 1e-14
    # Caso taxa ~ 0
    resultado[~mask] = pmts[~mask] * n_meses[~mask]
    # Caso geral
    tm = taxas_mensais[mask]
    nm = n_meses[mask]
    resultado[mask] = pmts[mask] * ((1.0 + tm) ** nm - 1.0) / tm
    return resultado


def fator_serie_descontada_vetor(
    taxas_mensais: np.ndarray,
    n_meses: np.ndarray
) -> np.ndarray:
    """Fator de desconto de serie para multiplas taxas/prazos."""
    resultado = np.zeros_like(taxas_mensais)
    mask = np.abs(taxas_mensais) >= 1e-14
    resultado[~mask] = n_meses[~mask].astype(float)
    tm = taxas_mensais[mask]
    nm = n_meses[mask]
    q = 1.0 / (1.0 + tm)
    resultado[mask] = q * (1.0 - q ** nm) / (1.0 - q)
    return resultado