from typing import Optional, Sequence

import numpy as np

try:
    import matplotlib

    matplotlib.use("Agg", force=True)
except Exception:
    pass
import matplotlib.pyplot as plt


def _polygon_feasivel(A, b, tol=1e-9) -> Optional[np.ndarray]:
    """Poligono convexo da regiao viavel de Ax <= b, x >= 0 (2 variaveis).

    Enumera as intersecoes par a par das linhas (restricoes + eixos),
    mantem as que satisfazem todas as restricoes e calcula o fecho convexo.
    Retorna None se a regiao nao for um poligono limitado.
    """
    A = np.asarray(A, dtype=float)
    b = np.asarray(b, dtype=float)
    if A.shape[1] != 2:
        return None

    lines = [(A[i][:2], float(b[i])) for i in range(A.shape[0])]
    lines.append((np.array([1.0, 0.0]), 0.0))
    lines.append((np.array([0.0, 1.0]), 0.0))

    points = []
    for i in range(len(lines)):
        for j in range(i + 1, len(lines)):
            a1, r1 = lines[i]
            a2, r2 = lines[j]
            M = np.vstack([a1, a2]).T
            if abs(np.linalg.det(M)) < 1e-12:
                continue
            p = np.linalg.solve(M, np.array([r1, r2]))
            if np.all(p >= -tol) and np.all(A @ p <= b + 1e-7):
                points.append(p)

    if len(points) < 3:
        return None

    unique = []
    for p in points:
        if not any(np.allclose(p, q, atol=1e-8) for q in unique):
            unique.append(p)
    if len(unique) < 3:
        return None

    unique = sorted(unique, key=lambda p: (p[0], p[1]))

    def cross(o, a, c):
        return (a[0] - o[0]) * (c[1] - o[1]) - (a[1] - o[1]) * (c[0] - o[0])

    lower = []
    for p in unique:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= tol:
            lower.pop()
        lower.append(p)
    upper = []
    for p in reversed(unique):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= tol:
            upper.pop()
        upper.append(p)

    hull = np.array(lower[:-1] + upper[:-1])
    return hull if len(hull) >= 3 else None


def grafico_simplex(A, b, c, solucao, z_otimo=None):
    A = np.asarray(A, dtype=float)
    b = np.asarray(b, dtype=float)
    c = np.asarray(c, dtype=float)
    if A.shape[1] != 2:
        return None

    hull = _polygon_feasivel(A, b)
    if hull is None:
        return None

    fig, ax = plt.subplots(figsize=(8, 6))
    from matplotlib.patches import Polygon

    ax.add_patch(Polygon(hull, closed=True, alpha=0.25, color="green", label="Regiao viavel"))

    for v in hull:
        ax.plot(v[0], v[1], "ko", ms=5)
        ax.annotate(
            f"({v[0]:.3g}, {v[1]:.3g})",
            (v[0], v[1]),
            textcoords="offset points",
            xytext=(6, 6),
            fontsize=8,
        )

    range_x = max(hull[:, 0]) - min(hull[:, 0])
    range_y = max(hull[:, 1]) - min(hull[:, 1])
    pad = 0.15
    ax.set_xlim(min(hull[:, 0]) - pad * range_x, max(hull[:, 0]) + pad * range_x)
    ax.set_ylim(min(hull[:, 1]) - pad * range_y, max(hull[:, 1]) + pad * range_y)

    x = np.linspace(ax.get_xlim()[0], ax.get_xlim()[1], 300)
    for a, r in zip(A, b):
        if abs(a[1]) > 1e-12:
            ax.plot(x, (r - a[0] * x) / a[1], "--", alpha=0.7, linewidth=1.5)
        else:
            ax.axvline(r / a[0], linestyle="--", alpha=0.7, linewidth=1.5)

    if z_otimo and np.abs(z_otimo) > 1e-15 and abs(c[1]) > 1e-12:
        for k in range(1, 7):
            zz = float(z_otimo) * k / 6.0
            ax.plot(x, (zz - c[0] * x) / c[1], "k:", alpha=0.25)

    if solucao is not None:
        ax.plot(solucao[0], solucao[1], "r*", ms=16, label="Ponto otimo")

    ax.set_xlabel("$x_1$")
    ax.set_ylabel("$x_2$")
    ax.set_title("Regiao viavel do problema de Programacao Linear")
    ax.grid(alpha=0.3)
    ax.set_aspect("equal", adjustable="box")
    ax.legend(loc="best")
    fig.tight_layout()
    return fig


def grafico_newton_escalar(func, x0: float, root: float):
    x0 = float(x0)
    root = float(root)
    span = max(abs(root - x0), 2.0)
    xs = np.linspace(x0 - span, x0 + span, 400)
    ys = []
    for t in xs:
        try:
            ys.append(float(func(t)))
        except Exception:
            ys.append(np.nan)
    xs = np.asarray(xs)
    ys = np.asarray(ys)
    mask = np.isfinite(ys)

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(xs[mask], ys[mask], "b-", linewidth=1.8)
    ax.axhline(0.0, color="gray", linewidth=0.8)
    ax.axvline(root, color="r", linestyle="--", alpha=0.6)
    ax.plot(root, 0.0, "ro", markersize=8)
    ax.set_xlabel("x")
    ax.set_ylabel("F(x)")
    ax.set_title(f"Funcao F(x) e raiz encontrada (x = {root:.6g})")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    return fig


def grafico_convergencia(norms: Sequence[float]):
    arr = np.asarray(norms, dtype=float)
    arr = arr[np.isfinite(arr)]
    if arr.size == 0:
        return None
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.semilogy(range(1, arr.size + 1), arr, "o-", color="steelblue")
    ax.set_xlabel("Iteracao")
    ax.set_ylabel("$\\|F(x)\\|$ (escala log)")
    ax.set_title("Convergencia do residuo por iteracao")
    ax.grid(True, which="both", alpha=0.3)
    fig.tight_layout()
    return fig


def grafico_contorno(func, x0, solution):
    x0 = np.asarray(x0, dtype=float)
    solution = np.asarray(solution, dtype=float)
    if solution.size != 2:
        return None
    half = max(
        float(np.max(np.abs(solution - x0))) if x0.size == 2 else 0.0,
        float(np.max(np.abs(solution))),
        1.0,
    )
    g = np.linspace(solution[0] - 1.5 * half, solution[0] + 1.5 * half, 60)
    h = np.linspace(solution[1] - 1.5 * half, solution[1] + 1.5 * half, 60)
    X, Y = np.meshgrid(g, h)
    Z = np.zeros_like(X)
    for i in range(X.shape[0]):
        for j in range(X.shape[1]):
            try:
                Z[i, j] = float(func([X[i, j], Y[i, j]]))
            except Exception:
                Z[i, j] = np.nan

    fig, ax = plt.subplots(figsize=(8, 6))
    cf = ax.contourf(X, Y, Z, levels=30, cmap="viridis", alpha=0.75)
    fig.colorbar(cf, ax=ax, label="f(x)")
    ax.contour(X, Y, Z, levels=12, colors="black", alpha=0.3, linewidths=0.5)
    ax.plot(solution[0], solution[1], "r*", markersize=16, label="Ponto otimo")
    ax.set_xlabel("$x_1$")
    ax.set_ylabel("$x_2$")
    ax.set_title("Mapa de contorno da funcao objetivo")
    ax.legend(loc="best")
    fig.tight_layout()
    return fig


def grafico_alocacao(opt):
    if opt.allocation is None:
        return None
    alloc = np.asarray(opt.allocation, dtype=float)
    n = len(alloc)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))

    idx = np.arange(n)
    ax1.bar(idx, alloc, color="steelblue", edgecolor="black", alpha=0.85)
    ax1.set_xticks(idx)
    ax1.set_xticklabels([f"$x_{{{i + 1}}}$" for i in range(n)])
    ax1.set_ylabel("Valor alocado")
    ax1.set_title("Alocacao otima por investimento")
    for i, v in enumerate(alloc):
        pct = v / opt.budget * 100 if opt.budget > 0 else 0.0
        ax1.text(i, v, f"{pct:.1f}%", ha="center", va="bottom", fontsize=9)

    grid = np.linspace(0, opt.budget, 300) if opt.budget > 0 else np.linspace(0, 1, 300)
    for i, f in enumerate(opt.funcs):
        yv = []
        for t in grid:
            try:
                yv.append(float(f["func"](t)))
            except Exception:
                yv.append(np.nan)
        ax2.plot(grid, yv, linewidth=1.6, label=f"$f_{{{i + 1}}}$")
        try:
            val = float(f["func"](alloc[i]))
            ax2.plot(alloc[i], val, "o", markersize=7)
        except Exception:
            pass
    ax2.set_xlabel("x")
    ax2.set_ylabel("Retorno $f_i(x)$")
    ax2.set_title("Funcoes de retorno e alocacao escolhida")
    ax2.legend(fontsize=8, loc="best")
    ax2.set_xlim(0, max(opt.budget, 1.0))

    fig.tight_layout()
    return fig