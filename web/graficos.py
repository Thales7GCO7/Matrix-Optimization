"""Gráficos da otimização de investimentos (matplotlib) em PNG base64."""

import base64
import io
import textwrap
from typing import List, Optional

import numpy as np

import matplotlib

matplotlib.use("Agg", force=True)
import matplotlib.pyplot as plt

from src.desempenho import MetricasAtivo, serie_patrimonio


def _png(fig) -> str:
    """Serializa uma figura matplotlib como data URI PNG em base64."""
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
    # Quebra nomes longos em várias linhas para os rótulos do eixo y
    # caberem sempre na figura em vez de transbordar a borda.
    quebrados = [textwrap.fill(n, width=28) for n in nomes]
    iniciais = np.array([a.aporte_inicial for a in resultado.alocacoes])
    total_mensal = np.array([a.aporte_mensal * a.ativo.prazo_meses for a in resultado.alocacoes])

    idx = np.arange(len(nomes))
    fig, ax = plt.subplots(figsize=(12, max(5.0, 1.1 * len(nomes))))

    ax.barh(idx, iniciais, height=0.6, color="steelblue", edgecolor="black", label="Aporte inicial")
    ax.barh(
        idx, total_mensal, height=0.6, left=iniciais, color="mediumseagreen",
        edgecolor="black", label="Total de aportes mensais",
    )
    for i in range(len(nomes)):
        tot = iniciais[i] + total_mensal[i]
        if tot > 0:
            ax.text(tot, i, f"  {tot:,.0f}", va="center", fontsize=9)

    ax.set_yticks(idx)
    ax.set_yticklabels(quebrados, fontsize=9)
    ax.invert_yaxis()
    ax.set_xlabel("Valor (R$)")
    ax.set_title("Alocação ótima de capital")
    ax.grid(axis="x", alpha=0.3)
    ax.legend(loc="lower right", fontsize=9)
    fig.tight_layout()
    return _png(fig)


def grafico_pizza_alocacao(resultado) -> Optional[str]:
    """Gráfico de pizza: participação de cada ativo no capital total investido."""
    if not resultado.alocacoes:
        return None

    nomes = [a.ativo.nome for a in resultado.alocacoes]
    totais = np.array([
        a.aporte_inicial + a.aporte_mensal * a.ativo.prazo_meses
        for a in resultado.alocacoes
    ])
    if totais.sum() <= 0:
        return None

    fig, ax = plt.subplots(figsize=(7, 5))
    ax.pie(
        totais,
        labels=nomes,
        autopct=lambda v: f"{v:.1f}%" if v >= 3.0 else "",
        startangle=90,
        textprops={"fontsize": 9},
    )
    ax.set_title("Alocação de capital por ativo")
    fig.tight_layout()
    return _png(fig)


def grafico_evolucao_patrimonio(resultado) -> Optional[str]:
    """Crescimento da riqueza líquida total vs. o mesmo fluxo na taxa mínima."""
    if not resultado.metricas:
        return None
    pontos = serie_patrimonio(resultado.metricas, resultado.taxa_minima_anual)
    if not pontos:
        return None

    meses = [p["mes"] for p in pontos]
    patrimonio = [p["patrimonio"] for p in pontos]
    minima = [p["taxa_minima"] for p in pontos]

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(meses, patrimonio, "o-", color="steelblue", linewidth=2, label="Riqueza líquida (carteira)")
    ax.plot(
        meses, minima, "--", color="crimson", linewidth=1.8, alpha=0.85,
        label="Mesmo fluxo na taxa mínima (custo de oportunidade)",
    )
    ax.fill_between(meses, minima, patrimonio, where=[p >= t for p, t in zip(patrimonio, minima)], color="green",
                    alpha=0.12, interpolate=True)
    ax.set_xlabel("Mês")
    ax.set_ylabel("Riqueza (R$)")
    ax.set_title("Projeção da riqueza até o resgate")
    ax.grid(alpha=0.3)
    ax.legend(loc="upper left", fontsize=9)
    fig.tight_layout()
    return _png(fig)


def grafico_lucro_vs_taxa_minima(resultado) -> Optional[str]:
    """Lucro líquido por ativo vs. o que o mesmo fluxo renderia na taxa mínima."""
    if not resultado.metricas:
        return None
    mets: List[MetricasAtivo] = resultado.metricas
    nomes = [i.nome for i in mets]
    idx = np.arange(len(nomes))

    lucros = np.array([i.lucro_liquido for i in mets])
    na_minima = np.array([i.lucro_taxa_minima for i in mets])
    largura = 0.35

    fig, ax = plt.subplots(figsize=(10, max(3.5, 0.55 * len(nomes))))
    ax.barh(idx - largura / 2, lucros, height=largura, color="steelblue",
            edgecolor="black", label="Lucro líquido")
    ax.barh(idx + largura / 2, na_minima, height=largura, color="crimson", alpha=0.75,
            edgecolor="black", label="Lucro na taxa mínima")
    ax.axvline(0, color="black", linewidth=0.8)
    ax.set_yticks(idx)
    ax.set_yticklabels(nomes, fontsize=8)
    ax.invert_yaxis()
    ax.set_xlabel("Lucro (R$)")
    ax.set_title("Lucro líquido por ativo e custo de oportunidade (taxa mínima)")
    ax.grid(axis="x", alpha=0.3)
    ax.legend(loc="best", fontsize=8)
    fig.tight_layout()
    return _png(fig)


def grafico_max_pl(modelo) -> Optional[str]:
    """Plano do PL de 2 ativos: restrições, polígono viável, vértices, isolinhas.

    Desenha a reta do orçamento x1+x2=B e a caixa de limites, sombreia o
    polígono viável, marca cada vértice com seu valor de Z, mostra as
    isolinhas de isolucro paralelas, a direção do gradiente, a reta tangente
    ótima por Z*, o vértice ótimo (estrela) e a alocação gulosa
    efetiva (ponto branco).
    """
    if modelo is None or not modelo.viavel:
        return None

    import math

    c1, c2, B = modelo.c1, modelo.c2, modelo.orcamento
    xs = [p[0] for p in modelo.poligono] + [modelo.efetiva[0]]
    ys = [p[1] for p in modelo.poligono] + [modelo.efetiva[1]]
    xmax = max(xs + [modelo.u1, B - modelo.l2]) * 1.12
    ymax = max(ys + [modelo.u2, B - modelo.l1]) * 1.18
    xmax = max(xmax, 1.0)
    ymax = max(ymax, 1.0)

    fig, ax = plt.subplots(figsize=(11, 6.5))

    # Polígono viável (sombreado).
    px = [p[0] for p in modelo.poligono] + [modelo.poligono[0][0]]
    py = [p[1] for p in modelo.poligono] + [modelo.poligono[0][1]]
    ax.fill(px, py, color="steelblue", alpha=0.18, label="Região viável")
    ax.plot(px, py, color="steelblue", linewidth=1.6)

    # Reta do orçamento x1 + x2 = B ao longo do quadro.
    bx = [0.0, min(B, xmax)]
    by = [B, max(B - min(B, xmax), 0.0)]
    ax.plot(bx, by, "--", color="crimson", linewidth=1.8,
            label=f"Orçamento x1+x2={B:,.0f}")

    # Caixa de limites (pontilhada) mostrando as restrições de mínimo/máximo.
    ax.plot([modelo.l1, modelo.u1, modelo.u1, modelo.l1, modelo.l1],
            [modelo.l2, modelo.l2, modelo.u2, modelo.u2, modelo.l2],
            ":", color="gray", linewidth=1.4, label="Limites mín./máx.")

    # Isolinhas de isolucro c1*x1 + c2*x2 = nível; retorna as extremidades desenhadas.
    def _iso(nivel, **kw):
        pts_x, pts_y = [], []
        if abs(c2) > 1e-12:
            for x in (0.0, xmax):
                y = (nivel - c1 * x) / c2
                if 0 <= y <= ymax:
                    pts_x.append(x)
                    pts_y.append(y)
        if abs(c1) > 1e-12:
            for y in (0.0, ymax):
                x = (nivel - c2 * y) / c1
                if 0 <= x <= xmax and not any(abs(x - q) < 1e-9 for q in pts_x):
                    pts_x.append(x)
                    pts_y.append(y)
        if len(pts_x) >= 2:
            ax.plot([pts_x[0], pts_x[-1]], [pts_y[0], pts_y[-1]], **kw)
            return (pts_x[0], pts_y[0], pts_x[-1], pts_y[-1])
        return None

    for nv in modelo.niveis_iso:
        seg = _iso(nv, color="gray", linewidth=1.0, alpha=0.7)
        if seg is not None:
            ax.text((seg[0] + seg[2]) / 2.0, (seg[1] + seg[3]) / 2.0,
                    f"Z={nv:,.0f}", fontsize=8, color="gray",
                    ha="center", va="bottom")
    # Tangente: isolinha ótima de isolucro passando por Z*.
    _iso(modelo.z_estrela, color="green", linewidth=2.6,
         label=f"Tangente Z*={modelo.z_estrela:,.0f}")

    # Seta do gradiente a partir do centroide ao longo de (c1, c2).
    cx = sum(p[0] for p in modelo.poligono) / len(modelo.poligono)
    cy = sum(p[1] for p in modelo.poligono) / len(modelo.poligono)
    norma = math.hypot(c1, c2)
    if norma > 0:
        escala = min(xmax, ymax) * 0.28 / norma
        ax.annotate("", xy=(cx + c1 * escala, cy + c2 * escala), xytext=(cx, cy),
                    arrowprops=dict(facecolor="darkorange", edgecolor="darkorange",
                                    width=2.5, headwidth=9))
        ax.text(cx + c1 * escala, cy + c2 * escala,
                f"  grad Z=({c1:.3g},{c2:.3g})", fontsize=9, color="darkorange")

    # Vértices com rótulos de Z; o ótimo ganha uma estrela.
    for v in modelo.vertices:
        ax.plot(v["x1"], v["x2"], "o", color="black", markersize=5, zorder=5)
        ax.text(v["x1"], v["x2"],
                f"  {v['rotulo']}({v['x1']:,.0f},{v['x2']:,.0f}) Z={v['z']:,.0f}",
                fontsize=8, va="bottom", zorder=6)
    ox = modelo.otimo["x1"]
    oy = modelo.otimo["x2"]
    ax.plot(ox, oy, "*", color="gold", markersize=18,
            markeredgecolor="black", markeredgewidth=1.0, zorder=7,
            label=f"Ótimo {modelo.otimo['vertice']} ({ox:,.0f},{oy:,.0f})")

    # Alocação gulosa efetiva nestes eixos.
    ax.plot(modelo.efetiva[0], modelo.efetiva[1], "o", color="white",
            markersize=9, markeredgecolor="black", markeredgewidth=1.2,
            zorder=7, label="Alocação efetiva")

    ax.set_xlim(0, xmax)
    ax.set_ylim(0, ymax)
    ax.set_xlabel(f"x1: {textwrap.fill(modelo.ativo_x, width=40)} (R$)")
    ax.set_ylabel(f"x2: {textwrap.fill(modelo.ativo_y, width=40)} (R$)")
    ax.set_title(textwrap.fill(
        f"Maximização do lucro: máx Z = {c1:.3g}*x1 + {c2:.3g}*x2  "
        f"(plano de 2 ativos, orçamento {B:,.0f})", width=80))
    ax.grid(alpha=0.3)
    ax.legend(loc="upper left", bbox_to_anchor=(1.0, 1.0), fontsize=8)
    fig.tight_layout()
    return _png(fig)
