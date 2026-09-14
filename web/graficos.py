"""Graficos da otimizacao de investimento (matplotlib) como PNG base64."""

import base64
import io
from typing import List, Optional

import numpy as np

import matplotlib

matplotlib.use("Agg", force=True)
import matplotlib.pyplot as plt

from src.performance import IndicadoresAtivo, serie_patrimonio


def _png(fig) -> str:
    """Serializa uma figura matplotlib como data URI PNG base64."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=110, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return "data:image/png;base64," + base64.b64encode(buf.read()).decode("ascii")


def grafico_alocacao(resultado) -> Optional[str]:
    """Barras empilhadas: aporte inicial + total de aportes mensais por ativo."""
    if not resultado.alocacoes:
        return None

    nomes = [a.ativo.nome for a in resultado.alocacoes]
    inicial = np.array([a.aporte_inicial for a in resultado.alocacoes])
    mensal_total = np.array([a.aporte_mensal * a.ativo.prazo_meses for a in resultado.alocacoes])

    idx = np.arange(len(nomes))
    fig, ax = plt.subplots(figsize=(10, max(3.5, 0.55 * len(nomes))))

    ax.barh(idx, inicial, height=0.6, color="steelblue", edgecolor="black", label="Aporte inicial")
    ax.barh(
        idx, mensal_total, height=0.6, left=inicial, color="mediumseagreen",
        edgecolor="black", label="Total aportes mensais",
    )
    for i in range(len(nomes)):
        tot = inicial[i] + mensal_total[i]
        if tot > 0:
            ax.text(tot, i, f"  {tot:,.0f}", va="center", fontsize=8)

    ax.set_yticks(idx)
    ax.set_yticklabels(nomes, fontsize=8)
    ax.invert_yaxis()
    ax.set_xlabel("Valor (R$)")
    ax.set_title("Alocacao otima de capital")
    ax.grid(axis="x", alpha=0.3)
    ax.legend(loc="lower right", fontsize=8)
    fig.tight_layout()
    return _png(fig)


def grafico_evolucao_patrimonio(resultado) -> Optional[str]:
    """Evolucao do patrimonio liquido total vs. o mesmo fluxo na TMA."""
    if not resultado.indicadores:
        return None
    serie = serie_patrimonio(resultado.indicadores, resultado.tma_anual)
    if not serie:
        return None

    meses = [p["mes"] for p in serie]
    pat = [p["patrimonio"] for p in serie]
    tma = [p["tma"] for p in serie]

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(meses, pat, "o-", color="steelblue", linewidth=2, label="Patrimonio liquido (carteira)")
    ax.plot(
        meses, tma, "--", color="crimson", linewidth=1.8, alpha=0.85,
        label="Mesmo fluxo na TMA (custo de oportunidade)",
    )
    ax.fill_between(meses, tma, pat, where=[p >= t for p, t in zip(pat, tma)], color="green",
                    alpha=0.12, interpolate=True)
    ax.set_xlabel("Mes")
    ax.set_ylabel("Patrimonio (R$)")
    ax.set_title("Projecao do patrimonio ate o resgate")
    ax.grid(alpha=0.3)
    ax.legend(loc="upper left", fontsize=9)
    fig.tight_layout()
    return _png(fig)


def grafico_lucro_versus_tma(resultado) -> Optional[str]:
    """Lucro liquido por ativo vs. o que o mesmo fluxo renderia na TMA."""
    if not resultado.indicadores:
        return None
    inds: List[IndicadoresAtivo] = resultado.indicadores
    nomes = [i.nome for i in inds]
    idx = np.arange(len(nomes))

    lucros = np.array([i.lucro_liquido for i in inds])
    na_tma = np.array([i.lucro_tma for i in inds])
    largura = 0.35

    fig, ax = plt.subplots(figsize=(10, max(3.5, 0.55 * len(nomes))))
    ax.barh(idx - largura / 2, lucros, height=largura, color="steelblue",
            edgecolor="black", label="Lucro liquido")
    ax.barh(idx + largura / 2, na_tma, height=largura, color="crimson", alpha=0.75,
            edgecolor="black", label="Lucro na TMA")
    ax.axvline(0, color="black", linewidth=0.8)
    ax.set_yticks(idx)
    ax.set_yticklabels(nomes, fontsize=8)
    ax.invert_yaxis()
    ax.set_xlabel("Lucro (R$)")
    ax.set_title("Lucro liquido por ativo e custo de oportunidade (TMA)")
    ax.grid(axis="x", alpha=0.3)
    ax.legend(loc="best", fontsize=8)
    fig.tight_layout()
    return _png(fig)