"""API data contract and conversion to the domain model.

The front-end (HTML/JS) sends a JSON payload with the scenario and the
asset list; this module validates the payload (pydantic) and converts it
to the domain model in `src.instruments.Asset`, used by the optimizer.
"""

from typing import List

from pydantic import BaseModel, Field, field_validator

from src.instruments import Asset, RATE_BASES
from src.math_finance import PERIODS, hurdle_from_indicators

TAX_TYPES = ("exempt", "fixed")
FEE_TYPES = ("none", "contribution", "assets", "gain")
PERIODS_UI = list(PERIODS)

#: Editable US benchmark defaults (Fed funds rate and CPI inflation,
#: in % p.a.). Illustrative defaults, not live quotes.
US_DEFAULTS = {"risk_free_pct": 4.0, "inflation_pct": 2.5}

EXAMPLE_ASSETS: List[dict] = [
    {
        "name": "US Treasury note 4.2% p.a.",
        "rate_pct": 4.2, "period": "annual", "basis": "effective", "term_months": 24,
        "tax_mode": "fixed", "tax_pct": 22.0,
        "fee_mode": "none", "fee_pct": 0.0,
        "initial_min": 0.0, "initial_max": 5000.0,
        "uses_monthly": True, "monthly_max": 300.0,
    },
    {
        "name": "S&P 500 index fund (0.03% exp. ratio)",
        "rate_pct": 8.0, "period": "annual", "basis": "effective", "term_months": 60,
        "tax_mode": "fixed", "tax_pct": 15.0,
        "fee_mode": "assets", "fee_pct": 0.03,
        "initial_min": 0.0, "initial_max": 2500.0,
        "uses_monthly": True, "monthly_max": 200.0,
    },
    {
        "name": "US corporate bond 5.1% p.a.",
        "rate_pct": 5.1, "period": "annual", "basis": "effective", "term_months": 36,
        "tax_mode": "fixed", "tax_pct": 22.0,
        "fee_mode": "none", "fee_pct": 0.0,
        "initial_min": 0.0, "initial_max": 3000.0,
        "uses_monthly": True, "monthly_max": 100.0,
    },
    {
        "name": "US high-yield savings 4.0% p.a.",
        "rate_pct": 4.0, "period": "annual", "basis": "effective", "term_months": 12,
        "tax_mode": "fixed", "tax_pct": 22.0,
        "fee_mode": "none", "fee_pct": 0.0,
        "initial_min": 1000.0, "initial_max": 2000.0,
        "uses_monthly": True, "monthly_max": 100.0,
    },
]


class AssetPayload(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    rate_pct: float = 0.0
    period: str = "annual"
    basis: str = "effective"
    term_months: int = Field(gt=0, le=600)
    tax_mode: str = "exempt"
    tax_pct: float = Field(default=0.0, ge=0.0, le=100.0)
    fee_mode: str = "none"
    fee_pct: float = Field(default=0.0, ge=0.0, le=100.0)
    initial_min: float = Field(default=0.0, ge=0.0)
    initial_max: float = Field(default=0.0, ge=0.0)
    uses_monthly: bool = False
    monthly_max: float = Field(default=0.0, ge=0.0)

    @field_validator("period")
    @classmethod
    def _period_ok(cls, v: str) -> str:
        if v not in PERIODS:
            raise ValueError(f"Invalid period: {v!r}. Use {list(PERIODS)}.")
        return v

    @field_validator("basis")
    @classmethod
    def _basis_ok(cls, v: str) -> str:
        if v not in RATE_BASES:
            raise ValueError(f"Invalid basis: {v!r}.")
        return v

    @field_validator("tax_mode")
    @classmethod
    def _tax_ok(cls, v: str) -> str:
        if v not in TAX_TYPES:
            raise ValueError(f"Invalid tax type: {v!r}.")
        return v

    @field_validator("fee_mode")
    @classmethod
    def _fee_ok(cls, v: str) -> str:
        if v not in FEE_TYPES:
            raise ValueError(f"Invalid fee type: {v!r}.")
        return v

    @field_validator("rate_pct")
    @classmethod
    def _rate_ok(cls, v: float) -> float:
        if v <= -100.0:
            raise ValueError("Rate must be greater than -100%.")
        return v


class OptimizeRequest(BaseModel):
    capital: float = Field(default=10000.0, ge=0.0)
    use_monthly: bool = True
    monthly_contrib: float = Field(default=0.0, ge=0.0)
    hurdle_mode: str = "auto"
    risk_free_pct: float = Field(default=4.0, ge=0.0)
    inflation_pct: float = Field(default=2.5, ge=0.0)
    hurdle_manual_pct: float = Field(default=5.5, ge=0.0)
    assets: List[AssetPayload]

    @field_validator("hurdle_mode")
    @classmethod
    def _hurdle_mode_ok(cls, v: str) -> str:
        if v not in ("auto", "manual"):
            raise ValueError("hurdle_mode must be 'auto' or 'manual'.")
        return v


def to_asset(p: AssetPayload) -> Asset:
    """Convert a payload to the domain Asset model."""
    return Asset(
        name=p.name.strip() or "Asset",
        rate=p.rate_pct / 100.0,
        period=p.period,
        basis=p.basis,
        term_months=p.term_months,
        tax_mode=p.tax_mode,
        tax_percent=p.tax_pct / 100.0,
        fee_mode=p.fee_mode,
        fee_percent=p.fee_pct / 100.0,
        initial_min=p.initial_min,
        initial_max=p.initial_max if p.initial_max > 0 else None,
        uses_monthly=p.uses_monthly,
        monthly_max=p.monthly_max if p.monthly_max > 0 else None,
    )


def resolve_hurdle_rate(req: OptimizeRequest) -> float:
    """Determine the annual hurdle rate from the payload's chosen mode."""
    if req.hurdle_mode == "auto":
        return hurdle_from_indicators(req.risk_free_pct / 100.0, req.inflation_pct / 100.0)
    return req.hurdle_manual_pct / 100.0


def resolve_inflation(req: OptimizeRequest) -> float:
    """Annual inflation used for the real return."""
    return req.inflation_pct / 100.0
