"""Matrix operations for the investment optimizer.

This module shows how the capital-allocation problem can be expressed
with linear algebra: cash-flow matrices, dot products for NPV,
rate vectorization, etc.
"""

import numpy as np
from typing import List, TYPE_CHECKING
from . import math_finance as mf

if TYPE_CHECKING:
    from . import instruments
    from . import performance


def extract_asset_features(assets: List["instruments.Asset"]) -> np.ndarray:
    """Extract numeric asset features as a matrix (n_assets x n_features).

    Features per asset:
    0: annual_rate (effective)
    1: term_months
    2: tax_rate
    3: fee_percent (0 when mode='none')
    4: initial_min
    5: initial_max (inf when None)
    6: uses_monthly (0/1)
    7: monthly_max (inf when None or not used)
    """
    n = len(assets)
    X = np.zeros((n, 8), dtype=float)
    for i, a in enumerate(assets):
        X[i, 0] = a.annual_rate
        X[i, 1] = a.term_months
        X[i, 2] = a.tax_rate
        X[i, 3] = a.fee_percent if a.fee_mode != "none" else 0.0
        X[i, 4] = a.initial_min if a.initial_min is not None else 0.0
        X[i, 5] = a.initial_max if a.initial_max is not None else np.inf
        X[i, 6] = 1.0 if a.uses_monthly else 0.0
        X[i, 7] = a.monthly_max if a.uses_monthly and a.monthly_max is not None else np.inf
    return X


def net_returns_vector(assets: List["instruments.Asset"]) -> np.ndarray:
    """Annualized net rates of all assets, computed in vectorized form.

    Returns a vector r_net where r_net[i] = annualized_net_return(assets[i]).
    """
    from . import instruments
    n = len(assets)
    r_net = np.zeros(n)
    for i, a in enumerate(assets):
        summary = instruments.asset_summary(a, 1.0, 0.0)
        net = summary["net_amount"]
        if net <= 0.0:
            r_net[i] = -np.inf
        else:
            r_net[i] = net ** (12.0 / a.term_months) - 1.0
    return r_net


def build_cashflow_matrix(
    indicators: List["performance.AssetMetrics"],
    horizon: int
) -> np.ndarray:
    """Build the monthly cash-flow matrix (n_assets x H).

    Each row i holds one asset. Column t (1-indexed) contains that
    asset's monthly deposit in month t, or 0 when t exceeds the asset
    term. Column 0 is always 0 (initial deposits handled separately).
    """
    n = len(indicators)
    P = np.zeros((n, horizon + 1), dtype=float)
    for i, ind in enumerate(indicators):
        term = len(ind.projection) - 1
        monthly = ind.monthly_contrib
        if monthly > 0 and term > 0:
            end = min(term, horizon)
            P[i, 1:end + 1] = monthly
    return P


def portfolio_npv(
    outflows: np.ndarray,
    net_amount_h: float,
    total_initial: float,
    hurdle_annual: float,
    horizon: int
) -> float:
    """Portfolio NPV computed with a dot product.

    NPV = -A0 + sum_{t=1..H} (-outflows[t]) / (1+i)^t + NET_H / (1+i)^H
    """
    monthly_i = mf.equivalent_monthly_rate(hurdle_annual)
    discount = (1.0 + monthly_i) ** (-np.arange(horizon + 1))
    npv = -total_initial
    npv += float(np.dot(-outflows[1:], discount[1:]))
    npv += net_amount_h * discount[horizon]
    return npv


def matrix_projection(
    assets: List["instruments.Asset"],
    initial_contribs: np.ndarray,
    monthly_contribs: np.ndarray
) -> np.ndarray:
    """Monthly net-amount projection for all assets.

    Returns a matrix M (n_assets x H_max+1) where M[i, t] is the net
    amount of asset i in month t. Rows are zero-padded past the asset term.
    """
    from . import instruments
    n = len(assets)
    terms = np.array([a.term_months for a in assets])
    H_max = int(terms.max()) if n > 0 else 0
    M = np.zeros((n, H_max + 1), dtype=float)

    for i, a in enumerate(assets):
        a_ini = initial_contribs[i]
        p_mon = monthly_contribs[i]
        m = a.term_months
        annual_r = a.annual_rate
        monthly_i = a.monthly_rate

        summary = instruments.asset_summary(a, a_ini, p_mon)
        total_ded = summary["tax"] + summary["fee"]

        for t in range(0, m + 1):
            if t == 0:
                f = a_ini
            else:
                f = a_ini * (1.0 + annual_r) ** (t / 12.0)
                f += p_mon * mf.arrears_series_factor(monthly_i, t)
            fraction = t / m if m else 1.0
            net = max(f - total_ded * fraction, 0.0)
            M[i, t] = net

    return M


def vectorized_allocate(
    capital: float,
    net_rates: np.ndarray,
    mins: np.ndarray,
    maxs: np.ndarray
) -> np.ndarray:
    """Greedy vectorized allocation by decreasing net rate.

    Args:
        capital: Total capital available.
        net_rates: Vector of net rates (higher = better).
        mins: Per-asset minimum vector.
        maxs: Per-asset maximum vector (inf = uncapped).

    Returns:
        Per-asset allocation vector (same input order).
    """
    n = len(net_rates)
    order = np.argsort(-net_rates)

    mins_ord = mins[order]
    maxs_ord = maxs[order]

    alloc_ord = mins_ord.copy()
    remaining = capital - mins_ord.sum()

    capacities = maxs_ord - mins_ord
    for i in range(n):
        if remaining <= 1e-9:
            break
        cap = capacities[i]
        if cap <= 0:
            continue
        extra = min(cap, remaining)
        alloc_ord[i] += extra
        remaining -= extra

    alloc = np.zeros(n)
    alloc[order] = alloc_ord
    return alloc


def lump_sum_vector(
    principals: np.ndarray,
    annual_rates: np.ndarray,
    terms_months: np.ndarray
) -> np.ndarray:
    """Lump-sum future value for multiple assets (vectorized).

    M[i] = principals[i] * (1 + annual_rates[i])^(terms_months[i] / 12)
    """
    return principals * (1.0 + annual_rates) ** (terms_months / 12.0)


def arrears_series_vector(
    pmts: np.ndarray,
    monthly_rates: np.ndarray,
    n_months: np.ndarray
) -> np.ndarray:
    """In-arrears series future value for multiple assets (vectorized)."""
    result = np.zeros_like(pmts)
    mask = np.abs(monthly_rates) >= 1e-14
    # Near-zero rate case
    result[~mask] = pmts[~mask] * n_months[~mask]
    # General case
    tm = monthly_rates[mask]
    nm = n_months[mask]
    result[mask] = pmts[mask] * ((1.0 + tm) ** nm - 1.0) / tm
    return result


def discounted_series_factor_vector(
    monthly_rates: np.ndarray,
    n_months: np.ndarray
) -> np.ndarray:
    """Series discount factor for multiple rates/terms."""
    result = np.zeros_like(monthly_rates)
    mask = np.abs(monthly_rates) >= 1e-14
    result[~mask] = n_months[~mask].astype(float)
    tm = monthly_rates[mask]
    nm = n_months[mask]
    q = 1.0 / (1.0 + tm)
    result[mask] = q * (1.0 - q ** nm) / (1.0 - q)
    return result
