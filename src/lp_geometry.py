"""Two-asset projection of the profit-maximization linear program.

The full problem is N-dimensional::

    max  Z = SUM p_i * x_i            (net profit, linear in each deposit)
    s.t. SUM x_i <= B                 (available initial capital)
         l_i <= x_i <= u_i            (per-asset minimum/maximum)

where ``p_i`` is the net profit of $1 placed in asset ``i``
(``asset_summary(asset, 1.0, 0.0)["net_profit"]``), ``B`` the initial
capital, and ``l_i``/``u_i`` the asset's initial bounds. Because the
objective and all constraints are linear, the optimum sits at a vertex
of the feasible polytope — hence the greedy solver (walk in the
direction of the gradient ``(p_1..p_N)`` until a bound stops you).

This module projects that geometry onto the plane of the two most
efficient assets (``x1`` horizontal, ``x2`` vertical) so it can be drawn:
constraint lines, feasible polygon, enumerated vertices with their
``Z`` values, iso-profit lines, the gradient, and the tangent (optimal)
iso-profit line touching the polygon at the optimum vertex.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from . import instruments
from . import matrix

EPS = 1e-9


@dataclass
class LPModel:
    feasible: bool = False
    asset_x: str = ""
    asset_y: str = ""
    c1: float = 0.0
    c2: float = 0.0
    budget: float = 0.0
    l1: float = 0.0
    u1: float = 0.0
    l2: float = 0.0
    u2: float = 0.0
    actual: Tuple[float, float] = (0.0, 0.0)
    polygon: List[Tuple[float, float]] = field(default_factory=list)
    vertices: List[Dict[str, Any]] = field(default_factory=list)
    optimum: Dict[str, Any] = field(default_factory=dict)
    iso_levels: List[float] = field(default_factory=list)
    z_star: float = 0.0
    edge_optimal: bool = False
    profit_functions: List[Dict[str, Any]] = field(default_factory=list)
    reason: str = ""


def _unit_profit(asset: instruments.Asset) -> Tuple[float, Dict[str, Any]]:
    """Net profit of $1 of initial deposit plus its formula breakdown."""
    s = instruments.asset_summary(asset, 1.0, 0.0)
    gross_factor = s["gross_amount"]  # G for x = 1
    info = {
        "asset": asset.name,
        "formula": (
            f"L(x) = p*x, p = G - 1 - tax_1 - fee_1 "
            f"= {gross_factor:.6g} - 1 - {s['tax']:.6g} - {s['fee']:.6g} "
            f"= {s['net_profit']:.6g}"
        ),
        "per_unit_profit": float(s["net_profit"]),
        "gross_factor": float(gross_factor),
        "tax_per_unit": float(s["tax"]),
        "fee_per_unit": float(s["fee"]),
        "term_months": asset.term_months,
    }
    return float(s["net_profit"]), info


def _pick_axes(assets: List[instruments.Asset]) -> Optional[Tuple[Any, Any]]:
    """Two most efficient non-reserve assets; falls back to best + reserve."""
    cands = [a for a in assets if a.name != "Reserve (hurdle)"]
    if len(cands) >= 2:
        rates = matrix.net_returns_vector(cands)
        order = sorted(range(len(cands)), key=lambda i: -rates[i])
        return cands[order[0]], cands[order[1]]
    if len(cands) == 1:
        reserve = next((a for a in assets if a.name == "Reserve (hurdle)"), None)
        if reserve is not None:
            return cands[0], reserve
        return None
    return None


def build_lp_model(result) -> Optional[LPModel]:
    """Project an OptimizationResult onto its 2-asset LP plane."""
    assets = list(getattr(result, "assets", []) or [])
    axes = _pick_axes(assets)
    if axes is None:
        return None
    ax, ay = axes
    B = float(result.initial_capital)
    if B <= 0.0:
        return None

    c1, info_x = _unit_profit(ax)
    c2, info_y = _unit_profit(ay)

    l1 = max(float(ax.initial_min or 0.0), 0.0)
    u1 = float(ax.initial_max) if ax.initial_max else B
    u1 = min(u1, B)
    l2 = max(float(ay.initial_min or 0.0), 0.0)
    u2 = float(ay.initial_max) if ay.initial_max else B
    u2 = min(u2, B)

    model = LPModel(
        asset_x=ax.name, asset_y=ay.name, c1=c1, c2=c2, budget=B,
        l1=l1, u1=u1, l2=l2, u2=u2,
        profit_functions=[info_x, info_y],
    )
    if l1 + l2 > B + EPS:
        model.reason = "Infeasible 2-asset projection: l1 + l2 > budget."
        return model

    pts = _feasible_vertices(l1, u1, l2, u2, B)
    if not pts:
        model.reason = "Empty feasible polygon."
        return model

    model.feasible = True
    model.polygon = _order_polygon(pts)
    # Vertices with Z values, ranked best-first.
    ranked = sorted(pts, key=lambda p: -(c1 * p[0] + c2 * p[1]))
    z_star = c1 * ranked[0][0] + c2 * ranked[0][1]
    model.z_star = z_star
    model.vertices = [
        {"label": f"V{k + 1}", "x1": p[0], "x2": p[1],
         "z": c1 * p[0] + c2 * p[1],
         "optimal": (c1 * p[0] + c2 * p[1]) >= z_star - 1e-6}
        for k, p in enumerate(ranked)
    ]
    model.edge_optimal = sum(1 for v in model.vertices if v["optimal"]) > 1
    best = model.vertices[0]
    model.optimum = {"x1": best["x1"], "x2": best["x2"], "z": best["z"],
                     "vertex": best["label"]}
    model.iso_levels = [z_star * f for f in (0.25, 0.55, 0.85) if z_star > 0]

    by_name = {m.name: m for m in (result.metrics or [])}
    mx = by_name.get(ax.name)
    my = by_name.get(ay.name)
    if mx is not None and my is not None:
        model.actual = (float(mx.initial_contrib), float(my.initial_contrib))
    return model


def _feasible_vertices(l1, u1, l2, u2, B) -> List[Tuple[float, float]]:
    """Box corners inside the budget half-plane + budget-line crossings."""
    raw: List[Tuple[float, float]] = [
        (l1, l2), (l1, u2), (u1, l2), (u1, u2),
        (B - l2, l2), (B - u2, u2), (l1, B - l1), (u1, B - u1),
    ]
    out: List[Tuple[float, float]] = []
    for x1, x2 in raw:
        if not (l1 - EPS <= x1 <= u1 + EPS and l2 - EPS <= x2 <= u2 + EPS):
            continue
        if x1 + x2 > B + EPS:
            continue
        out.append((max(x1, 0.0), max(x2, 0.0)))
    # Deduplicate (rounded) preserving order.
    seen, uniq = set(), []
    for p in out:
        key = (round(p[0], 6), round(p[1], 6))
        if key not in seen:
            seen.add(key)
            uniq.append(p)
    return uniq


def _order_polygon(pts: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
    """Order vertices counter-clockwise around the centroid (for shading)."""
    cx = sum(p[0] for p in pts) / len(pts)
    cy = sum(p[1] for p in pts) / len(pts)
    import math
    return sorted(pts, key=lambda p: math.atan2(p[1] - cy, p[0] - cx))


def describe_lp_model(model: LPModel) -> Dict[str, Any]:
    """JSON-serializable model: formulas, constraints, vertices, resolution."""
    def _f(v: float) -> float:
        return round(float(v), 2)
    constraints = [
        f"x1 + x2 <= {_f(model.budget)}  (budget)",
        f"{_f(model.l1)} <= x1 <= {_f(model.u1) if model.u1 < float('inf') else float('inf')}  ({model.asset_x})",
        f"{_f(model.l2)} <= x2 <= {_f(model.u2) if model.u2 < float('inf') else float('inf')}  ({model.asset_y})",
        "x1 >= 0, x2 >= 0",
    ]
    steps = [
        f"Write each profit function: L1(x1) = {model.c1:.6g}*x1, "
        f"L2(x2) = {model.c2:.6g}*x2 (net profit per $1 after tax/fees).",
        f"Objective: max Z = {model.c1:.6g}*x1 + {model.c2:.6g}*x2; "
        f"gradient vZ = ({model.c1:.6g}, {model.c2:.6g}).",
        "Intersect the bound box with the budget half-plane x1 + x2 <= B: "
        "the feasible polygon (shaded).",
        "Evaluate Z at every vertex " + ", ".join(
            f"{v['label']}({_f(v['x1'])}, {_f(v['x2'])}) -> Z={_f(v['z'])}"
            for v in model.vertices) + ".",
        f"Optimum at {model.optimum.get('vertex')}: "
        f"x1*={_f(model.optimum.get('x1', 0.0))}, "
        f"x2*={_f(model.optimum.get('x2', 0.0))}, "
        f"Z*={_f(model.optimum.get('z', 0.0))} — the tangent iso-profit line "
        f"{model.c1:.6g}*x1 + {model.c2:.6g}*x2 = {_f(model.z_star)} "
        "touches the polygon there"
        + (" along a whole edge (any point on it is optimal)." if model.edge_optimal
           else " (unique vertex)."),
        "The N-asset greedy solver does exactly this walk in N dimensions: "
        "guarantee minimums, then push remaining capital along vZ into the "
        "steepest asset until a cap binds. The monthly-deposit LP is "
        "analogous (variables P_i, monthly caps).",
    ]
    return {
        "feasible": model.feasible,
        "asset_x": model.asset_x,
        "asset_y": model.asset_y,
        "objective": f"max Z = {model.c1:.6g}*x1 + {model.c2:.6g}*x2",
        "c1": model.c1,
        "c2": model.c2,
        "gradient": [model.c1, model.c2],
        "budget": model.budget,
        "bounds": {"l1": model.l1, "u1": model.u1,
                   "l2": model.l2, "u2": model.u2},
        "constraints": constraints,
        "profit_functions": model.profit_functions,
        "vertices": [{**v, "x1": _f(v["x1"]), "x2": _f(v["x2"]),
                      "z": _f(v["z"])} for v in model.vertices],
        "optimum": {k: (_f(v) if isinstance(v, float) else v)
                    for k, v in model.optimum.items()},
        "tangent": f"{model.c1:.6g}*x1 + {model.c2:.6g}*x2 = {_f(model.z_star)}",
        "z_star": _f(model.z_star),
        "edge_optimal": model.edge_optimal,
        "actual": {"x1": _f(model.actual[0]), "x2": _f(model.actual[1])},
        "steps": steps,
        "note": ("2-asset projection onto the two most efficient assets; "
                 "with 3+ funded assets the true optimum lives in N dimensions "
                 "and this plane shows the method's geometry. White dot = "
                 "actual greedy allocation on these axes."),
    }
