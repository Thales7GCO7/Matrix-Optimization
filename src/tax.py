"""Taxes and administrative fees applied to investments.

Generic net-value logic (works for any investment type):

.. code-block:: text

    gross_gain  = gross_amount - total_contributed
    tax         = tax_on_gain(resolve_tax_rate(...), gross_gain)
    fee         = admin_fee_amount(fee_mode, fee_percent, ...)
    net_amount  = gross_amount - tax - fee
    net_profit  = net_amount - total_contributed

Income-tax specs (``tax_mode`` + ``tax_percent`` + optional ``brackets``):

- ``"exempt"``: no taxation (e.g. municipal bonds, Roth IRA qualified
  withdrawals). ``tax_percent`` and ``brackets`` are ignored.
- ``"fixed"``: a single flat rate on the gross gain (e.g. federal
  capital-gains rates entered by the user: short-term marginal bracket
  or long-term 0%/15%/20%).
- ``"brackets"``: a progressive/regressive table selected by holding
  period or gain size. ``brackets`` is a list of ``(limit, rate)`` pairs
  sorted ascending; the first ``limit`` that covers the lookup value
  wins, otherwise the last rate wins. Two lookup keys are supported:

  - ``("term", months)``: e.g. regressive tables ``[(6, 0.225),
    (12, 0.20), (24, 0.175), (inf, 0.15)]``;
  - ``("gain", amount)``: e.g. progressive brackets on the gain.

  Any other ``mode`` falls back to 0.0 (no tax) so unknown future
  investment types never crash the computation.

Administrative-fee specs (``fee_mode`` + ``fee_percent``):

- ``"none"``: no fee.
- ``"contribution"``: one-off ``fee_percent`` of deposits (front loads).
- ``"assets"``: ``fee_percent`` p.a. on assets under management
  (mutual-fund/ETF expense ratios), applied geometrically over the term.
- ``"gain"``: ``fee_percent`` of the gross gain (performance fee).

Use :func:`compute_net_amount` as the single generic entry point and
:func:`explain_net_calculation` when the front-end needs to show the
formulas, variables, and per-asset numeric steps.
"""

from typing import Any, Dict, List, Optional, Sequence, Tuple

TAX_MODES = ["exempt", "fixed"]
#: Extended modes accepted by the generic resolver (superset of TAX_MODES).
#: Kept separate so the legacy ``TAX_MODES`` constant stays stable.
EXTENDED_TAX_MODES = ["exempt", "fixed", "brackets"]
FEE_MODES = ["none", "contribution", "assets", "gain"]


def tax_rate(mode: str, fixed_percent: Optional[float] = None) -> float:
    """Effective income-tax rate (0 for exempt / fixed=None)."""
    if mode == "exempt":
        return 0.0
    if mode == "fixed":
        return float(fixed_percent if fixed_percent is not None else 0.0)
    return 0.0


def resolve_tax_rate(
    mode: str,
    fixed_percent: Optional[float] = None,
    brackets: Optional[Sequence[Tuple[float, float]]] = None,
    bracket_key: str = "term",
    lookup_value: float = 0.0,
) -> float:
    """Effective income-tax rate for any investment type.

    - ``exempt``/``fixed`` behave exactly like :func:`tax_rate`.
    - ``brackets`` picks the rate from a ``[(limit, rate), ...]`` table
      using ``lookup_value`` (term in months when ``bracket_key="term"``,
      gross gain when ``bracket_key="gain"``). Unknown modes return 0.0.
    """
    if mode == "brackets":
        return _bracket_rate(brackets, lookup_value)
    return tax_rate(mode, fixed_percent)


def _bracket_rate(
    brackets: Optional[Sequence[Tuple[float, float]]], lookup_value: float
) -> float:
    if not brackets:
        return 0.0
    try:
        ordered = sorted(brackets, key=lambda b: b[0])
    except Exception:
        return 0.0
    value = float(lookup_value)
    for limit, rate in ordered:
        try:
            if value <= float(limit):
                return float(rate)
        except Exception:
            continue
    try:
        return float(ordered[-1][1])
    except Exception:
        return 0.0


def tax_on_gain(rate: float, gross_gain: float) -> float:
    """Tax in currency units on the gross gain (losses are not taxed)."""
    if gross_gain <= 0.0:
        return 0.0
    return float(rate) * float(gross_gain)


def admin_fee_amount(
    mode: str,
    percent: float,
    gross_amount: float,
    gross_gain: float,
    total_contributed: float,
    term_months: int,
) -> float:
    """Administrative fee in currency units for the configured mode."""
    if mode == "none" or percent <= 0.0:
        return 0.0
    pct = float(percent)
    if mode == "contribution":
        return pct * float(total_contributed)
    if mode == "assets":
        years = float(term_months) / 12.0
        return float(gross_amount) * (1.0 - (1.0 - pct) ** years)
    if mode == "gain":
        return pct * max(float(gross_gain), 0.0)
    return 0.0


def compute_net_amount(
    gross_amount: float,
    total_contributed: float,
    tax_mode: str = "exempt",
    tax_percent: float = 0.0,
    fee_mode: str = "none",
    fee_percent: float = 0.0,
    term_months: int = 12,
    brackets: Optional[Sequence[Tuple[float, float]]] = None,
    bracket_key: str = "term",
) -> Dict[str, float]:
    """Generic net-value computation for any investment type.

    Applies, in order: ``gross_gain = gross - contributed``,
    ``tax = rate * max(gain, 0)``, ``fee = f(mode, ...)``,
    ``net = gross - tax - fee``, ``profit = net - contributed``.
    """
    gross = float(gross_amount)
    contributed = float(total_contributed)
    gross_gain = gross - contributed
    lookup = float(term_months) if bracket_key == "term" else max(gross_gain, 0.0)
    rate = resolve_tax_rate(tax_mode, tax_percent, brackets, bracket_key, lookup)
    income_tax = tax_on_gain(rate, gross_gain)
    fee = admin_fee_amount(
        fee_mode, fee_percent, gross, gross_gain, contributed, int(term_months)
    )
    net_amount = gross - income_tax - fee
    return {
        "gross_amount": gross,
        "total_contributed": contributed,
        "gross_gain": gross_gain,
        "tax_rate": float(rate),
        "tax": float(income_tax),
        "fee": float(fee),
        "net_amount": float(net_amount),
        "net_profit": float(net_amount - contributed),
    }


def describe_calculation_logic() -> Dict[str, Any]:
    """Static description of the generic formulas, functions, and variables.

    Returned verbatim by the API (``calculation_logic``) and rendered by
    the front-end, so the UI always documents the exact logic in code.
    """
    return {
        "pipeline": [
            "gross_amount = lump_sum_gross(A) + monthly_series_gross(P)",
            "gross_gain = gross_amount - total_contributed, where total_contributed = A + P * term_months",
            "tax_rate = resolve_tax_rate(tax_mode, tax_percent[, brackets])",
            "tax = tax_rate * max(gross_gain, 0)  [losses are not taxed]",
            "fee = admin_fee_amount(fee_mode, fee_percent, gross_amount, gross_gain, total_contributed, term_months)",
            "net_amount = gross_amount - tax - fee",
            "net_profit = net_amount - total_contributed",
        ],
        "functions": [
            {
                "name": "lump_sum_gross / monthly_series_gross",
                "module": "src/instruments.py",
                "role": "Compounds deposits at the asset's effective annual rate to the redemption month (gross, before deductions).",
            },
            {
                "name": "resolve_tax_rate",
                "module": "src/tax.py",
                "role": "Maps any tax spec to one effective rate: exempt -> 0, fixed -> flat %, brackets -> table lookup by term or gain.",
            },
            {
                "name": "tax_on_gain",
                "module": "src/tax.py",
                "role": "Converts the rate to currency: rate * gain, or 0 when gain <= 0.",
            },
            {
                "name": "admin_fee_amount",
                "module": "src/tax.py",
                "role": "Converts any fee spec to currency: contribution (% of deposits), assets (% p.a. geometric), gain (% of gain).",
            },
            {
                "name": "compute_net_amount",
                "module": "src/tax.py",
                "role": "Single generic entry point chaining the steps above; used by every asset type including the hurdle reserve.",
            },
        ],
        "variables": [
            {"name": "A", "meaning": "Lump-sum initial deposit allocated today."},
            {"name": "P", "meaning": "Recurring monthly deposit (in arrears)."},
            {"name": "term_months", "meaning": "Months until redemption; also sizes the fee horizon and bracket lookup."},
            {"name": "gross_amount", "meaning": "Accumulated value before tax/fees."},
            {"name": "total_contributed", "meaning": "Cash actually deposited: A + P * term_months."},
            {"name": "gross_gain", "meaning": "gross_amount - total_contributed; the only tax/fee base tied to profit."},
            {"name": "tax_mode / tax_percent", "meaning": "Investment's tax spec: exempt | fixed % on gains | brackets table."},
            {"name": "fee_mode / fee_percent", "meaning": "Investment's fee spec: none | contribution | assets (% p.a.) | gain."},
            {"name": "net_amount", "meaning": "Final spendable wealth: gross - tax - fee."},
            {"name": "net_profit", "meaning": "net_amount - total_contributed; maximized by the optimizer."},
        ],
    }


def explain_net_calculation(
    gross_amount: float,
    total_contributed: float,
    tax_mode: str = "exempt",
    tax_percent: float = 0.0,
    fee_mode: str = "none",
    fee_percent: float = 0.0,
    term_months: int = 12,
    brackets: Optional[Sequence[Tuple[float, float]]] = None,
    bracket_key: str = "term",
    asset_name: str = "Asset",
) -> Dict[str, Any]:
    """Per-asset numeric walkthrough of the generic net-value logic."""
    res = compute_net_amount(
        gross_amount, total_contributed, tax_mode, tax_percent,
        fee_mode, fee_percent, term_months, brackets, bracket_key,
    )
    if tax_mode == "exempt":
        tax_formula = "tax = 0 (exempt)"
    elif tax_mode == "brackets":
        tax_formula = (
            f"tax = brackets_lookup({bracket_key}={res['tax_rate']:.4g} rate) * "
            f"max(gain, 0) = {res['tax']:.2f}"
        )
    else:
        tax_formula = (
            f"tax = {res['tax_rate']:.4g} * max({res['gross_gain']:.2f}, 0)"
            f" = {res['tax']:.2f}"
        )
    if fee_mode == "contribution":
        fee_formula = f"fee = {float(fee_percent):.4g} * contributed = {res['fee']:.2f}"
    elif fee_mode == "assets":
        fee_formula = (
            f"fee = gross * (1 - (1 - {float(fee_percent):.4g})^({float(term_months)/12.0:.4g}y))"
            f" = {res['fee']:.2f}"
        )
    elif fee_mode == "gain":
        fee_formula = f"fee = {float(fee_percent):.4g} * max(gain, 0) = {res['fee']:.2f}"
    else:
        fee_formula = "fee = 0 (none)"
    steps: List[str] = [
        f"{asset_name}: contributed = A + P*n = {res['total_contributed']:.2f}",
        f"{asset_name}: gross_gain = {res['gross_amount']:.2f} - {res['total_contributed']:.2f} = {res['gross_gain']:.2f}",
        f"{asset_name}: {tax_formula}",
        f"{asset_name}: {fee_formula}",
        f"{asset_name}: net_amount = {res['gross_amount']:.2f} - {res['tax']:.2f} - {res['fee']:.2f} = {res['net_amount']:.2f}",
        f"{asset_name}: net_profit = {res['net_amount']:.2f} - {res['total_contributed']:.2f} = {res['net_profit']:.2f}",
    ]
    return {**res, "asset": asset_name, "tax_formula": tax_formula,
            "fee_formula": fee_formula, "steps": steps}
