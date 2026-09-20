# Investment Optimizer

A web app (FastAPI + HTML page) that **allocates capital across fixed-return
assets** accounting for per-period rates, income tax, management fees, and the
**opportunity cost** (hurdle rate), computing performance metrics such as ROI,
NPV, IRR, payback, and the profitability index.

## Overview

The problem: given **available capital** today and (optionally) a **monthly
budget**, distribute the money across assets with different traits to maximize
**final net wealth** (after tax and management fees).

Mathematically it is a bounded linear-programming problem, since actual income
is **proportional to capital**. The optimal solution is found by **greedy
selection**: invest first in the assets with the highest **annualized net
return** (after deductions), honoring each asset's minimum and maximum limits.
Leftover capital, or capital no asset can place above the hurdle rate, stays in
a **reserve** earning exactly the minimum rate.

```
max Σ Lᵢ(xᵢ)          Lᵢ = final net wealth of asset i
s.t. Σ xᵢ ≤ B         available initial capital
     Σ pᵢ ≤ B_monthly  available monthly deposits
     ℓᵢ ≤ xᵢ ≤ uᵢ     per-asset limits
```

## Asset model

Each asset is defined by:

- **Name** and **min/max** (initial) capital plus a **monthly max**;
- **Rate** for the period with a **basis**:
  - *Effective*: the rate of the period itself (compounded). E.g.: 1% monthly ≈ 12.68% p.a.
  - *Nominal*: annual rate split across the period. E.g.: 13% p.a. nominal with monthly
    compounding uses 13%/12 = 1.083% per month.
- **Compounding period**: annual, semiannual, quarterly, bimonthly, monthly (weekly, daily);
- **Term to redemption** (months);
- **Income tax** on gains (generic rate entered per asset): `exempt` (e.g. US
  municipal bonds, Roth IRA qualified withdrawals) or `fixed` flat percent
  (e.g. federal capital-gains rates: short-term marginal bracket or
  long-term 0%/15%/20%);
- **Management fee**: on deposits, **% p.a. of assets** (fund management fee),
  or on gains (performance fee).

There are two deposit flows, combinable per asset:

- **Lump-sum initial deposit** — allocation of today's available capital;
- **Recurring monthly deposit** (in arrears) — level series to redemption.

## Hurdle rate (minimum attractive rate)

The hurdle rate is the **opportunity cost** of capital. It can be:

- entered manually; or
- computed as a **real rate**: `hurdle = (1 + risk_free)/(1 + inflation) - 1`,
  defaulting to Fed funds + CPI editable benchmarks.

It is used as:

- the **NPV** discount rate;
- the **alpha** benchmark (excess return over the hurdle);
- the **reserve** rate (leftovers earn the hurdle);
- the basis for **discounted payback** and the "profit vs. hurdle" comparison.

## Performance metrics

Computed **per asset** and **for the portfolio**:

| Metric | Definition |
|--------|-----------|
| **ROI** | `net profit / invested capital` (period return) |
| **Annualized ROI** | equivalent per-year return (CAGR/IRR), comparable across terms |
| **Real return** | net annual return discounted by inflation (CPI) |
| **NPV** | present value of the cash flow discounted at the hurdle (`> 0` adds value) |
| **IRR** | per-year rate that zeroes the NPV (`>` hurdle is desirable) |
| **Payback** | month when redemption recovers the capital (simple and discounted) |
| **PI** | `NPV / capital + 1` (`> 1` pays the opportunity cost) |
| **Alpha** | `annual ROI - hurdle` (excess over the opportunity cost) |
| **Profit at hurdle** | what the same deposit flow would earn at the minimum rate |
| **Excess profit** | `portfolio profit - profit at hurdle` |

## Run

```bash
pip install -r requirements.txt
uvicorn server:app --reload
```

(or `python server.py`, which opens the browser at `http://localhost:8000`).

On the page, configure the scenario (capital, hurdle, monthly budget), edit the
asset list (or load the sample portfolio), and click **Optimize allocation**.
Results arrive via `POST /api/optimize`; charts are rendered server-side
(matplotlib) as PNGs embedded in the JSON.

## Screenshots

> Screenshots below show earlier versions; the UI is now a two-page US-market
> app (dashboard + assets page). They remain valid for layout reference.

### Scenario and hurdle rate

<img width="1343" height="399" alt="Scenario and hurdle" src="https://github.com/user-attachments/assets/2a5a1383-dd2f-434d-b950-983723221e87" />

### Assets — example: bank CD 13% p.a. (nominal, monthly compounding)

<img width="1051" height="487" alt="Assets — bank CD 13% p.a." src="https://github.com/user-attachments/assets/5fba7a3d-3420-4bac-a28a-eecc32d814ef" />

### Example: govt bond SELIC (tax table)

<img width="1063" height="353" alt="Govt bond SELIC (tax table)" src="https://github.com/user-attachments/assets/6c816376-662e-49ed-ad94-87cafbd923ea" />

### Example: exempt bond 9.5% p.a.

<img width="1062" height="346" alt="Exempt bond 9.5% p.a." src="https://github.com/user-attachments/assets/8a560d7a-6269-411d-a06e-794cb4b05552" />

### Example: bond fund (1.5% p.a. mgmt fee)

<img width="1068" height="376" alt="Bond fund (1.5% p.a. mgmt fee)" src="https://github.com/user-attachments/assets/bc38357f-c34d-4e50-b31c-3a6fe8a4f544" />

## Demo

![Investment Optimizer demo](/videos/demo.mp4)

> 3.1 MB (compressed: 1280×720, H.264). If it does not load, see `videos/demo.mp4` in the repo.

## API

| Route | Method | Description |
|------|--------|-----------|
| `/` | GET | Dashboard (main front-end page: KPIs, pie/bar/line charts, tables) |
| `/assets` | GET | Asset data entry + scenario page (runs the optimization) |
| `/api/examples` | GET | Sample portfolio for the form (`assets[]`) |
| `/api/optimize` | POST | Receives `{capital, use_monthly, monthly_contrib, hurdle_mode, risk_free_pct, inflation_pct, hurdle_manual_pct, assets[]}` and returns allocation, per-asset metrics, portfolio, and charts |

The asset payload mirrors the form: `name`, `rate_pct`, `period`, `basis`,
`term_months`, `tax_mode`/`tax_pct`, `fee_mode`/`fee_pct`,
`initial_min`/`initial_max`, `uses_monthly`/`monthly_max`. Interactive docs at
`/docs` (OpenAPI).

`POST /api/optimize` responds with:

- **portfolio**: per-asset aggregates (`net_amount`, `roi`, `npv`, `annual_irr`,
  `payback`, `profitability_index`, `alpha`) and portfolio totals
  (`invested_capital`, `reserve`, `roi`, `annualized_roi`, `npv`,
  `hurdle_profit`);
- **metrics**: one row per asset (includes the hurdle reserve) with the monthly
  projection;
- **usage**: invested initial capital, monthly deposits, reserve, and excess
  profit vs. hurdle;
- **charts**: 5 base64 PNG images (`allocation`, `allocation_pie`, `equity`, `profit_vs_hurdle`, `lp_max`);
- **lp_model**: 2-asset LP projection — objective (`max Z = c1*x1 + c2*x2`),
  per-asset profit formulas, constraint lines, vertices with Z values,
  tangent line, optimum, actual allocation, and resolution steps;
- **warnings**: validation alerts (e.g.: no capital, minimums exceed capital).

Business and validation errors return `422` with `{"error": ...}`.

## Project layout

```
matrix-optimization/
├── server.py                      # FastAPI API (GET /, /api/examples, POST /api/optimize)
├── requirements.txt              # Dependencies
├── videos/
│   └── demo.mp4                  # Page demo (3.1 MB, 1280×720)
├── src/
│   ├── math_finance.py           # Rate conversion, compounding, series, IRR, hurdle
│   ├── tax.py                    # Generic net logic (compute_net_amount/explain) + taxes/fees
│   ├── instruments.py            # Asset model (gross → net) and monthly projection
│   ├── performance.py            # Metrics: ROI, NPV, IRR, payback, PI, alpha
│   ├── portfolio_optimizer.py    # Optimal allocation (greedy) + hurdle reserve
│   ├── lp_geometry.py            # 2-asset LP plane (constraints, vertices, optimum, tangent)
│   └── investment_optimizer.py   # Generic nonlinear allocation (scipy SLSQP)
├── web/
│   ├── __init__.py               # Empty package
│   ├── schema.py                 # API contract (pydantic) and sample portfolio
│   ├── charts.py                 # Matplotlib charts → base64 PNG
│   └── static/                   # Front-end (plain HTML/JS, no CDN):
│       ├── index.html            # Dashboard (KPIs, pie/bar/line charts, tables)
│       ├── assets.html           # Asset data entry + scenario form
│       └── app.js                # Shared helpers, API calls, result rendering
└── tests/
    ├── test_math_finance.py      # Rates, compounding, series, IRR, hurdle
    ├── test_tax.py               # Income tax and management fees
    ├── test_lp_geometry.py       # LP plane: vertices, optimum, tangent, chart
    ├── test_performance.py       # Per-asset and portfolio metrics
    ├── test_optimizer.py         # Allocation with limits, reserve, monthly deposits
    └── test_server.py            # API: examples, optimization, and errors (422)
```

## Tests

```bash
python -m unittest discover tests -v
```

Suite with 71 tests covering the calculation core (rates, taxes, series, IRR,
hurdle), the LP plane (vertices, optimum, tangent, chart), the allocation (limits, reserve, monthly deposits), and the API layer
via `TestClient` (sample portfolio, manual hurdle, and `422` errors).

## Tech stack

- Python 3.12
- NumPy / SciPy (`brentq` for IRR)
- FastAPI + Uvicorn (HTTP server)
- Matplotlib (PNG charts)
- Plain HTML/CSS/JS front-end (no framework, no CDN)
