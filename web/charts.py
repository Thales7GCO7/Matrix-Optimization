"""Investment-optimization charts (matplotlib) as base64 PNG."""

import base64
import io
import textwrap
from typing import List, Optional

import numpy as np

import matplotlib

matplotlib.use("Agg", force=True)
import matplotlib.pyplot as plt

from src.performance import AssetMetrics, equity_series


def _png(fig) -> str:
    """Serialize a matplotlib figure as a base64 PNG data URI."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=110, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return "data:image/png;base64," + base64.b64encode(buf.read()).decode("ascii")


def allocation_chart(result) -> Optional[str]:
    """Stacked bars: initial deposit + total monthly deposits per asset."""
    if not result.allocations:
        return None

    names = [a.asset.name for a in result.allocations]
    # Wrap long names onto multiple lines so y-axis labels always fit
    # inside the figure frame instead of overflowing past its edge.
    wrapped = [textwrap.fill(n, width=28) for n in names]
    initial = np.array([a.initial_contrib for a in result.allocations])
    monthly_total = np.array([a.monthly_contrib * a.asset.term_months for a in result.allocations])

    idx = np.arange(len(names))
    fig, ax = plt.subplots(figsize=(12, max(5.0, 1.1 * len(names))))

    ax.barh(idx, initial, height=0.6, color="steelblue", edgecolor="black", label="Initial deposit")
    ax.barh(
        idx, monthly_total, height=0.6, left=initial, color="mediumseagreen",
        edgecolor="black", label="Total monthly deposits",
    )
    for i in range(len(names)):
        tot = initial[i] + monthly_total[i]
        if tot > 0:
            ax.text(tot, i, f"  {tot:,.0f}", va="center", fontsize=9)

    ax.set_yticks(idx)
    ax.set_yticklabels(wrapped, fontsize=9)
    ax.invert_yaxis()
    ax.set_xlabel("Value ($)")
    ax.set_title("Optimal capital allocation")
    ax.grid(axis="x", alpha=0.3)
    ax.legend(loc="lower right", fontsize=9)
    fig.tight_layout()
    return _png(fig)


def allocation_pie_chart(result) -> Optional[str]:
    """Pie chart: share of total invested capital per asset."""
    if not result.allocations:
        return None

    names = [a.asset.name for a in result.allocations]
    totals = np.array([
        a.initial_contrib + a.monthly_contrib * a.asset.term_months
        for a in result.allocations
    ])
    if totals.sum() <= 0:
        return None

    fig, ax = plt.subplots(figsize=(7, 5))
    ax.pie(
        totals,
        labels=names,
        autopct=lambda v: f"{v:.1f}%" if v >= 3.0 else "",
        startangle=90,
        textprops={"fontsize": 9},
    )
    ax.set_title("Capital allocation by asset")
    fig.tight_layout()
    return _png(fig)


def equity_growth_chart(result) -> Optional[str]:
    """Total net-wealth growth vs. the same cash flow at the hurdle rate."""
    if not result.metrics:
        return None
    series = equity_series(result.metrics, result.hurdle_annual)
    if not series:
        return None

    months = [p["month"] for p in series]
    wealth = [p["wealth"] for p in series]
    hurdle = [p["hurdle"] for p in series]

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(months, wealth, "o-", color="steelblue", linewidth=2, label="Net wealth (portfolio)")
    ax.plot(
        months, hurdle, "--", color="crimson", linewidth=1.8, alpha=0.85,
        label="Same cash flow at hurdle (opportunity cost)",
    )
    ax.fill_between(months, hurdle, wealth, where=[p >= t for p, t in zip(wealth, hurdle)], color="green",
                    alpha=0.12, interpolate=True)
    ax.set_xlabel("Month")
    ax.set_ylabel("Wealth ($)")
    ax.set_title("Wealth projection to redemption")
    ax.grid(alpha=0.3)
    ax.legend(loc="upper left", fontsize=9)
    fig.tight_layout()
    return _png(fig)


def profit_vs_hurdle_chart(result) -> Optional[str]:
    """Net profit per asset vs. what the same flow would earn at the hurdle."""
    if not result.metrics:
        return None
    inds: List[AssetMetrics] = result.metrics
    names = [i.name for i in inds]
    idx = np.arange(len(names))

    profits = np.array([i.net_profit for i in inds])
    at_hurdle = np.array([i.hurdle_profit for i in inds])
    width = 0.35

    fig, ax = plt.subplots(figsize=(10, max(3.5, 0.55 * len(names))))
    ax.barh(idx - width / 2, profits, height=width, color="steelblue",
            edgecolor="black", label="Net profit")
    ax.barh(idx + width / 2, at_hurdle, height=width, color="crimson", alpha=0.75,
            edgecolor="black", label="Profit at hurdle")
    ax.axvline(0, color="black", linewidth=0.8)
    ax.set_yticks(idx)
    ax.set_yticklabels(names, fontsize=8)
    ax.invert_yaxis()
    ax.set_xlabel("Profit ($)")
    ax.set_title("Net profit per asset and opportunity cost (hurdle)")
    ax.grid(axis="x", alpha=0.3)
    ax.legend(loc="best", fontsize=8)
    fig.tight_layout()
    return _png(fig)


def lp_max_chart(model) -> Optional[str]:
    """2-asset LP plane: constraints, feasible polygon, vertices, iso-lines.

    Draws the budget line x1+x2=B and the bound box, shades the feasible
    polygon, marks every vertex with its Z value, shows parallel
    iso-profit lines, the gradient direction, the tangent optimal line
    through Z*, the optimum vertex (star), and the actual greedy
    allocation (white dot).
    """
    if model is None or not model.feasible:
        return None

    import math

    c1, c2, B = model.c1, model.c2, model.budget
    xs = [p[0] for p in model.polygon] + [model.actual[0]]
    ys = [p[1] for p in model.polygon] + [model.actual[1]]
    xmax = max(xs + [model.u1, B - model.l2]) * 1.12
    ymax = max(ys + [model.u2, B - model.l1]) * 1.18
    xmax = max(xmax, 1.0)
    ymax = max(ymax, 1.0)

    fig, ax = plt.subplots(figsize=(11, 6.5))

    # Feasible polygon (shaded).
    px = [p[0] for p in model.polygon] + [model.polygon[0][0]]
    py = [p[1] for p in model.polygon] + [model.polygon[0][1]]
    ax.fill(px, py, color="steelblue", alpha=0.18, label="Feasible region")
    ax.plot(px, py, color="steelblue", linewidth=1.6)

    # Budget line x1 + x2 = B across the frame.
    bx = [0.0, min(B, xmax)]
    by = [B, max(B - min(B, xmax), 0.0)]
    ax.plot(bx, by, "--", color="crimson", linewidth=1.8,
            label=f"Budget x1+x2={B:,.0f}")

    # Bound box (dotted) showing the min/max constraints.
    ax.plot([model.l1, model.u1, model.u1, model.l1, model.l1],
            [model.l2, model.l2, model.u2, model.u2, model.l2],
            ":", color="gray", linewidth=1.4, label="Min/max bounds")

    # Iso-profit lines c1*x1 + c2*x2 = level; returns drawn endpoints.
    def _iso(level, **kw):
        pts_x, pts_y = [], []
        if abs(c2) > 1e-12:
            for x in (0.0, xmax):
                y = (level - c1 * x) / c2
                if 0 <= y <= ymax:
                    pts_x.append(x)
                    pts_y.append(y)
        if abs(c1) > 1e-12:
            for y in (0.0, ymax):
                x = (level - c2 * y) / c1
                if 0 <= x <= xmax and not any(abs(x - q) < 1e-9 for q in pts_x):
                    pts_x.append(x)
                    pts_y.append(y)
        if len(pts_x) >= 2:
            ax.plot([pts_x[0], pts_x[-1]], [pts_y[0], pts_y[-1]], **kw)
            return (pts_x[0], pts_y[0], pts_x[-1], pts_y[-1])
        return None

    for lv in model.iso_levels:
        seg = _iso(lv, color="gray", linewidth=1.0, alpha=0.7)
        if seg is not None:
            ax.text((seg[0] + seg[2]) / 2.0, (seg[1] + seg[3]) / 2.0,
                    f"Z={lv:,.0f}", fontsize=8, color="gray",
                    ha="center", va="bottom")
    # Tangent: optimal iso-profit line through Z*.
    _iso(model.z_star, color="green", linewidth=2.6,
         label=f"Tangent Z*={model.z_star:,.0f}")

    # Gradient arrow from the centroid along (c1, c2).
    cx = sum(p[0] for p in model.polygon) / len(model.polygon)
    cy = sum(p[1] for p in model.polygon) / len(model.polygon)
    norm = math.hypot(c1, c2)
    if norm > 0:
        scale = min(xmax, ymax) * 0.28 / norm
        ax.annotate("", xy=(cx + c1 * scale, cy + c2 * scale), xytext=(cx, cy),
                    arrowprops=dict(facecolor="darkorange", edgecolor="darkorange",
                                    width=2.5, headwidth=9))
        ax.text(cx + c1 * scale, cy + c2 * scale,
                f"  grad Z=({c1:.3g},{c2:.3g})", fontsize=9, color="darkorange")

    # Vertices with Z labels; optimum gets a star.
    for v in model.vertices:
        ax.plot(v["x1"], v["x2"], "o", color="black", markersize=5, zorder=5)
        ax.text(v["x1"], v["x2"],
                f"  {v['label']}({v['x1']:,.0f},{v['x2']:,.0f}) Z={v['z']:,.0f}",
                fontsize=8, va="bottom", zorder=6)
    ox = model.optimum["x1"]
    oy = model.optimum["x2"]
    ax.plot(ox, oy, "*", color="gold", markersize=18,
            markeredgecolor="black", markeredgewidth=1.0, zorder=7,
            label=f"Optimum {model.optimum['vertex']} ({ox:,.0f},{oy:,.0f})")

    # Actual greedy allocation on these axes.
    ax.plot(model.actual[0], model.actual[1], "o", color="white",
            markersize=9, markeredgecolor="black", markeredgewidth=1.2,
            zorder=7, label="Actual allocation")

    ax.set_xlim(0, xmax)
    ax.set_ylim(0, ymax)
    ax.set_xlabel(f"x1: {textwrap.fill(model.asset_x, width=40)} ($)")
    ax.set_ylabel(f"x2: {textwrap.fill(model.asset_y, width=40)} ($)")
    ax.set_title(textwrap.fill(
        f"Profit maximization: max Z = {c1:.3g}*x1 + {c2:.3g}*x2  "
        f"(2-asset plane, budget {B:,.0f})", width=80))
    ax.grid(alpha=0.3)
    ax.legend(loc="upper left", bbox_to_anchor=(1.0, 1.0), fontsize=8)
    fig.tight_layout()
    return _png(fig)
