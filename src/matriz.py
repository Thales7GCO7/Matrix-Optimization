"""Operações matriciais do otimizador de investimentos.

Este módulo mostra como o problema de alocação de capital pode ser
expresso com álgebra linear: matrizes de fluxos de caixa, produtos
escalares para o VPL, vetorização de taxas etc.
"""

import numpy as np
from typing import List, TYPE_CHECKING
from . import matematica_financeira as mf

if TYPE_CHECKING:
    from . import instrumentos
    from . import desempenho


def extrair_caracteristicas_ativos(ativos: List["instrumentos.Ativo"]) -> np.ndarray:
    """Extrai as características numéricas dos ativos como matriz (n_ativos x n_features).

    Features por ativo:
    0: taxa anual (efetiva)
    1: prazo em meses
    2: alíquota de imposto
    3: percentual de taxa (0 quando modo='nenhuma')
    4: mínimo inicial
    5: máximo inicial (inf quando None)
    6: aceita aportes mensais (0/1)
    7: máximo mensal (inf quando None ou não usado)
    """
    n = len(ativos)
    X = np.zeros((n, 8), dtype=float)
    for i, a in enumerate(ativos):
        X[i, 0] = a.taxa_anual
        X[i, 1] = a.prazo_meses
        X[i, 2] = a.aliquota
        X[i, 3] = a.taxa_pct if a.modo_taxa != "nenhuma" else 0.0
        X[i, 4] = a.minimo_inicial if a.minimo_inicial is not None else 0.0
        X[i, 5] = a.maximo_inicial if a.maximo_inicial is not None else np.inf
        X[i, 6] = 1.0 if a.usa_mensal else 0.0
        X[i, 7] = a.maximo_mensal if a.usa_mensal and a.maximo_mensal is not None else np.inf
    return X


def vetor_retornos_liquidos(ativos: List["instrumentos.Ativo"]) -> np.ndarray:
    """Taxas líquidas anualizadas de todos os ativos, calculadas de forma vetorizada.

    Retorna um vetor r_liq onde r_liq[i] = retorno_liquido_anualizado(ativos[i]).
    """
    from . import instrumentos
    n = len(ativos)
    r_liq = np.zeros(n)
    for i, a in enumerate(ativos):
        resumo = instrumentos.resumo_ativo(a, 1.0, 0.0)
        liquido = resumo["valor_liquido"]
        if liquido <= 0.0:
            r_liq[i] = -np.inf
        else:
            r_liq[i] = liquido ** (12.0 / a.prazo_meses) - 1.0
    return r_liq


def montar_matriz_fluxos(
    metricas: List["desempenho.MetricasAtivo"],
    horizonte: int
) -> np.ndarray:
    """Monta a matriz de fluxos de caixa mensais (n_ativos x H).

    Cada linha i contém um ativo. A coluna t (indexada em 1) contém o
    aporte mensal daquele ativo no mês t, ou 0 quando t excede o prazo
    do ativo. A coluna 0 é sempre 0 (aportes iniciais tratados à parte).
    """
    n = len(metricas)
    P = np.zeros((n, horizonte + 1), dtype=float)
    for i, met in enumerate(metricas):
        prazo = len(met.projecao) - 1
        mensal = met.aporte_mensal
        if mensal > 0 and prazo > 0:
            fim = min(prazo, horizonte)
            P[i, 1:fim + 1] = mensal
    return P


def vpl_carteira(
    saidas: np.ndarray,
    liquido_h: float,
    total_inicial: float,
    taxa_minima_anual: float,
    horizonte: int
) -> float:
    """VPL da carteira calculado com produto escalar.

    VPL = -A0 + soma_{t=1..H} (-aportes[t]) / (1+i)^t + LÍQ_H / (1+i)^H
    """
    taxa_m = mf.taxa_mensal_equivalente(taxa_minima_anual)
    desconto = (1.0 + taxa_m) ** (-np.arange(horizonte + 1))
    vpl = -total_inicial
    vpl += float(np.dot(-saidas[1:], desconto[1:]))
    vpl += liquido_h * desconto[horizonte]
    return vpl


def projecao_matricial(
    ativos: List["instrumentos.Ativo"],
    aportes_iniciais: np.ndarray,
    aportes_mensais: np.ndarray
) -> np.ndarray:
    """Projeção mensal de valor líquido de todos os ativos.

    Retorna uma matriz M (n_ativos x H_max+1) onde M[i, t] é o valor
    líquido do ativo i no mês t. As linhas são preenchidas com zero após
    o prazo do ativo.
    """
    from . import instrumentos
    n = len(ativos)
    prazos = np.array([a.prazo_meses for a in ativos])
    H_max = int(prazos.max()) if n > 0 else 0
    M = np.zeros((n, H_max + 1), dtype=float)

    for i, a in enumerate(ativos):
        a_ini = aportes_iniciais[i]
        p_men = aportes_mensais[i]
        m = a.prazo_meses
        taxa_a = a.taxa_anual
        taxa_m = a.taxa_mensal

        resumo = instrumentos.resumo_ativo(a, a_ini, p_men)
        total_ded = resumo["imposto"] + resumo["taxa"]

        for t in range(0, m + 1):
            if t == 0:
                f = a_ini
            else:
                f = a_ini * (1.0 + taxa_a) ** (t / 12.0)
                f += p_men * mf.fator_serie_postecipada(taxa_m, t)
            fracao = t / m if m else 1.0
            liquido = max(f - total_ded * fracao, 0.0)
            M[i, t] = liquido

    return M


def alocacao_vetorizada(
    capital: float,
    taxas_liquidas: np.ndarray,
    minimos: np.ndarray,
    maximos: np.ndarray
) -> np.ndarray:
    """Alocação gulosa vetorizada por taxa líquida decrescente.

    Args:
        capital: Capital total disponível.
        taxas_liquidas: Vetor de taxas líquidas (maior = melhor).
        minimos: Vetor de mínimos por ativo.
        maximos: Vetor de máximos por ativo (inf = sem teto).

    Returns:
        Vetor de alocação por ativo (mesma ordem de entrada).
    """
    n = len(taxas_liquidas)
    ordem = np.argsort(-taxas_liquidas)

    min_ord = minimos[ordem]
    max_ord = maximos[ordem]

    aloc_ord = min_ord.copy()
    restante = capital - min_ord.sum()

    capacidades = max_ord - min_ord
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


def vetor_aporte_unico(
    principais: np.ndarray,
    taxas_anuais: np.ndarray,
    prazos_meses: np.ndarray
) -> np.ndarray:
    """Valor futuro de aporte único para vários ativos (vetorizado).

    M[i] = principais[i] * (1 + taxas_anuais[i])^(prazos_meses[i] / 12)
    """
    return principais * (1.0 + taxas_anuais) ** (prazos_meses / 12.0)


def vetor_serie_postecipada(
    pmts: np.ndarray,
    taxas_mensais: np.ndarray,
    n_meses: np.ndarray
) -> np.ndarray:
    """Valor futuro de série postecipada para vários ativos (vetorizado)."""
    resultado = np.zeros_like(pmts)
    mascara = np.abs(taxas_mensais) >= 1e-14
    # Caso de taxa próxima de zero
    resultado[~mascara] = pmts[~mascara] * n_meses[~mascara]
    # Caso geral
    tm = taxas_mensais[mascara]
    nm = n_meses[mascara]
    resultado[mascara] = pmts[mascara] * ((1.0 + tm) ** nm - 1.0) / tm
    return resultado


def vetor_fator_serie_descontada(
    taxas_mensais: np.ndarray,
    n_meses: np.ndarray
) -> np.ndarray:
    """Fator de desconto em série para várias taxas/prazos."""
    resultado = np.zeros_like(taxas_mensais)
    mascara = np.abs(taxas_mensais) >= 1e-14
    resultado[~mascara] = n_meses[~mascara].astype(float)
    tm = taxas_mensais[mascara]
    nm = n_meses[mascara]
    q = 1.0 / (1.0 + tm)
    resultado[mascara] = q * (1.0 - q ** nm) / (1.0 - q)
    return resultado
