"use strict";
/* Shared helpers, API calls, state, and result rendering for both pages. */

const PERIODS = ["annual","semiannual","quarterly","bimonthly","monthly","weekly","daily"];
const PERIOD_LABEL = {annual:"Annual", semiannual:"Semiannual", quarterly:"Quarterly", bimonthly:"Bimonthly",
  monthly:"Monthly", weekly:"Weekly", daily:"Daily"};
const TAX = {exempt:"Exempt", fixed:"Flat % on gains"};
const FEE = {none:"No fee", contribution:"% of deposits", assets:"% p.a. of assets",
  gain:"% of gains"};
const BASIS = {effective:"Effective", nominal:"Nominal"};

const DEFAULT_ASSET = {
  name:"", rate_pct:10.0, period:"annual", basis:"effective", term_months:12,
  tax_mode:"exempt", tax_pct:0.0, fee_mode:"none", fee_pct:0.0,
  initial_min:0.0, initial_max:0.0, uses_monthly:false, monthly_max:0.0,
};

const DEFAULT_SCENARIO = {
  capital:10000, use_monthly:true, monthly_contrib:500,
  hurdle_mode:"auto", risk_free_pct:4.0, inflation_pct:2.5, hurdle_manual_pct:5.5,
};

const STATE_KEY = "optState";
/* Bump when the stored result shape/charts change so stale cached
   results are re-optimized instead of rendered. */
const STATE_VERSION = 4;

const $ = (id) => document.getElementById(id);
const fmt = (v, d=2) => v == null ? "-" : Number(v).toLocaleString("en-US", {minimumFractionDigits:d, maximumFractionDigits:d});
const fmtPct = (v, d=2) => v == null ? "-" : (v*100).toLocaleString("en-US", {minimumFractionDigits:d, maximumFractionDigits:d}) + "%";

function el(tag, attrs={}, children=[]) {
  const node = document.createElement(tag);
  for (const [k,v] of Object.entries(attrs)) {
    if (k === "class") node.className = v;
    else if (k === "text") node.textContent = v;
    else if (k === "html") node.innerHTML = v;
    else if (k in node && typeof node[k] !== "function") node[k] = v;
    else if (v != null) node.setAttribute(k, v);
  }
  for (const c of children) node.appendChild(typeof c === "string" ? document.createTextNode(c) : c);
  return node;
}

function opts(map, val) {
  return Object.entries(map).map(([k,l]) => el("option", {value:k, text:l, selected: k===val}));
}
function inp(cls, type, value, extra={}) {
  return el("input", Object.assign({type, class:cls, value}, extra));
}

function loadState() {
  try {
    const raw = localStorage.getItem(STATE_KEY);
    if (raw) {
      const s = JSON.parse(raw);
      if (s.v === STATE_VERSION) return s;
    }
  } catch (e) { /* ignore corrupt state */ }
  return {v: STATE_VERSION, scenario:{...DEFAULT_SCENARIO}, assets:[], result:null};
}

function saveState(state) {
  try { localStorage.setItem(STATE_KEY, JSON.stringify({...state, v: STATE_VERSION})); } catch (e) { /* storage full/blocked */ }
}

async function fetchExamples() {
  const r = await fetch("/api/examples");
  const j = await r.json();
  return j.assets.map((x) => ({...x}));
}

async function runOptimization(scenario, assets) {
  const payload = {
    capital: Number(scenario.capital),
    use_monthly: Boolean(scenario.use_monthly),
    monthly_contrib: Number(scenario.monthly_contrib),
    hurdle_mode: scenario.hurdle_mode,
    risk_free_pct: Number(scenario.risk_free_pct),
    inflation_pct: Number(scenario.inflation_pct),
    hurdle_manual_pct: Number(scenario.hurdle_manual_pct),
    assets,
  };
  const r = await fetch("/api/optimize", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(payload),
  });
  const j = await r.json();
  if (!r.ok) {
    throw new Error(j.error ||
      (Array.isArray(j.detail) ? j.detail.map((d) => d.msg).join("; ") : (j.detail || "Unknown error")));
  }
  return j;
}

function mkMetric(label, value, formatter) {
  return el("div", {class:"metric"}, [
    el("div", {class:"k", text:label}),
    el("div", {class:"v", text:formatter(value)}),
  ]);
}

function tab(head, rows) {
  const t = el("table");
  t.appendChild(el("thead", {}, [el("tr", {}, head.map((h) => el("th", {text:h})))]));
  const tb = el("tbody");
  for (const r of rows) tb.appendChild(el("tr", {}, r.map((cell) => el("td", {text: cell}))));
  t.appendChild(tb);
  return t;
}

/* Renders an /api/optimize response into the dashboard DOM. */
function renderResult(j) {
  const {portfolio:c, scenario, usage, metrics, charts, warnings} = j;
  $("error").innerHTML = "";

  $("warnings").innerHTML = "";
  (warnings||[]).forEach((w) => $("warnings").appendChild(el("div", {class:"banner", text:w})));

  const r1 = $("metrics-r1"); r1.innerHTML = "";
  r1.appendChild(mkMetric("Total plan capital", c.invested_capital, fmt));
  r1.appendChild(mkMetric("Reserve (hurdle)", c.reserve, fmt));
  r1.appendChild(mkMetric("Final net wealth", c.net_amount, fmt));
  r1.appendChild(mkMetric("Net profit", c.net_profit, fmt));
  r1.appendChild(mkMetric("ROI", c.roi, fmtPct));

  const r2 = $("metrics-r2"); r2.innerHTML = "";
  r2.appendChild(mkMetric("Annualized ROI (IRR)", c.annualized_roi, fmtPct));
  r2.appendChild(mkMetric("NPV", c.npv, fmt));
  r2.appendChild(mkMetric("Alpha over hurdle", c.alpha, fmtPct));
  r2.appendChild(mkMetric("Hurdle used", scenario.hurdle_pct, (v) => fmt(v) + "%"));
  r2.appendChild(mkMetric("Hurdle line (same flow)", c.hurdle_profit, fmt));

  const ul = el("ul", {}, [
    el("li", {text:`Initial capital: ${fmt(usage.invested_capital)} of ${fmt(scenario.initial_capital)} available`}),
  ]);
  if (scenario.available_monthly > 0)
    ul.appendChild(el("li", {text:`Monthly deposits: ${fmt(usage.monthly_contribs)} of ${fmt(scenario.available_monthly)} available`}));
  ul.appendChild(el("li", {text:`Reserve: ${fmt(usage.reserve)} (earning the ${fmt(scenario.hurdle_pct)}% hurdle)`}));
  ul.appendChild(el("li", {text:`Excess profit vs hurdle: ${fmt(usage.excess_profit)}`}));
  ul.appendChild(el("li", {text:`Had all capital stayed at the hurdle, profit would be ${fmt(c.hurdle_profit)}.`}));
  $("usage").innerHTML = "";
  $("usage").appendChild(ul);

  const head = ["Asset","Initial ($)","Monthly ($)","Net wealth ($)","Profit ($)","ROI","ROI p.a.","NPV ($)","IRR p.a.","Payback","PI","Alpha"];
  const perfRows = metrics.map((i) => [
    i.is_reserve ? i.name + " ↗" : i.name,
    fmt(i.initial_contrib), fmt(i.monthly_contrib), fmt(i.net_amount), fmt(i.net_profit),
    fmtPct(i.roi), fmtPct(i.annualized_roi), fmt(i.npv), fmtPct(i.annual_irr),
    i.simple_payback != null ? `${(i.simple_payback|0)}m / ${(i.discounted_payback|0)}m` : "n/r",
    i.profitability_index != null ? fmt(i.profitability_index) : "-",
    fmtPct(i.alpha),
  ]);
  $("tbl-perf").replaceChildren(tab(head, perfRows));
  $("tbl-perf-caption").textContent = "Payback in months (simple/discounted). ↗ = hurdle reserve. 'n/r' = term does not recover capital.";

  const pct = (x) => Number.isFinite(x) ? (x*100).toLocaleString("en-US",{maximumFractionDigits:1}) + "%" : "-";
  const dedHead = ["Asset","Gross gain ($)","Income tax ($)","Rate","Mgmt fee ($)"];
  const dedRows = metrics.map((i) => [i.name, fmt(i.gross_gain), fmt(i.tax), pct(i.tax_rate), fmt(i.fee)]);
  $("tbl-ded").replaceChildren(tab(dedHead, dedRows));

  const setImg = (id, uri) => { const img = $(id); img.src = uri || ""; img.hidden = !uri; };
  setImg("g-equity", charts.equity);
  setImg("g-pie", charts.allocation_pie);
  setImg("g-alloc", charts.allocation);
  setImg("g-profit", charts.profit_vs_hurdle);
  setImg("g-lp", charts.lp_max);

  renderCalculationLogic(j);
  renderLpModel(j);
}

/* Renders the 2-asset LP resolution: objective, profit functions,
   constraints, vertices table, tangent/optimum, and solver steps.
   No-op on pages without the #lp-model section. */
function renderLpModel(j) {
  const section = $("lp-model");
  if (!section) return;
  const m = j.lp_model;
  section.innerHTML = "";
  if (!m || !m.feasible) {
    section.appendChild(el("p", {class:"hint", text:
      (m && m.reason) ? ("LP plane unavailable: " + m.reason)
                      : "LP plane unavailable for this scenario (needs capital and at least one asset)."}));
    return;
  }
  section.appendChild(el("p", {}, [
    document.createTextNode("Plane of the two most efficient assets — "),
    el("b", {text:`x1 = ${m.asset_x}`}), document.createTextNode(", "),
    el("b", {text:`x2 = ${m.asset_y}`}), document.createTextNode("."),
  ]));
  section.appendChild(el("p", {}, [el("b", {text:"Objective: "}), el("code", {text: m.objective})]));
  section.appendChild(el("p", {}, [el("b", {text:"Tangent (optimal iso-line): "}), el("code", {text: m.tangent})]));

  section.appendChild(el("h3", {text:"Investment formulas (net profit per $1)"}));
  (m.profit_functions || []).forEach((f) => {
    section.appendChild(el("p", {}, [el("b", {text: f.asset + ": "}), el("code", {text: f.formula})]));
  });

  section.appendChild(el("h3", {text:"Constraints (lines)"}));
  const cl = el("ul", {});
  (m.constraints || []).forEach((c) => cl.appendChild(el("li", {}, [el("code", {text: c})])));
  section.appendChild(cl);

  section.appendChild(el("h3", {text:"Vertices — Z evaluated at each one"}));
  const vhead = ["Vertex", "x1 ($)", "x2 ($)", "Z ($)", "Status"];
  const vrows = (m.vertices || []).map((v) => [
    v.label, fmt(v.x1), fmt(v.x2), fmt(v.z),
    v.optimal ? (m.edge_optimal ? "OPTIMAL (edge)" : "OPTIMAL") : "—",
  ]);
  section.appendChild(tab(vhead, vrows));

  section.appendChild(el("h3", {text:"Resolution — how the variable values are found"}));
  const ol = el("ol", {});
  (m.steps || []).forEach((s) => ol.appendChild(el("li", {}, [el("code", {text: s})])));
  section.appendChild(ol);
  section.appendChild(el("p", {class:"hint", text: m.note || ""}));
  section.appendChild(el("p", {class:"hint", text:
    `Actual greedy allocation on these axes: x1=${fmt(m.actual.x1)}, x2=${fmt(m.actual.x2)}.`}));
}

/* Renders the generic net-value logic (formulas, functions, variables)
   plus the per-asset numeric walkthrough. No-op on pages without the
   #calc-logic section (e.g. assets.html). */
function renderCalculationLogic(j) {
  const section = $("calc-logic");
  if (!section) return;
  const logic = j.calculation_logic;
  const breakdown = j.breakdown || [];
  section.innerHTML = "";
  if (!logic) {
    section.appendChild(el("p", {class:"hint", text:"No calculation details in this response — re-run the optimization."}));
    return;
  }
  section.appendChild(el("p", {text:"Every investment type shares one pipeline: compound to gross, then subtract tax and fee. Net = gross − tax − fee."}));
  const pipe = el("ol", {});
  (logic.pipeline || []).forEach((step) => pipe.appendChild(el("li", {}, [el("code", {text: step})])));
  section.appendChild(pipe);

  section.appendChild(el("h3", {text:"Functions"}));
  const fhead = ["Function", "Module", "Role"];
  const frows = (logic.functions || []).map((f) => [f.name, f.module, f.role]);
  section.appendChild(tab(fhead, frows));

  section.appendChild(el("h3", {text:"Variables"}));
  const vhead = ["Variable", "Meaning"];
  const vrows = (logic.variables || []).map((v) => [v.name, v.meaning]);
  section.appendChild(tab(vhead, vrows));

  if (breakdown.length) {
    section.appendChild(el("h3", {text:"Per-asset walkthrough (actual numbers)"}));
    breakdown.forEach((b) => {
      const det = el("details", {}, [
        el("summary", {text:`${b.asset}: net ${fmt(b.net_amount)} = gross ${fmt(b.gross_amount)} − tax ${fmt(b.tax)} − fee ${fmt(b.fee)}`}),
        el("div", {class:"gloss"}, [
          b.gross_detail ? el("p", {}, [el("b", {text:"Gross: "}), document.createTextNode(b.gross_detail)]) : null,
          b.spec ? el("p", {}, [el("b", {text:"Spec: "}),
            document.createTextNode(`tax ${b.spec.tax_mode}${b.spec.tax_mode === "fixed" ? " " + (b.spec.tax_percent*100).toFixed(2) + "%" : ""} · fee ${b.spec.fee_mode}${b.spec.fee_mode === "none" ? "" : " " + (b.spec.fee_percent*100).toFixed(3) + "%"} · ${b.spec.term_months}m`)]) : null,
          el("p", {}, [el("b", {text:"Tax: "}), document.createTextNode(b.tax_formula || "")]),
          el("p", {}, [el("b", {text:"Fee: "}), document.createTextNode(b.fee_formula || "")]),
          el("ol", {}, (b.steps || []).map((s) => el("li", {}, [el("code", {text: s})]))),
        ].filter(Boolean)),
      ]);
      section.appendChild(det);
    });
  }
}

function showError(msg) {
  const box = $("error");
  box.innerHTML = "";
  box.appendChild(el("div", {class:"banner err", text:msg}));
}
