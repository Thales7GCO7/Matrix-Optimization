"""Investment performance metrics (ROI, NPV, IRR, payback, PI, alpha).

Metrics are computed per asset (given the deposits chosen by the
optimization) and aggregated for the portfolio. The hurdle rate (minimum
attractive rate) is the NPV discount rate and represents the opportunity
cost of capital; inflation allows the real return to be computed.
"""

from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np

from . import instruments
from . import math_finance as mf
from . import matrix


@dataclass
class AssetMetrics:
    name: str
    is_reserve: bool
    initial_contrib: float
    monthly_contrib: float
    total_contributed: float
    gross_amount: float
    gross_gain: float
    tax: float
    fee: float
    tax_rate: float
    net_amount: float
    net_profit: float
    roi: float
    annualized_roi: Optional[float]
    real_return: Optional[float]
    npv: float
    monthly_irr: Optional[float]
    annual_irr: Optional[float]
    simple_payback: Optional[float]
    discounted_payback: Optional[float]
    profitability_index: Optional[float]
    alpha: Optional[float]
    hurdle_profit: float
    excess_profit: float
    net_annual_rate: float
    projection: List[dict] = field(default_factory=list)


@dataclass
class PortfolioMetrics:
    initial_capital: float
    total_monthly_contrib: float
    invested_capital: float
    reserve: float
    net_amount: float
    net_profit: float
    roi: float
    annualized_roi: Optional[float]
    npv: float
    annual_irr: Optional[float]
    alpha: Optional[float]
    hurdle_profit: float
    excess_profit: float


def compute_asset(
    asset: instruments.Asset,
    initial_contrib: float,
    monthly_contrib: float,
    hurdle_annual: float,
    inflation_annual: float,
    is_reserve: bool = False,
) -> AssetMetrics:
    """Performance metrics of a single asset."""
    res = instruments.asset_summary(asset, initial_contrib, monthly_contrib)
    m = asset.term_months
    a = res["initial_contrib"]
    p = res["monthly_contrib"]
    net = res["net_amount"]
    contributed = res["total_contributed"]

    discount_rate = mf.equivalent_monthly_rate(hurdle_annual)
    series_discount = mf.discounted_series_factor(discount_rate, m)
    npv = -a - p * series_discount + net / (1.0 + discount_rate) ** m

    # IRR over the monthly cash flow. The month-m deposit is placed and
    # immediately redeemed (zero yield), so the final flow is NET - p.
    flow = [-a] + [-p] * (m - 1) + [net - p]
    if a <= 0.0 and p <= 0.0:
        monthly_irr = None
    else:
        monthly_irr = mf.cashflow_irr(flow)
    annual_irr = (1.0 + monthly_irr) ** 12 - 1.0 if monthly_irr is not None else None

    roi = res["net_profit"] / contributed if contributed > 0 else 0.0

    if p > 0.0 and annual_irr is not None:
        annualized_roi = annual_irr
    elif a > 0.0 and net > 0.0:
        annualized_roi = (net / a) ** (12.0 / m) - 1.0
    else:
        annualized_roi = None

    real_return = (
        (1.0 + annualized_roi) / (1.0 + inflation_annual) - 1.0
        if annualized_roi is not None and (1.0 + inflation_annual) > 0.0
        else None
    )

    pv_contributed = a + p * series_discount
    profitability_index = npv / pv_contributed + 1.0 if pv_contributed > 0.0 else None

    alpha = annualized_roi - hurdle_annual if annualized_roi is not None else None

    # Opportunity cost: the same deposit flow earning the hurdle rate.
    hurdle_net = (
        mf.lump_sum_future_value(a, hurdle_annual, m)
        + mf.arrears_series_future_value(p, mf.equivalent_monthly_rate(hurdle_annual), m)
    )
    hurdle_profit = hurdle_net - contributed
    excess_profit = res["net_profit"] - hurdle_profit

    projection = instruments.monthly_projection(asset, a, p)
    simple_payback = _simple_payback(projection)
    discounted_payback = _discounted_payback(projection, discount_rate)

    return AssetMetrics(
        name=asset.name,
        is_reserve=is_reserve,
        initial_contrib=a,
        monthly_contrib=p,
        total_contributed=contributed,
        gross_amount=res["gross_amount"],
        gross_gain=res["gross_gain"],
        tax=res["tax"],
        fee=res["fee"],
        tax_rate=res["tax_rate"],
        net_amount=net,
        net_profit=res["net_profit"],
        roi=roi,
        annualized_roi=annualized_roi,
        real_return=real_return,
        npv=npv,
        monthly_irr=monthly_irr,
        annual_irr=annual_irr,
        simple_payback=simple_payback,
        discounted_payback=discounted_payback,
        profitability_index=profitability_index,
        alpha=alpha,
        hurdle_profit=hurdle_profit,
        excess_profit=excess_profit,
        net_annual_rate=instruments.annualized_net_return(asset),
        projection=projection,
    )


def _simple_payback(projection: List[dict]) -> Optional[float]:
    """Month when the early-redemption (projected net amount) exceeds deposits."""
    for pt in projection:
        if pt["month"] == 0:
            continue
        if pt["net_amount"] >= pt["contributed"]:
            return float(pt["month"])
    return None


def _discounted_payback(projection: List[dict], discount_rate: float) -> Optional[float]:
    """Month when the NPV of redeeming at date t (discounted flow) turns >= 0."""
    if len(projection) < 2:
        return None
    a = projection[0]["contributed"]
    p = projection[1]["contributed"] - a
    for pt in projection:
        t = pt["month"]
        if t == 0:
            continue
        series_discount = mf.discounted_series_factor(discount_rate, t)
        npv = -a - p * series_discount + pt["net_amount"] / (1.0 + discount_rate) ** t
        if npv >= 0.0:
            return float(t)
    return None


def _extend_projection(projection: List[dict], horizon: int, monthly_rate: float) -> List[dict]:
    """Extend the projection to horizon H by compounding past maturity.

    After the asset term the deductions are already paid and the amount
    grows again at the asset monthly rate (implicit reinvestment).
    """
    m = len(projection) - 1
    if m >= horizon:
        return projection[: horizon + 1]
    out = list(projection)
    final_net = projection[-1]["net_amount"]
    final_contributed = projection[-1]["contributed"]
    for t in range(m + 1, horizon + 1):
        out.append(
            {
                "month": t,
                "net_amount": final_net * (1.0 + monthly_rate) ** (t - m),
                "contributed": final_contributed,
            }
        )
    return out


def compute_portfolio(
    metrics: List[AssetMetrics],
    hurdle_annual: float,
) -> PortfolioMetrics:
    """Aggregate portfolio metrics, assembling the actual monthly cash flow.

    The portfolio horizon H is the longest asset term. Monthly deposits
    run until each asset's own term (in arrears); each asset's wealth is
    projected (with implicit reinvestment) to H. The portfolio IRR and
    NPV are computed over that aggregate flow.
    """
    if not metrics:
        # Empty portfolio.
        return PortfolioMetrics(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, None, 0.0, None, None, 0.0, 0.0)

    H = max(len(i.projection) - 1 for i in metrics) or 1
    hurdle_monthly = mf.equivalent_monthly_rate(hurdle_annual)

    total_initial = sum(i.initial_contrib for i in metrics)
    extended = [
        _extend_projection(i.projection, H, _monthly_rate_from_metrics(i)) for i in metrics
    ]

    net_h = sum(pj[H]["net_amount"] for pj in extended)

    # Cash-flow matrix (n_assets x H+1)
    P = matrix.build_cashflow_matrix(metrics, H)
    outflows = P.sum(axis=0)  # 1D vector: summed over assets

    total_contributed = total_initial + float(outflows[1:].sum())

    # Aggregate flow for IRR
    flow = [-total_initial]
    for t in range(1, H):
        flow.append(-outflows[t])
    flow.append(net_h - outflows[H])

    # NPV via dot product
    npv = matrix.portfolio_npv(outflows, net_h, total_initial, hurdle_annual, H)

    if total_initial > 0.0 or any(o > 0 for o in outflows):
        monthly_irr = mf.cashflow_irr(flow)
    else:
        monthly_irr = None
    annual_irr = (1.0 + monthly_irr) ** 12 - 1.0 if monthly_irr is not None else None

    profit = net_h - total_contributed
    reserve = sum(i.total_contributed for i in metrics if i.is_reserve)

    # Benchmark: same deposit flow earning the hurdle rate until H.
    balance = total_initial
    for t in range(1, H + 1):
        balance = balance * (1.0 + hurdle_monthly) + outflows[t]
    hurdle_net = balance
    hurdle_profit = hurdle_net - total_contributed
    excess_profit = profit - hurdle_profit
    alpha = annual_irr - hurdle_annual if annual_irr is not None else None

    return PortfolioMetrics(
        initial_capital=total_initial,
        total_monthly_contrib=float(outflows[1:].sum()),
        invested_capital=total_contributed,
        reserve=reserve,
        net_amount=net_h,
        net_profit=profit,
        roi=profit / total_contributed if total_contributed > 0 else 0.0,
        annualized_roi=annual_irr,
        npv=npv,
        annual_irr=annual_irr,
        alpha=alpha,
        hurdle_profit=hurdle_profit,
        excess_profit=excess_profit,
    )


def _monthly_rate_from_metrics(ind: AssetMetrics) -> float:
    """Monthly rate equivalent to the asset's annualized net return.

    Used only for implicit reinvestment when extending the projection.
    """
    if ind.annualized_roi is not None and ind.annualized_roi > -1.0:
        return mf.equivalent_monthly_rate(ind.annualized_roi)
    return 0.0


def equity_series(
    metrics: List[AssetMetrics], hurdle_annual: float
) -> List[dict]:
    """Total month-by-month net wealth plus the hurdle-rate benchmark.

    Same deposit horizon used for the portfolio: each asset receives
    deposits until its own term and the invested remainder keeps earning
    past maturity.
    """
    if not metrics:
        return []
    H = max(len(i.projection) - 1 for i in metrics) or 1
    hurdle_monthly = mf.equivalent_monthly_rate(hurdle_annual)

    extended = [_extend_projection(i.projection, H, _monthly_rate_from_metrics(i)) for i in metrics]

    total_initial = sum(i.initial_contrib for i in metrics)
    P = matrix.build_cashflow_matrix(metrics, H)
    outflows = P.sum(axis=0)

    hurdle_balance = total_initial
    pts = []
    for t in range(0, H + 1):
        if t > 0:
            hurdle_balance = hurdle_balance * (1.0 + hurdle_monthly) + outflows[t]
        total_wealth = sum(pj[t]["net_amount"] for pj in extended)
        pts.append({"month": t, "wealth": total_wealth, "hurdle": hurdle_balance})
    return pts
