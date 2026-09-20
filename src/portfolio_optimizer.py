"""Optimal capital allocation across assets.

Since net-return functions are linear in each deposit (actual income is
proportional to capital), the problem of maximizing final net wealth is
a bounded linear-programming problem whose optimal solution is found by
greedy selection: invest first in the assets with the highest annualized
net return, honoring per-asset minimum and maximum limits. Leftover
capital (or capital no asset can place above the hurdle rate) stays in a
reserve earning the hurdle rate itself (opportunity cost).
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np

from . import instruments
from . import performance
from . import matrix


def _create_reserve(hurdle_annual: float):
    """Virtual reserve asset: earns the hurdle rate, no tax/fees."""
    return instruments.Asset(
        name="Reserve (hurdle)",
        rate=max(hurdle_annual, 0.0),
        period="annual",
        basis="effective",
        term_months=12,
        tax_mode="exempt",
        fee_mode="none",
    )


@dataclass
class Allocation:
    asset: instruments.Asset
    initial_contrib: float
    monthly_contrib: float
    is_reserve: bool = False


@dataclass
class OptimizationResult:
    initial_capital: float
    available_monthly: float
    hurdle_annual: float
    inflation_annual: float
    allocations: List[Allocation] = field(default_factory=list)
    metrics: List[performance.AssetMetrics] = field(default_factory=list)
    portfolio: Optional[performance.PortfolioMetrics] = None
    error: str = ""
    assets: List[instruments.Asset] = field(default_factory=list)


class PortfolioOptimizer:
    def __init__(
        self,
        assets: List[instruments.Asset],
        initial_capital: float,
        hurdle_annual: float,
        inflation_annual: float,
        monthly_contrib: float = 0.0,
        use_monthly: bool = False,
    ):
        self.assets = list(assets)
        self.initial_capital = float(initial_capital)
        self.hurdle_annual = float(hurdle_annual)
        self.inflation_annual = float(inflation_annual)
        self.monthly_contrib = float(monthly_contrib) if use_monthly else 0.0
        self.use_monthly = bool(use_monthly)

    def solve(self) -> OptimizationResult:
        res = OptimizationResult(
            initial_capital=self.initial_capital,
            available_monthly=self.monthly_contrib,
            hurdle_annual=self.hurdle_annual,
            inflation_annual=self.inflation_annual,
        )
        try:
            self._validate()
        except ValueError as exc:
            res.error = str(exc)
            return res

        reserve = _create_reserve(self.hurdle_annual)

        initial_order = self._rank_by_net_return(self.assets + [reserve])
        monthly_order = self._rank_by_net_return(
            [i for i in self.assets if i.uses_monthly] + [reserve]
        )

        initial = self._allocate(
            initial_order,
            self.initial_capital,
            min_fn=lambda a: a.initial_min,
            max_fn=lambda a: a.initial_max if a.initial_max is not None else float("inf"),
        )
        monthly = {}
        if self.use_monthly and self.monthly_contrib > 0.0:
            monthly = self._allocate(
                monthly_order,
                self.monthly_contrib,
                min_fn=lambda a: 0.0,
                max_fn=lambda a: a.monthly_max if a.monthly_max is not None else float("inf"),
            )

        # Merge each asset's allocations (reserve included in both flows).
        # Every asset appears in the metrics (even with zero deposits) to
        # show on screen which ones received no capital.
        names = list(dict.fromkeys([a.name for a in self.assets] + [reserve.name]))
        by_name = {a.name: a for a in self.assets + [reserve]}
        allocations: List[Allocation] = []
        metrics: List[performance.AssetMetrics] = []
        for name in names:
            asset = by_name[name]
            a_ini = initial.get(asset, 0.0)
            p_mon = monthly.get(asset, 0.0)
            is_reserve = asset is reserve
            allocations.append(Allocation(asset, a_ini, p_mon, is_reserve=is_reserve))
            metrics.append(
                performance.compute_asset(
                    asset, a_ini, p_mon, self.hurdle_annual, self.inflation_annual, is_reserve=is_reserve
                )
            )

        # Keep only funded assets in the allocation list (used by charts).
        res.allocations = [a for a in allocations if a.initial_contrib > 0 or a.monthly_contrib > 0]
        res.metrics = metrics
        res.assets = [by_name[name] for name in names]
        res.portfolio = performance.compute_portfolio(metrics, self.hurdle_annual)
        return res

    def _validate(self):
        for asset in self.assets:
            if asset.initial_min is None:
                continue
            if (
                asset.initial_max is not None
                and asset.initial_max < asset.initial_min
            ):
                raise ValueError(
                    f"Maximum limit below the minimum for asset {asset.name!r}."
                )
        mins_total = sum(
            a.initial_min for a in self.assets if a.initial_min is not None
        )
        if mins_total > self.initial_capital:
            raise ValueError("The sum of minimum deposits exceeds the available capital.")

    @staticmethod
    def _rank_by_net_return(assets: List[instruments.Asset]) -> List[instruments.Asset]:
        """Decreasing order of annualized net return (vectorized version)."""
        rates = matrix.net_returns_vector(assets)
        order = np.argsort(-rates)
        return [assets[i] for i in order]

    @staticmethod
    def _allocate(
        order: List[instruments.Asset],
        capital: float,
        min_fn,
        max_fn,
    ) -> Dict[instruments.Asset, float]:
        """Optimal allocation with minimum and maximum limits (vectorized).

        1. Guarantee each asset's minimum (mandatory diversification reserve).
        2. Distribute the remainder by efficiency (greedy): first to the
           highest-net-rate assets, up to each one's maximum limit.
        """
        n = len(order)
        rates = np.array([instruments.annualized_net_return(a) for a in order])
        mins = np.array([min_fn(a) or 0.0 for a in order])
        raw_maxs = [max_fn(a) for a in order]
        # Preserve original semantics: an asset with max <= 0 is skipped
        # (it does not even receive its minimum).
        valid = np.array([not (m is not None and m <= 0.0) for m in raw_maxs])
        mins = np.where(valid, mins, 0.0)
        maxs = np.array([m if m is not None else np.inf for m in raw_maxs])
        maxs = np.where(valid, maxs, 0.0)

        alloc_vector = matrix.vectorized_allocate(capital, rates, mins, maxs)

        alloc = {}
        for i, asset in enumerate(order):
            if not valid[i]:
                continue
            if alloc_vector[i] > 1e-9:
                alloc[asset] = float(alloc_vector[i])
            elif mins[i] > 0:
                alloc[asset] = float(mins[i])
        return alloc
