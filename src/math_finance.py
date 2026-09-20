"""Financial math: rate conversion, compound growth, and payment series.

Conventions used throughout the project:
- Rates are always decimal fractions (e.g.: 0.135 = 13.5% p.a.).
- Each asset's rate is quoted with a compounding period
  (annual, semiannual, etc.) and an "effective" or "nominal" basis.
- Internally everything is converted to the effective annual rate and,
  when needed, to the equivalent monthly rate.
"""

from typing import Optional

#: Number of periods per year for each compounding period.
PERIODS = {
    "annual": 1,
    "semiannual": 2,
    "quarterly": 4,
    "bimonthly": 6,
    "monthly": 12,
    "weekly": 52,
    "daily": 365,
}


def effective_annual_rate(rate: float, period: str = "annual", basis: str = "effective") -> float:
    """Convert a (rate, period, basis) triple to the effective annual rate.

    - "effective" basis: the rate already belongs to its own period
      (compounded). E.g.: 1% monthly -> r_year = (1.01)**12 - 1.
    - "nominal" basis: the rate is a nominal annual rate; the per-period
      rate is rate/periods and the effective annual rate follows from
      compounding. E.g.: 13% p.a. nominal with monthly compounding ->
      (1 + 0.13/12)**12 - 1.
    """
    k = PERIODS.get(period)
    if k is None:
        raise ValueError(f"Invalid compounding period: {period!r}")
    rate = float(rate)
    if basis == "nominal":
        return (1.0 + rate / k) ** k - 1.0
    return (1.0 + rate) ** k - 1.0


def equivalent_monthly_rate(annual_rate: float) -> float:
    """Monthly rate equivalent to a given effective annual rate."""
    return (1.0 + float(annual_rate)) ** (1.0 / 12.0) - 1.0


def equivalent_annual_rate(period_rate: float, periods_per_year: int) -> float:
    """Effective annual rate equivalent to a (compounded) per-period rate."""
    return (1.0 + float(period_rate)) ** periods_per_year - 1.0


def effective_periodic_rate(annual_rate: float, periods_per_year: int) -> float:
    """Effective per-period rate equivalent to an effective annual rate."""
    return (1.0 + float(annual_rate)) ** (1.0 / periods_per_year) - 1.0


def lump_sum_future_value(principal: float, annual_rate: float, term_months: int) -> float:
    """Future value of a lump-sum deposit compounded over term_months."""
    return float(principal) * (1.0 + float(annual_rate)) ** (float(term_months) / 12.0)


def arrears_series_factor(monthly_rate: float, n_months: int) -> float:
    """Accumulation factor of a level in-arrears series of n deposits.

    Sums (1+i)^t for t = 0 .. n-1. The last deposit earns no interest.
    """
    if abs(float(monthly_rate)) < 1e-14:
        return float(n_months)
    return ((1.0 + monthly_rate) ** n_months - 1.0) / monthly_rate


def arrears_series_future_value(pmt: float, monthly_rate: float, n_months: int) -> float:
    """Future value of equal monthly (in-arrears) deposits over n months."""
    return float(pmt) * arrears_series_factor(monthly_rate, n_months)


def discounted_series_factor(monthly_rate: float, n_months: int) -> float:
    """Sum of (1+i)^(-t) for t = 1 .. n (series discount factor)."""
    if abs(float(monthly_rate)) < 1e-14:
        return float(n_months)
    q = 1.0 / (1.0 + monthly_rate)
    return q * (1.0 - q ** n_months) / (1.0 - q)


def cashflow_irr(
    cashflows,
    lo: float = -0.9999,
    hi: float = 10.0,
    points: int = 6000,
) -> Optional[float]:
    """Internal rate of return (per period) of a cash flow series.

    Returns the per-period rate that zeroes the NPV. Prefers the positive
    root (the economic return of the investment); when no positive root
    exists, returns the negative root closest to zero if there is one.
    Returns None when no root exists in the interval.
    """
    import numpy as np

    cashflows = np.asarray(cashflows, dtype=float)
    if cashflows.size < 2:
        return None

    def npv(r):
        t = np.arange(cashflows.size)
        return float(np.sum(cashflows / (1.0 + r) ** t))

    from scipy.optimize import brentq

    def _find(lo_r, hi_r):
        xs = np.linspace(lo_r, hi_r, points)
        ys = np.array([npv(x) for x in xs])
        for i in range(1, len(xs)):
            if ys[i - 1] == 0.0:
                return float(xs[i - 1])
            if ys[i - 1] * ys[i] < 0.0:
                try:
                    root = brentq(npv, xs[i - 1], xs[i], xtol=1e-12, rtol=1e-12)
                except Exception:
                    return None
                if np.isfinite(root):
                    return float(root)
        return None

    positive_root = _find(0.0, hi)
    if positive_root is not None:
        return positive_root
    return _find(max(lo, -1.0 + 1e-6), 0.0)


def hurdle_from_indicators(risk_free: float, inflation: float) -> float:
    """Minimum attractive (hurdle) rate as a real rate: (1+risk_free)/(1+inflation) - 1.

    Use the US policy/risk-free rate and consumer inflation, e.g.
    the Fed funds rate + CPI.
    """
    inflation = float(inflation)
    if (1.0 + inflation) <= 0.0:
        raise ValueError("Invalid inflation.")
    return (1.0 + float(risk_free)) / (1.0 + inflation) - 1.0
