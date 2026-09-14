"""Indices de desempenho de investimentos (ROI, VPL, TIR, payback, IL, alfa).

Os indices sao calculados por ativo (dados os aportes decididos pela
otimizacao) e agregados para a carteira. A TMA (taxa minima de
atratividade) e a taxa de desconto do VPL e representa o custo de
oportunidade do capital; a inflacao permite calcular o retorno real.
"""

from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np

from . import instruments
from . import math_finance as mf
from . import matrix


@dataclass
class IndicadoresAtivo:
    nome: str
    reserva: bool
    aporte_inicial: float
    aporte_mensal: float
    aportado_total: float
    montante_bruto: float
    rendimento_bruto: float
    imposto: float
    admin: float
    aliquota_imposto: float
    montante_liquido: float
    lucro_liquido: float
    roi: float
    roi_anualizado: Optional[float]
    retorno_real: Optional[float]
    vpl: float
    tir_mensal: Optional[float]
    tir_anual: Optional[float]
    payback_simples: Optional[float]
    payback_descontado: Optional[float]
    il: Optional[float]
    alfa: Optional[float]
    lucro_tma: float
    ganho_adicional: float
    taxa_anual_liq: float
    projecao: List[dict] = field(default_factory=list)


@dataclass
class IndicadoresCarteira:
    capital_inicial: float
    aporte_mensal_total: float
    capital_aplicado: float
    reserva: float
    montante_liquido: float
    lucro_liquido: float
    roi: float
    roi_anualizado: Optional[float]
    vpl: float
    tir_anual: Optional[float]
    alfa: Optional[float]
    lucro_tma: float
    ganho_adicional: float


def calcular_ativo(
    ativo: instruments.Ativo,
    aporte_inicial: float,
    aporte_mensal: float,
    tma_anual: float,
    inflacao_anual: float,
    reserva: bool = False,
) -> IndicadoresAtivo:
    """Indices de desempenho de um unico ativo."""
    res = instruments.resumo_ativo(ativo, aporte_inicial, aporte_mensal)
    m = ativo.prazo_meses
    a = res["aporte_inicial"]
    p = res["aporte_mensal"]
    ml = res["montante_liquido"]
    aplicado = res["aportado_total"]

    taxa_disc = mf.taxa_mensal_equivalente(tma_anual)
    desc_serie = mf.fator_serie_descontada(taxa_disc, m)
    vpl = -a - p * desc_serie + ml / (1.0 + taxa_disc) ** m

    # TIR pelo fluxo mensal. O aporte do mes m e depositado e pronto
    # resgatado (rendimento zero), por isso o fluxo final e ML - p.
    fluxo = [-a] + [-p] * (m - 1) + [ml - p]
    if a <= 0.0 and p <= 0.0:
        tir_mensal = None
    else:
        tir_mensal = mf.tir_de_fluxo(fluxo)
    tir_anual = (1.0 + tir_mensal) ** 12 - 1.0 if tir_mensal is not None else None

    roi = res["lucro_liquido"] / aplicado if aplicado > 0 else 0.0

    if p > 0.0 and tir_anual is not None:
        roi_anualizado = tir_anual
    elif a > 0.0 and ml > 0.0:
        roi_anualizado = (ml / a) ** (12.0 / m) - 1.0
    else:
        roi_anualizado = None

    retorno_real = (
        (1.0 + roi_anualizado) / (1.0 + inflacao_anual) - 1.0
        if roi_anualizado is not None and (1.0 + inflacao_anual) > 0.0
        else None
    )

    pv_aplicado = a + p * desc_serie
    il = vpl / pv_aplicado + 1.0 if pv_aplicado > 0.0 else None

    alfa = roi_anualizado - tma_anual if roi_anualizado is not None else None

    # Custo de oportunidade: o mesmo fluxo de aportes rendendo na TMA.
    ml_tma = (
        mf.montante_aporte_unico(a, tma_anual, m)
        + mf.montante_serie_postecipada(p, mf.taxa_mensal_equivalente(tma_anual), m)
    )
    lucro_tma = ml_tma - aplicado
    ganho_adicional = res["lucro_liquido"] - lucro_tma

    projecao = instruments.projecao_mensal(ativo, a, p)
    payback_simples = _payback_simples(projecao)
    payback_descontado = _payback_descontado(projecao, taxa_disc)

    return IndicadoresAtivo(
        nome=ativo.nome,
        reserva=reserva,
        aporte_inicial=a,
        aporte_mensal=p,
        aportado_total=aplicado,
        montante_bruto=res["montante_bruto"],
        rendimento_bruto=res["rendimento_bruto"],
        imposto=res["imposto"],
        admin=res["admin"],
        aliquota_imposto=res["aliquota_imposto"],
        montante_liquido=ml,
        lucro_liquido=res["lucro_liquido"],
        roi=roi,
        roi_anualizado=roi_anualizado,
        retorno_real=retorno_real,
        vpl=vpl,
        tir_mensal=tir_mensal,
        tir_anual=tir_anual,
        payback_simples=payback_simples,
        payback_descontado=payback_descontado,
        il=il,
        alfa=alfa,
        lucro_tma=lucro_tma,
        ganho_adicional=ganho_adicional,
        taxa_anual_liq=instruments.taxa_liquida_anualizada(ativo),
        projecao=projecao,
    )


def _payback_simples(projecao: List[dict]) -> Optional[float]:
    """Mes em que o resgate antecipado (montante liquido projetado) supera o aportado."""
    for pt in projecao:
        if pt["mes"] == 0:
            continue
        if pt["montante_liquido"] >= pt["aportado"]:
            return float(pt["mes"])
    return None


def _payback_descontado(projecao: List[dict], taxa_desconto: float) -> Optional[float]:
    """Mes em que o VPL do resgate na data t (fluxo descontado) fica >= 0."""
    if len(projecao) < 2:
        return None
    a = projecao[0]["aportado"]
    p = projecao[1]["aportado"] - a
    for pt in projecao:
        t = pt["mes"]
        if t == 0:
            continue
        desc_serie = mf.fator_serie_descontada(taxa_desconto, t)
        vpl = -a - p * desc_serie + pt["montante_liquido"] / (1.0 + taxa_desconto) ** t
        if vpl >= 0.0:
            return float(t)
    return None


def _projecao_ate(projecao: List[dict], horizonte: int, taxa_mensal: float) -> List[dict]:
    """Estende a projecao ate o horizonte H compostando apos o vencimento.

    Apos o prazo do ativo as deducoes ja foram pagas e o montante volta a
    crescer a taxa mensal do ativo (reinvestimento implicito).
    """
    m = len(projecao) - 1
    if m >= horizonte:
        return projecao[: horizonte + 1]
    out = list(projecao)
    ml_final = projecao[-1]["montante_liquido"]
    aportado_final = projecao[-1]["aportado"]
    for t in range(m + 1, horizonte + 1):
        out.append(
            {
                "mes": t,
                "montante_liquido": ml_final * (1.0 + taxa_mensal) ** (t - m),
                "aportado": aportado_final,
            }
        )
    return out


def calcular_carteira(
    indicadores: List[IndicadoresAtivo],
    tma_anual: float,
) -> IndicadoresCarteira:
    """Indices agregados da carteira, montando o fluxo mensal real.

    O horizonte da carteira H e o maior prazo entre os ativos. Aportes
    mensais ocorrem ate o prazo de cada ativo (postecipados); o patrimonio
    de um ativo e projetado (com reinvestimento implicito) ate H. A TIR e o
    VPL da carteira sao calculados sobre esse fluxo agregado.
    """
    if not indicadores:
        # Carteira vazia.
        return IndicadoresCarteira(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, None, 0.0, None, None, 0.0, 0.0)

    H = max(len(i.projecao) - 1 for i in indicadores) or 1
    i_tma = mf.taxa_mensal_equivalente(tma_anual)

    a_tot = sum(i.aporte_inicial for i in indicadores)
    proj_est = [
        _projecao_ate(i.projecao, H, _taxa_mensal_do_indicador(i)) for i in indicadores
    ]

    ml_h = sum(pj[H]["montante_liquido"] for pj in proj_est)
    prazos = [len(i.projecao) - 1 for i in indicadores]
    p_meses = [i.aporte_mensal for i in indicadores]

    # Matriz de fluxos (n_ativos x H+1)
    P = matrix.construir_matriz_fluxos(indicadores, H)
    outflows = P.sum(axis=0)  # vetor 1D: soma ao longo dos ativos

    total_aportado = a_tot + float(outflows[1:].sum())

    # Fluxo agregado para TIR
    fluxo = [-a_tot]
    for t in range(1, H):
        fluxo.append(-outflows[t])
    fluxo.append(ml_h - outflows[H])

    # VPL via produto escalar (dot product)
    vpl = matrix.vpl_carteira(outflows, ml_h, a_tot, tma_anual, H)

    if a_tot > 0.0 or any(o > 0 for o in outflows):
        tir_mensal = mf.tir_de_fluxo(fluxo)
    else:
        tir_mensal = None
    tir_anual = (1.0 + tir_mensal) ** 12 - 1.0 if tir_mensal is not None else None

    lucro = ml_h - total_aportado
    reserva = sum(i.aportado_total for i in indicadores if i.reserva)

    # Benchmark: mesmo fluxo de aportes rendendo na TMA ate H.
    bal = a_tot
    for t in range(1, H + 1):
        bal = bal * (1.0 + i_tma) + outflows[t]
    ml_tma = bal
    lucro_tma = ml_tma - total_aportado
    ganho_adicional = lucro - lucro_tma
    alfa = tir_anual - tma_anual if tir_anual is not None else None

    return IndicadoresCarteira(
        capital_inicial=a_tot,
        aporte_mensal_total=float(outflows[1:].sum()),
        capital_aplicado=total_aportado,
        reserva=reserva,
        montante_liquido=ml_h,
        lucro_liquido=lucro,
        roi=lucro / total_aportado if total_aportado > 0 else 0.0,
        roi_anualizado=tir_anual,
        vpl=vpl,
        tir_anual=tir_anual,
        alfa=alfa,
        lucro_tma=lucro_tma,
        ganho_adicional=ganho_adicional,
    )


def _taxa_mensal_do_indicador(ind: IndicadoresAtivo) -> float:
    """Taxa mensal equivalente ao retorno anualizado liquido do ativo.

    Usada apenas para reinvestimento implicito na extensao da projecao.
    """
    if ind.roi_anualizado is not None and ind.roi_anualizado > -1.0:
        return mf.taxa_mensal_equivalente(ind.roi_anualizado)
    return 0.0


def serie_patrimonio(
    indicadores: List[IndicadoresAtivo], tma_anual: float
) -> List[dict]:
    """Patrimonio liquido total mes a mes e o benchmark rendendo na TMA.

    Mesmo horizonte dos aportes usado na carteira: cada ativo aporta ate o
    proprio prazo e o resto investido rende apos o vencimento.
    """
    if not indicadores:
        return []
    H = max(len(i.projecao) - 1 for i in indicadores) or 1
    i_tma = mf.taxa_mensal_equivalente(tma_anual)

    proj_est = [_projecao_ate(i.projecao, H, _taxa_mensal_do_indicador(i)) for i in indicadores]

    a_tot = sum(i.aporte_inicial for i in indicadores)
    P = matrix.construir_matriz_fluxos(indicadores, H)
    outflows = P.sum(axis=0)

    bal_tma = a_tot
    pts = []
    for t in range(0, H + 1):
        if t > 0:
            bal_tma = bal_tma * (1.0 + i_tma) + outflows[t]
        pat_tot = sum(pj[t]["montante_liquido"] for pj in proj_est)
        pts.append({"mes": t, "patrimonio": pat_tot, "tma": bal_tma})
    return pts