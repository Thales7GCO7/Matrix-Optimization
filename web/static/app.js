"use strict";
/* Utilitários compartilhados, chamadas à API, estado e renderização dos resultados (ambas as páginas). */

const PERIODOS = ["anual","semestral","trimestral","bimestral","mensal","semanal","diaria"];
const ROTULO_PERIODO = {anual:"Anual", semestral:"Semestral", trimestral:"Trimestral", bimestral:"Bimestral",
  mensal:"Mensal", semanal:"Semanal", diaria:"Diária"};
const IMPOSTO = {isento:"Isento", fixo:"Alíquota % sobre ganhos"};
const TAXA = {nenhuma:"Sem taxa", aporte:"% dos aportes", patrimonio:"% a.a. do patrimônio",
  ganho:"% dos ganhos"};
const BASE = {efetiva:"Efetiva", nominal:"Nominal"};

const ATIVO_PADRAO = {
  nome:"", rentabilidade_pct:10.0, periodo:"anual", base:"efetiva", prazo_meses:12,
  modo_imposto:"isento", imposto_pct:0.0, modo_taxa:"nenhuma", taxa_pct:0.0,
  minimo_inicial:0.0, maximo_inicial:0.0, usa_mensal:false, maximo_mensal:0.0,
};

const CENARIO_PADRAO = {
  capital_inicial:10000, usar_mensal:true, aporte_mensal:500,
  modo_taxa_minima:"auto", taxa_livre_risco_pct:15.0, inflacao_pct:5.0, taxa_minima_manual_pct:10.0,
};

const CHAVE_ESTADO = "estadoOtimizador";
/* Incremente quando o formato do resultado/gráficos armazenado mudar, para que
   resultados antigos em cache sejam reotimizados em vez de renderizados. */
const VERSAO_ESTADO = 6;

const $ = (id) => document.getElementById(id);
const fmt = (v, d=2) => v == null ? "-" : Number(v).toLocaleString("pt-BR", {minimumFractionDigits:d, maximumFractionDigits:d});
const fmtPct = (v, d=2) => v == null ? "-" : (v*100).toLocaleString("pt-BR", {minimumFractionDigits:d, maximumFractionDigits:d}) + "%";

function no(tag, attrs={}, filhos=[]) {
  const el = document.createElement(tag);
  for (const [k,v] of Object.entries(attrs)) {
    if (k === "class") el.className = v;
    else if (k === "text") el.textContent = v;
    else if (k === "html") el.innerHTML = v;
    else if (k in el && typeof el[k] !== "function") el[k] = v;
    else if (v != null) el.setAttribute(k, v);
  }
  for (const c of filhos) el.appendChild(typeof c === "string" ? document.createTextNode(c) : c);
  return el;
}

function opcoes(mapa, val) {
  return Object.entries(mapa).map(([k,l]) => no("option", {value:k, text:l, selected: k===val}));
}
function campo(cls, tipo, valor, extra={}) {
  return no("input", Object.assign({type:tipo, class:cls, value:valor}, extra));
}

function carregarEstado() {
  try {
    const bruto = localStorage.getItem(CHAVE_ESTADO);
    if (bruto) {
      const s = JSON.parse(bruto);
      if (s.v === VERSAO_ESTADO) return s;
    }
  } catch (e) { /* ignora estado corrompido */ }
  return {v: VERSAO_ESTADO, cenario:{...CENARIO_PADRAO}, ativos:[], resultado:null};
}

function salvarEstado(estado) {
  try { localStorage.setItem(CHAVE_ESTADO, JSON.stringify({...estado, v: VERSAO_ESTADO})); } catch (e) { /* armazenamento cheio/bloqueado */ }
}

async function buscarExemplos() {
  const r = await fetch("/api/exemplos");
  const j = await r.json();
  return j.ativos.map((x) => ({...x}));
}

async function executarOtimizacao(cenario, ativos) {
  const payload = {
    capital_inicial: Number(cenario.capital_inicial),
    usar_mensal: Boolean(cenario.usar_mensal),
    aporte_mensal: Number(cenario.aporte_mensal),
    modo_taxa_minima: cenario.modo_taxa_minima,
    taxa_livre_risco_pct: Number(cenario.taxa_livre_risco_pct),
    inflacao_pct: Number(cenario.inflacao_pct),
    taxa_minima_manual_pct: Number(cenario.taxa_minima_manual_pct),
    ativos,
  };
  const r = await fetch("/api/otimizar", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(payload),
  });
  const j = await r.json();
  if (!r.ok) {
    throw new Error(j.erro ||
      (Array.isArray(j.detail) ? j.detail.map((d) => d.msg).join("; ") : (j.detail || "Erro desconhecido")));
  }
  return j;
}

function criarMetrica(rotulo, valor, formatador) {
  return no("div", {class:"metrica"}, [
    no("div", {class:"k", text:rotulo}),
    no("div", {class:"v", text:formatador(valor)}),
  ]);
}

function tabela(cabecalho, linhas) {
  const t = no("table");
  t.appendChild(no("thead", {}, [no("tr", {}, cabecalho.map((h) => no("th", {text:h})))]));
  const tb = no("tbody");
  for (const r of linhas) tb.appendChild(no("tr", {}, r.map((cel) => no("td", {text: cel}))));
  t.appendChild(tb);
  return t;
}

/* Renderiza uma resposta do /api/otimizar no DOM do painel. */
function renderizarResultado(j) {
  const {carteira:c, cenario, uso, metricas, graficos, avisos} = j;
  $("erro").innerHTML = "";

  $("avisos").innerHTML = "";
  (avisos||[]).forEach((w) => $("avisos").appendChild(no("div", {class:"banner", text:w})));

  const l1 = $("metricas-l1"); l1.innerHTML = "";
  l1.appendChild(criarMetrica("Capital total do plano", c.capital_investido, fmt));
  l1.appendChild(criarMetrica("Reserva (taxa mínima)", c.reserva, fmt));
  l1.appendChild(criarMetrica("Riqueza líquida final", c.valor_liquido, fmt));
  l1.appendChild(criarMetrica("Lucro líquido", c.lucro_liquido, fmt));
  l1.appendChild(criarMetrica("ROI", c.roi, fmtPct));

  const l2 = $("metricas-l2"); l2.innerHTML = "";
  l2.appendChild(criarMetrica("ROI anualizado (TIR)", c.roi_anualizado, fmtPct));
  l2.appendChild(criarMetrica("VPL", c.vpl, fmt));
  l2.appendChild(criarMetrica("Alpha sobre a taxa mínima", c.alpha, fmtPct));
  l2.appendChild(criarMetrica("Taxa mínima usada", cenario.taxa_minima_pct, (v) => fmt(v) + "%"));
  l2.appendChild(criarMetrica("Linha da taxa mínima (mesmo fluxo)", c.lucro_taxa_minima, fmt));

  const ul = no("ul", {}, [
    no("li", {text:`Capital inicial: ${fmt(uso.capital_investido)} de ${fmt(cenario.capital_inicial)} disponíveis`}),
  ]);
  if (cenario.mensal_disponivel > 0)
    ul.appendChild(no("li", {text:`Aportes mensais: ${fmt(uso.aportes_mensais)} de ${fmt(cenario.mensal_disponivel)} disponíveis`}));
  ul.appendChild(no("li", {text:`Reserva: ${fmt(uso.reserva)} (rendendo a taxa mínima de ${fmt(cenario.taxa_minima_pct)}%)`}));
  ul.appendChild(no("li", {text:`Lucro excedente vs. taxa mínima: ${fmt(uso.lucro_excedente)}`}));
  ul.appendChild(no("li", {text:`Se todo o capital tivesse ficado na taxa mínima, o lucro seria ${fmt(c.lucro_taxa_minima)}.`}));
  $("uso").innerHTML = "";
  $("uso").appendChild(ul);

  const cab = ["Ativo","Inicial (R$)","Mensal (R$)","Riqueza líq. (R$)","Lucro (R$)","ROI","ROI a.a.","VPL (R$)","TIR a.a.","Payback","IL","Alpha"];
  const linhasDes = metricas.map((i) => [
    i.eh_reserva ? i.nome + " ↗" : i.nome,
    fmt(i.aporte_inicial), fmt(i.aporte_mensal), fmt(i.valor_liquido), fmt(i.lucro_liquido),
    fmtPct(i.roi), fmtPct(i.roi_anualizado), fmt(i.vpl), fmtPct(i.tir_anual),
    i.payback_simples != null ? `${(i.payback_simples|0)}m / ${(i.payback_descontado|0)}m` : "s/r",
    i.indice_lucratividade != null ? fmt(i.indice_lucratividade) : "-",
    fmtPct(i.alpha),
  ]);
  $("tbl-desempenho").replaceChildren(tabela(cab, linhasDes));
  $("tbl-desempenho-legenda").textContent = "Payback em meses (simples/descontado). ↗ = reserva na taxa mínima. 's/r' = o prazo não recupera o capital.";

  const pct = (x) => Number.isFinite(x) ? (x*100).toLocaleString("pt-BR",{maximumFractionDigits:1}) + "%" : "-";
  const cabDed = ["Ativo","Ganho bruto (R$)","Imposto de renda (R$)","Alíquota","Taxa adm. (R$)"];
  const linhasDed = metricas.map((i) => [i.nome, fmt(i.ganho_bruto), fmt(i.imposto), pct(i.aliquota), fmt(i.taxa)]);
  $("tbl-deducoes").replaceChildren(tabela(cabDed, linhasDed));

  const definirImg = (id, uri) => { const img = $(id); img.src = uri || ""; img.hidden = !uri; };
  definirImg("g-evolucao", graficos.evolucao);
  definirImg("g-pizza", graficos.alocacao_pizza);
  definirImg("g-alocacao", graficos.alocacao);
  definirImg("g-lucro", graficos.lucro_vs_taxa_minima);
  definirImg("g-pl", graficos.pl_max);

  renderizarLogicaCalculo(j);
  renderizarModeloPL(j);
}

/* Renderiza a resolução do PL de 2 ativos: objetivo, funções de lucro,
   restrições, tabela de vértices, tangente/ótimo e passos do solver.
   Não faz nada em páginas sem a seção #modelo-pl. */
function renderizarModeloPL(j) {
  const secao = $("modelo-pl");
  if (!secao) return;
  const m = j.modelo_pl;
  secao.innerHTML = "";
  if (!m || !m.viavel) {
    secao.appendChild(no("p", {class:"hint", text:
      (m && m.motivo) ? ("Plano do PL indisponível: " + m.motivo)
                      : "Plano do PL indisponível para este cenário (é preciso capital e ao menos um ativo)."}));
    return;
  }
  secao.appendChild(no("p", {}, [
    document.createTextNode("Plano dos dois ativos mais eficientes — "),
    no("b", {text:`x1 = ${m.ativo_x}`}), document.createTextNode(", "),
    no("b", {text:`x2 = ${m.ativo_y}`}), document.createTextNode("."),
  ]));
  secao.appendChild(no("p", {}, [no("b", {text:"Objetivo: "}), no("code", {text: m.objetivo})]));
  secao.appendChild(no("p", {}, [no("b", {text:"Tangente (isolinha ótima): "}), no("code", {text: m.tangente})]));

  secao.appendChild(no("h3", {text:"Fórmulas dos investimentos (lucro líquido por R$ 1)"}));
  (m.funcoes_lucro || []).forEach((f) => {
    secao.appendChild(no("p", {}, [no("b", {text: f.ativo + ": "}), no("code", {text: f.formula})]));
  });

  secao.appendChild(no("h3", {text:"Restrições (retas)"}));
  const cl = no("ul", {});
  (m.restricoes || []).forEach((c) => cl.appendChild(no("li", {}, [no("code", {text: c})])));
  secao.appendChild(cl);

  secao.appendChild(no("h3", {text:"Vértices — Z avaliado em cada um"}}));
  const cabV = ["Vértice", "x1 (R$)", "x2 (R$)", "Z (R$)", "Status"];
  const linhasV = (m.vertices || []).map((v) => [
    v.rotulo, fmt(v.x1), fmt(v.x2), fmt(v.z),
    v.otimo ? (m.otimo_aresta ? "ÓTIMO (aresta)" : "ÓTIMO") : "—",
  ]);
  secao.appendChild(tabela(cabV, linhasV));

  secao.appendChild(no("h3", {text:"Resolução — como os valores das variáveis são encontrados"}}));
  const ol = no("ol", {});
  (m.passos || []).forEach((s) => ol.appendChild(no("li", {}, [no("code", {text: s})])));
  secao.appendChild(ol);
  secao.appendChild(no("p", {class:"hint", text: m.observacao || ""}));
  secao.appendChild(no("p", {class:"hint", text:
    `Alocação gulosa efetiva nestes eixos: x1=${fmt(m.efetiva.x1)}, x2=${fmt(m.efetiva.x2)}.`}));
}

/* Renderiza a lógica genérica de valor líquido (fórmulas, funções, variáveis)
   mais o passo a passo numérico por ativo. Não faz nada em páginas sem a
   seção #logica-calculo (ex. assets.html). */
function renderizarLogicaCalculo(j) {
  const secao = $("logica-calculo");
  if (!secao) return;
  const logica = j.logica_calculo;
  const detalhamento = j.detalhamento || [];
  secao.innerHTML = "";
  if (!logica) {
    secao.appendChild(no("p", {class:"hint", text:"Sem detalhes de cálculo nesta resposta — execute a otimização de novo."}));
    return;
  }
  secao.appendChild(no("p", {text:"Todo tipo de investimento segue o mesmo pipeline: capitalizar até o bruto, depois subtrair imposto e taxa. Líquido = bruto − imposto − taxa."}));
  const pipe = no("ol", {});
  (logica.etapas || []).forEach((etapa) => pipe.appendChild(no("li", {}, [no("code", {text: etapa})])));
  secao.appendChild(pipe);

  secao.appendChild(no("h3", {text:"Funções"}));
  const cabF = ["Função", "Módulo", "Papel"];
  const linhasF = (logica.funcoes || []).map((f) => [f.nome, f.modulo, f.papel]);
  secao.appendChild(tabela(cabF, linhasF));

  secao.appendChild(no("h3", {text:"Variáveis"}));
  const cabV = ["Variável", "Significado"];
  const linhasV = (logica.variaveis || []).map((v) => [v.nome, v.significado]);
  secao.appendChild(tabela(cabV, linhasV));

  if (detalhamento.length) {
    secao.appendChild(no("h3", {text:"Passo a passo por ativo (números efetivos)"}));
    detalhamento.forEach((b) => {
      const det = no("details", {}, [
        no("summary", {text:`${b.ativo}: líquido ${fmt(b.valor_liquido)} = bruto ${fmt(b.valor_bruto)} − imposto ${fmt(b.imposto)} − taxa ${fmt(b.taxa)}`}),
        no("div", {class:"gloss"}, [
          b.detalhe_bruto ? no("p", {}, [no("b", {text:"Bruto: "}), document.createTextNode(b.detalhe_bruto)]) : null,
          b.especificacao ? no("p", {}, [no("b", {text:"Especificação: "}),
            document.createTextNode(`imposto ${b.especificacao.modo_imposto}${b.especificacao.modo_imposto === "fixo" ? " " + (b.especificacao.imposto_pct*100).toFixed(2) + "%" : ""} · taxa ${b.especificacao.modo_taxa}${b.especificacao.modo_taxa === "nenhuma" ? "" : " " + (b.especificacao.taxa_pct*100).toFixed(3) + "%"} · ${b.especificacao.prazo_meses}m`)]) : null,
          no("p", {}, [no("b", {text:"Imposto: "}), document.createTextNode(b.formula_imposto || "")]),
          no("p", {}, [no("b", {text:"Taxa: "}), document.createTextNode(b.formula_taxa || "")]),
          no("ol", {}, (b.passos || []).map((s) => no("li", {}, [no("code", {text: s})]))),
        ].filter(Boolean)),
      ]);
      secao.appendChild(det);
    });
  }
}

function mostrarErro(msg) {
  const caixa = $("erro");
  caixa.innerHTML = "";
  caixa.appendChild(no("div", {class:"banner err", text:msg}));
}
