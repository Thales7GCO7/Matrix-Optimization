"""Métricas de desempenho dos investimentos (ROI, VPL, TIR, payback, IL, alpha).

As métricas são calculadas por ativo (dados os aportes escolhidos pela
otimização) e agregadas para a carteira. A taxa mínima de atratividade é a
taxa de desconto do VPL e representa o custo de oportunidade do capital;
a inflação permite calcular o retorno real.
"""

from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np

from . import instrumentos
from . import matematica_financeira as mf
from . import matriz


@dataclass
class MetricasAtivo:
    nome: str
    eh_reserva: bool
    aporte_inicial: float
    aporte_mensal: float
    total_aportado: float
    valor_bruto: float
    ganho_bruto: float
    imposto: float
    taxa: float
    aliquota: float
    valor_liquido: float
    lucro_liquido: float
    roi: float
    roi_anualizado: Optional[float]
    retorno_real: Optional[float]
    vpl: float
    tir_mensal: Optional[float]
    tir_anual: Optional[float]
    payback_simples: Optional[float]
    payback_descontado: Optional[float]
    indice_lucratividade: Optional[float]
    alpha: Optional[float]
    lucro_taxa_minima: float
    lucro_excedente: float
    taxa_anual_liquida: float
    projecao: List[dict] = field(default_factory=list)


@dataclass
class MetricasCarteira:
    capital_inicial: float
    total_aportes_mensais: float
    capital_investido: float
    reserva: float
    valor_liquido: float
    lucro_liquido: float
    roi: float
    roi_anualizado: Optional[float]
    vpl: float
    tir_anual: Optional[float]
    alpha: Optional[float]
    lucro_taxa_minima: float
    lucro_excedente: float


def calcular_ativo(
    ativo: instrumentos.Ativo,
    aporte_inicial: float,
    aporte_mensal: float,
    taxa_minima_anual: float,
    inflacao_anual: float,
    eh_reserva: bool = False,
) -> MetricasAtivo:
    """Métricas de desempenho de um único ativo."""
    res = instrumentos.resumo_ativo(ativo, aporte_inicial, aporte_mensal)
    m = ativo.prazo_meses
    a = res["aporte_inicial"]
    p = res["aporte_mensal"]
    liquido = res["valor_liquido"]
    aportado = res["total_aportado"]

    taxa_desconto = mf.taxa_mensal_equivalente(taxa_minima_anual)
    desconto_serie = mf.fator_serie_descontada(taxa_desconto, m)
    vpl = -a - p * desconto_serie + liquido / (1.0 + taxa_desconto) ** m

    # TIR sobre o fluxo de caixa mensal. O aporte do mês m é aplicado e
    # imediatamente resgatado (rendimento zero), logo o fluxo final é LÍQUIDO - p.
    fluxo = [-a] + [-p] * (m - 1) + [liquido - p]
    if a <= 0.0 and p <= 0.0:
        tir_mensal = None
    else:
        tir_mensal = mf.tir_fluxo_caixa(fluxo)
    tir_anual = (1.0 + tir_mensal) ** 12 - 1.0 if tir_mensal is not None else None

    roi = res["lucro_liquido"] / aportado if aportado > 0 else 0.0

    if p > 0.0 and tir_anual is not None:
        roi_anualizado = tir_anual
    elif a > 0.0 and liquido > 0.0:
        roi_anualizado = (liquido / a) ** (12.0 / m) - 1.0
    else:
        roi_anualizado = None

    retorno_real = (
        (1.0 + roi_anualizado) / (1.0 + inflacao_anual) - 1.0
        if roi_anualizado is not None and (1.0 + inflacao_anual) > 0.0
        else None
    )

    vp_aportado = a + p * desconto_serie
    indice_lucratividade = vpl / vp_aportado + 1.0 if vp_aportado > 0.0 else None

    alpha = roi_anualizado - taxa_minima_anual if roi_anualizado is not None else None

    # Custo de oportunidade: o mesmo fluxo de aportes rendendo a taxa mínima.
    liquido_minima = (
        mf.valor_futuro_aporte_unico(a, taxa_minima_anual, m)
        + mf.valor_futuro_serie_postecipada(p, mf.taxa_mensal_equivalente(taxa_minima_anual), m)
    )
    lucro_minima = liquido_minima - aportado
    lucro_excedente = res["lucro_liquido"] - lucro_minima

    projecao = instrumentos.projecao_mensal(ativo, a, p)
    payback_simples = _payback_simples(projecao)
    payback_descontado = _payback_descontado(projecao, taxa_desconto)

    return MetricasAtivo(
        nome=ativo.nome,
        eh_reserva=eh_reserva,
        aporte_inicial=a,
        aporte_mensal=p,
        total_aportado=aportado,
        valor_bruto=res["valor_bruto"],
        ganho_bruto=res["ganho_bruto"],
        imposto=res["imposto"],
        taxa=res["taxa"],
        aliquota=res["aliquota"],
        valor_liquido=liquido,
        lucro_liquido=res["lucro_liquido"],
        roi=roi,
        roi_anualizado=roi_anualizado,
        retorno_real=retorno_real,
        vpl=vpl,
        tir_mensal=tir_mensal,
        tir_anual=tir_anual,
        payback_simples=payback_simples,
        payback_descontado=payback_descontado,
        indice_lucratividade=indice_lucratividade,
        alpha=alpha,
        lucro_taxa_minima=lucro_minima,
        lucro_excedente=lucro_excedente,
        taxa_anual_liquida=instrumentos.retorno_liquido_anualizado(ativo),
        projecao=projecao,
    )


def _payback_simples(projecao: List[dict]) -> Optional[float]:
    """Mês em que o resgate antecipado (valor líquido projetado) supera os aportes."""
    for pt in projecao:
        if pt["mes"] == 0:
            continue
        if pt["valor_liquido"] >= pt["aportado"]:
            return float(pt["mes"])
    return None


def _payback_descontado(projecao: List[dict], taxa_desconto: float) -> Optional[float]:
    """Mês em que o VPL do resgate na data t (fluxo descontado) fica >= 0."""
    if len(projecao) < 2:
        return None
    a = projecao[0]["aportado"]
    p = projecao[1]["aportado"] - a
    for pt in projecao:
        t = pt["mes"]
        if t == 0:
            continue
        desconto_serie = mf.fator_serie_descontada(taxa_desconto, t)
        vpl = -a - p * desconto_serie + pt["valor_liquido"] / (1.0 + taxa_desconto) ** t
        if vpl >= 0.0:
            return float(t)
    return None


def _estender_projecao(projecao: List[dict], horizonte: int, taxa_mensal: float) -> List[dict]:
    """Estende a projeção até o horizonte H capitalizando após o vencimento.

    Após o prazo do ativo, as deduções já foram pagas e o valor volta a
    crescer à taxa mensal do ativo (reinvestimento implícito).
    """
    m = len(projecao) - 1
    if m >= horizonte:
        return projecao[: horizonte + 1]
    saida = list(projecao)
    liquido_final = projecao[-1]["valor_liquido"]
    aportado_final = projecao[-1]["aportado"]
    for t in range(m + 1, horizonte + 1):
        saida.append(
            {
                "mes": t,
                "valor_liquido": liquido_final * (1.0 + taxa_mensal) ** (t - m),
                "aportado": aportado_final,
            }
        )
    return saida


def calcular_carteira(
    metricas: List[MetricasAtivo],
    taxa_minima_anual: float,
) -> MetricasCarteira:
    """Agrega as métricas da carteira, montando o fluxo de caixa mensal efetivo.

    O horizonte H da carteira é o maior prazo entre os ativos. Os aportes
    mensais correm até o prazo de cada ativo (postecipados); a riqueza de
    cada ativo é projetada (com reinvestimento implícito) até H. A TIR e o
    VPL da carteira são calculados sobre esse fluxo agregado.
    """
    if not metricas:
        # Carteira vazia.
        return MetricasCarteira(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, None, 0.0, None, None, 0.0, 0.0)

    H = max(len(i.projecao) - 1 for i in metricas) or 1
    minima_mensal = mf.taxa_mensal_equivalente(taxa_minima_anual)

    total_inicial = sum(i.aporte_inicial for i in metricas)
    estendida = [
        _estender_projecao(i.projecao, H, _taxa_mensal_por_metricas(i)) for i in metricas
    ]

    liquido_h = sum(pj[H]["valor_liquido"] for pj in estendida)

    # Matriz de fluxos de caixa (n_ativos x H+1)
    P = matriz.montar_matriz_fluxos(metricas, H)
    saidas = P.sum(axis=0)  # vetor 1D: somado sobre os ativos

    total_aportado = total_inicial + float(saidas[1:].sum())

    # Fluxo agregado para a TIR
    fluxo = [-total_inicial]
    for t in range(1, H):
        fluxo.append(-saidas[t])
    fluxo.append(liquido_h - saidas[H])

    # VPL via produto escalar
    vpl = matriz.vpl_carteira(saidas, liquido_h, total_inicial, taxa_minima_anual, H)

    if total_inicial > 0.0 or any(o > 0 for o in saidas):
        tir_mensal = mf.tir_fluxo_caixa(fluxo)
    else:
        tir_mensal = None
    tir_anual = (1.0 + tir_mensal) ** 12 - 1.0 if tir_mensal is not None else None

    lucro = liquido_h - total_aportado
    reserva = sum(i.total_aportado for i in metricas if i.eh_reserva)

    # Referência: o mesmo fluxo de aportes rendendo a taxa mínima até H.
    saldo = total_inicial
    for t in range(1, H + 1):
        saldo = saldo * (1.0 + minima_mensal) + saidas[t]
    liquido_minima = saldo
    lucro_minima = liquido_minima - total_aportado
    lucro_excedente = lucro - lucro_minima
    alpha = tir_anual - taxa_minima_anual if tir_anual is not None else None

    return MetricasCarteira(
        capital_inicial=total_inicial,
        total_aportes_mensais=float(saidas[1:].sum()),
        capital_investido=total_aportado,
        reserva=reserva,
        valor_liquido=liquido_h,
        lucro_liquido=lucro,
        roi=lucro / total_aportado if total_aportado > 0 else 0.0,
        roi_anualizado=tir_anual,
        vpl=vpl,
        tir_anual=tir_anual,
        alpha=alpha,
        lucro_taxa_minima=lucro_minima,
        lucro_excedente=lucro_excedente,
    )


def _taxa_mensal_por_metricas(met: MetricasAtivo) -> float:
    """Taxa mensal equivalente ao retorno líquido anualizado do ativo.

    Usada só no reinvestimento implícito ao estender a projeção.
    """
    if met.roi_anualizado is not None and met.roi_anualizado > -1.0:
        return mf.taxa_mensal_equivalente(met.roi_anualizado)
    return 0.0


def serie_patrimonio(
    metricas: List[MetricasAtivo], taxa_minima_anual: float
) -> List[dict]:
    """Riqueza líquida total mês a mês mais a referência na taxa mínima.

    Mesmo horizonte de aportes da carteira: cada ativo recebe aportes
    até seu próprio prazo e o restante investido segue rendendo após
    o vencimento.
    """
    if not metricas:
        return []
    H = max(len(i.projecao) - 1 for i in metricas) or 1
    minima_mensal = mf.taxa_mensal_equivalente(taxa_minima_anual)

    estendida = [_estender_projecao(i.projecao, H, _taxa_mensal_por_metricas(i)) for i in metricas]

    total_inicial = sum(i.aporte_inicial for i in metricas)
    P = matriz.montar_matriz_fluxos(metricas, H)
    saidas = P.sum(axis=0)

    saldo_minima = total_inicial
    pontos = []
    for t in range(0, H + 1):
        if t > 0:
            saldo_minima = saldo_minima * (1.0 + minima_mensal) + saidas[t]
        patrimonio_total = sum(pj[t]["valor_liquido"] for pj in estendida)
        pontos.append({"mes": t, "patrimonio": patrimonio_total, "taxa_minima": saldo_minima})
    return pontos
