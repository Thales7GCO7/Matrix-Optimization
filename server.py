"""FastAPI server for the Investment Optimizer.

Routes:
- GET  /                dashboard (main front-end page)
- GET  /assets          asset data entry + optimization page
- GET  /api/examples    sample portfolio to fill in the form
- POST /api/optimize    receives a scenario + assets and returns allocation, metrics, and charts
"""

import webbrowser
from dataclasses import asdict
from pathlib import Path
from threading import Timer
from typing import Any, Dict, List

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from src.instruments import Asset, lump_sum_gross, monthly_series_gross
from src.performance import AssetMetrics, PortfolioMetrics
from src.portfolio_optimizer import PortfolioOptimizer
from src import tax as tax_logic
from src import lp_geometry

from web import charts
from web.schema import OptimizeRequest, to_asset, resolve_hurdle_rate, resolve_inflation

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "web" / "static"

app = FastAPI(title="Investment Optimizer", version="1.0.0")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/assets", include_in_schema=False)
def assets_page() -> FileResponse:
    return FileResponse(STATIC_DIR / "assets.html")


@app.get("/api/examples")
def examples() -> Dict[str, Any]:
    from web.schema import EXAMPLE_ASSETS

    return {"assets": EXAMPLE_ASSETS}


@app.post("/api/optimize")
def optimize(req: OptimizeRequest):
    try:
        assets = [to_asset(p) for p in req.assets]
    except ValueError as exc:
        return JSONResponse(status_code=422, content={"error": str(exc)})

    hurdle = resolve_hurdle_rate(req)
    inflation = resolve_inflation(req)
    use_monthly = req.use_monthly and req.monthly_contrib > 0

    res = PortfolioOptimizer(
        assets,
        initial_capital=req.capital,
        hurdle_annual=hurdle,
        inflation_annual=inflation,
        monthly_contrib=req.monthly_contrib,
        use_monthly=use_monthly,
    ).solve()

    if res.error:
        return JSONResponse(status_code=422, content={"error": res.error})

    return _build_response(res)


def _lp_payload(res) -> Dict[str, Any]:
    """2-asset LP projection: chart + full model (formulas, resolution)."""
    model = lp_geometry.build_lp_model(res)
    if model is None:
        return {"chart": None, "model": None}
    if not model.feasible:
        return {"chart": None,
                "model": {"feasible": False, "reason": model.reason}}
    return {"chart": charts.lp_max_chart(model),
            "model": lp_geometry.describe_lp_model(model)}


def _build_response(res) -> Dict[str, Any]:
    c = res.portfolio
    assert c is not None
    total_initial = sum(i.initial_contrib for i in res.metrics)
    total_monthly = sum(i.monthly_contrib for i in res.metrics)
    lp = _lp_payload(res)

    warnings: List[str] = []
    if c.excess_profit <= 0 and c.invested_capital > 0:
        warnings.append(
            "The invested portfolio earns less than the capital kept at the hurdle rate. "
            "Consider reviewing the assets' net rates."
        )
    if c.alpha is not None and c.alpha <= 0 and c.invested_capital > 0:
        warnings.append("The portfolio annualized return does not beat the hurdle rate (alpha <= 0).")

    return {
        "error": None,
        "scenario": {
            "initial_capital": res.initial_capital,
            "available_monthly": res.available_monthly,
            "hurdle_pct": res.hurdle_annual * 100.0,
            "inflation_pct": res.inflation_annual * 100.0,
        },
        "portfolio": _portfolio_dict(c),
        "usage": {
            "invested_capital": total_initial,
            "monthly_contribs": total_monthly,
            "reserve": c.reserve,
            "excess_profit": c.excess_profit,
            "hurdle_profit": c.hurdle_profit,
        },
        "metrics": [_metric_dict(i) for i in res.metrics],
        "allocations": [
            {
                "name": a.asset.name,
                "label": a.asset.label(),
                "initial_contrib": a.initial_contrib,
                "monthly_contrib": a.monthly_contrib,
                "is_reserve": a.is_reserve,
            }
            for a in res.allocations
        ],
        "charts": {
            "allocation": charts.allocation_chart(res),
            "allocation_pie": charts.allocation_pie_chart(res),
            "equity": charts.equity_growth_chart(res),
            "profit_vs_hurdle": charts.profit_vs_hurdle_chart(res),
            "lp_max": lp["chart"],
        },
        "lp_model": lp["model"],
        "calculation_logic": tax_logic.describe_calculation_logic(),
        "breakdown": _breakdown_from_result(res),
        "warnings": warnings,
    }


def _portfolio_dict(c: PortfolioMetrics) -> Dict[str, Any]:
    d = asdict(c)
    return d


def _metric_dict(i: AssetMetrics) -> Dict[str, Any]:
    d = {k: v for k, v in asdict(i).items() if k != "projection"}
    return d


def _breakdown_from_result(res) -> List[Dict[str, Any]]:
    """Per-asset numeric walkthrough of the generic net-value logic."""
    by_name = {a.name: a for a in (res.assets or [])}
    out: List[Dict[str, Any]] = []
    for m in res.metrics:
        asset = by_name.get(m.name)
        if asset is None:
            explanation = tax_logic.explain_net_calculation(
                m.gross_amount, m.total_contributed, asset_name=m.name,
            )
        else:
            explanation = tax_logic.explain_net_calculation(
                m.gross_amount, m.total_contributed,
                tax_mode=asset.tax_mode, tax_percent=asset.tax_percent,
                fee_mode=asset.fee_mode, fee_percent=asset.fee_percent,
                term_months=asset.term_months,
                brackets=asset.tax_brackets, bracket_key=asset.tax_bracket_key,
                asset_name=asset.name,
            )
            explanation["gross_detail"] = (
                f"gross = lump_sum({m.initial_contrib:.2f})"
                f" + series({m.monthly_contrib:.2f}/mo x {asset.term_months}m)"
                f" = {m.gross_amount:.2f}"
            )
            explanation["spec"] = {
                "tax_mode": asset.tax_mode,
                "tax_percent": asset.tax_percent,
                "fee_mode": asset.fee_mode,
                "fee_percent": asset.fee_percent,
                "term_months": asset.term_months,
            }
        out.append(explanation)
    return out


if __name__ == "__main__":
    import os
    import sys

    import uvicorn

    port = int(os.environ.get("PORT", "8000"))
    Timer(1.5, lambda: webbrowser.open(f"http://localhost:{port}")).start()
    uvicorn.run(app if "--reload" not in sys.argv else "server:app", host="0.0.0.0", port=port)
