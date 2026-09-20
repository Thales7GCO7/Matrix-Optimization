"""Investment asset model and gross-to-net computation.

An `Asset` is characterized by its rate (with period and basis), its term
to redemption, income tax, and an administrative fee. Income is modeled as
a deposit series:

- a lump-sum initial deposit A (capital allocated today);
- a monthly deposit P (recurring, in arrears, at the end of each month).

The final net-profit function is linear in A and in P, which allows an
optimal allocation via greedy selection (economic intuition: invest first
where the annualized net return is highest).
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from . import math_finance as mf
from . import tax
from . import matrix

#: Accepted rate bases and tax/fee modes.
RATE_BASES = ["effective", "nominal"]


@dataclass(frozen=True)
class Asset:
    name: str
    rate: float = 0.10
    period: str = "annual"
    basis: str = "effective"
    term_months: int = 12
    tax_mode: str = "exempt"
    tax_percent: float = 0.0
    tax_brackets: Optional[Tuple[Tuple[float, float], ...]] = None
    tax_bracket_key: str = "term"
    fee_mode: str = "none"
    fee_percent: float = 0.0
    initial_min: float = 0.0
    initial_max: Optional[float] = None
    uses_monthly: bool = False
    monthly_max: Optional[float] = None

    @property
    def annual_rate(self) -> float:
        return mf.effective_annual_rate(self.rate, self.period, self.basis)

    @property
    def monthly_rate(self) -> float:
        return mf.equivalent_monthly_rate(self.annual_rate)

    @property
    def tax_rate(self) -> float:
        lookup = float(self.term_months) if self.tax_bracket_key == "term" else 0.0
        return tax.resolve_tax_rate(
            self.tax_mode, self.tax_percent, self.tax_brackets,
            self.tax_bracket_key, lookup,
        )

    def __post_init__(self):
        if not self.name:
            raise ValueError("Asset without a name.")
        if self.term_months <= 0:
            raise ValueError(f"Invalid term for asset {self.name!r}: {self.term_months}.")
        if self.rate <= -1.0:
            raise ValueError(f"Invalid rate for asset {self.name!r}.")

    def label(self) -> str:
        rate_pct = self.rate * 100
        basis = "eff." if self.basis == "effective" else "nom."
        summary = f"{self.name} | {rate_pct:.3g}% p.a.-{self._period_abbr(self.period)} ({basis})"
        summary += f" | {self.term_months} months"
        if self.tax_mode == "fixed":
            summary += f" | tax {self.tax_percent * 100:.2g}%"
        elif self.tax_mode == "brackets":
            summary += " | tax brackets"
        elif self.tax_mode == "exempt":
            summary += " | exempt"
        if self.fee_mode != "none":
            summary += f" | fee {self.fee_percent * 100:.2g}%/{self.fee_mode}"
        return summary

    @staticmethod
    def _period_abbr(period: str) -> str:
        return {"annual": "y", "semiannual": "s", "quarterly": "q", "bimonthly": "b",
                "monthly": "m", "weekly": "w", "daily": "d"}.get(period, "y")


def lump_sum_gross(asset: Asset, principal: float) -> float:
    """Gross accumulated value of a lump-sum deposit held to redemption."""
    if principal <= 0.0:
        return 0.0
    return mf.lump_sum_future_value(float(principal), asset.annual_rate, asset.term_months)


def monthly_series_gross(asset: Asset, pmt: float) -> float:
    """Gross accumulated value of in-arrears monthly deposits (pmt) to redemption."""
    if pmt <= 0.0:
        return 0.0
    return mf.arrears_series_future_value(float(pmt), asset.monthly_rate, asset.term_months)


def deductions(asset: Asset, gross_amount: float, gross_gain: float, contributed: float) -> Dict[str, float]:
    """Income-tax and administrative-fee deductions in currency units.

    Delegates to the generic :func:`tax.compute_net_amount` so every
    investment type shares one net-value logic.
    """
    res = tax.compute_net_amount(
        gross_amount, contributed, asset.tax_mode, asset.tax_percent,
        asset.fee_mode, asset.fee_percent, asset.term_months,
        getattr(asset, "tax_brackets", None),
        getattr(asset, "tax_bracket_key", "term"),
    )
    return {"tax": res["tax"], "fee": res["fee"]}


def asset_summary(asset: Asset, initial_contrib: float, monthly_contrib: float) -> Dict:
    """Investment summary for the asset given its deposits (actual cash-flow values).

    Generic pipeline shared by every investment type: gross compounding
    first, then :func:`tax.compute_net_amount` (tax + fee -> net).
    """
    a = float(initial_contrib)
    p = float(monthly_contrib)
    m = asset.term_months

    gross_total = lump_sum_gross(asset, a) + monthly_series_gross(asset, p)
    contributed = a + p * m

    net = tax.compute_net_amount(
        gross_total, contributed, asset.tax_mode, asset.tax_percent,
        asset.fee_mode, asset.fee_percent, m,
        asset.tax_brackets, asset.tax_bracket_key,
    )

    return {
        "initial_contrib": a,
        "monthly_contrib": p,
        "total_contributed": contributed,
        "gross_amount": gross_total,
        "gross_gain": net["gross_gain"],
        "tax": net["tax"],
        "fee": net["fee"],
        "tax_rate": net["tax_rate"],
        "net_amount": net["net_amount"],
        "net_profit": net["net_profit"],
    }


def monthly_projection(asset: Asset, initial_contrib: float, monthly_contrib: float) -> List[Dict]:
    """Month-by-month projection of the net amount and the contributed capital.

    Illustrative: deductions (income tax and fees) that only occur at
    redemption are spread linearly over the term, so the final month of
    the projection matches the actual summary exactly. Used for payback
    and charts.
    """
    a = float(initial_contrib)
    p = float(monthly_contrib)
    m = asset.term_months
    annual_r = asset.annual_rate
    monthly_i = asset.monthly_rate

    summary = asset_summary(asset, a, p)
    total_ded = summary["tax"] + summary["fee"]

    pts = []
    for t in range(0, m + 1):
        if t == 0:
            f = a
        else:
            f = a * (1.0 + annual_r) ** (t / 12.0)
            f += p * mf.arrears_series_factor(monthly_i, t)
        fraction = t / m if m else 1.0
        net = max(f - total_ded * fraction, 0.0)
        pts.append({"month": t, "net_amount": net, "contributed": a + p * t})
    return pts


def annualized_net_return(asset: Asset) -> float:
    """Annualized net return of the asset (basis for the allocation ranking).

    Computed with a unit lump-sum deposit (the function is linear in A, so
    the rate does not depend on the amount). Accounts for income tax and
    administrative fees.
    """
    summary = asset_summary(asset, 1.0, 0.0)
    net = summary["net_amount"]
    if net <= 0.0:
        return float("-inf")
    return (net) ** (12.0 / asset.term_months) - 1.0


def net_returns_vector(assets: List[Asset]) -> np.ndarray:
    """Wrapper around matrix.net_returns_vector."""
    return matrix.net_returns_vector(assets)
