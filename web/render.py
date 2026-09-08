from typing import List, Optional

import numpy as np
import streamlit as st
from fractions import Fraction

from src.utils import format_fraction
from web import explicacoes

STATUS_INFO = {
    "unica": ("success", "Solucao unica"),
    "solucao_unica": ("success", "Solucao unica"),
    "convergiu": ("success", "Convergiu"),
    "otimo": ("success", "Otimizado com sucesso"),
    "inconsistente": ("error", "Sistema inconsistente (sem solucao)"),
    "inviavel": ("error", "Problema infactivel"),
    "ilimitado": ("error", "Problema ilimitado"),
    "jacobiano_singular": ("error", "Jacobiano singular"),
    "divergente": ("error", "Divergiu"),
    "falhou": ("error", "Otimizacao falhou"),
    "infinitas_solucoes": ("warning", "Infinitas solucoes (variaveis livres)"),
    "max_iteracoes": ("warning", "Maximo de iteracoes atingido"),
    "nao_resolvido": ("info", "Nao resolvido"),
}

DEFAULT_BADGE = ("info", "Desconhecido")


def badge(status: str):
    kind, text = STATUS_INFO.get(status.split(":")[0], DEFAULT_BADGE)
    if status.startswith("erro"):
        kind, text = "error", status
    handler = {
        "success": st.success,
        "warning": st.warning,
        "error": st.error,
        "info": st.info,
    }[kind]
    handler(text)


def explicacao(tela: str):
    cont = explicacoes.obter(tela)
    st.title(cont["titulo"])
    st.markdown(cont["resumo"])
    if cont.get("formula"):
        st.latex(cont["formula"])
    if cont.get("variaveis"):
        st.subheader("Variaveis de entrada e formulas")
        for var, desc in cont["variaveis"]:
            st.markdown(f"- **{var}**: {desc}")
    if cont.get("extra"):
        st.info(cont["extra"])


def tabela_matriz(titulo: str, matriz, header: Optional[List[str]] = None):
    if not matriz:
        st.markdown(f"**{titulo}**: vazia.")
        return
    rows = [[format_fraction(val) for val in row] for row in matriz]
    st.markdown(f"**{titulo}**")
    if header:
        st.table([list(header)] + rows)
    else:
        st.table(rows)


def render_passos(steps: List[str], titulo: str = "Passos do calculo"):
    if not steps:
        return
    with st.expander(titulo, expanded=False):
        for step in steps:
            if "\n" in step:
                st.code(step)
            else:
                st.markdown(f"- {step or ''}")


def _metricas_solucao(vals, prefixo: str = "x"):
    cols = st.columns(len(vals))
    for i, (col, val) in enumerate(zip(cols, vals)):
        col.metric(f"{prefixo}{i + 1}", str(val))


def render_gauss(gj):
    badge(gj.status)
    tabela_matriz("Matriz aumentada (RREF)", gj.matrix)
    if gj.solution is not None and gj.status == "unica":
        st.subheader("Solucao")
        _metricas_solucao([format_fraction(v) for v in gj.solution])
    else:
        st.markdown("Nenhuma solucao unica a exibir para este sistema.")
    render_passos(gj.steps)


def _termo_latex(coef, var):
    if coef == 0:
        return None
    s = format_fraction(abs(coef))
    signo = "+" if coef > 0 else "-"
    return f"{signo} {s}{var}"


def render_simplex(solver):
    badge(solver.status)
    st.subheader("Problema de Programacao Linear")
    termos = [_termo_latex(c, f"x_{{{i + 1}}}") for i, c in enumerate(solver.c)]
    termos = [t for t in termos if t]
    st.latex("\\max\\,z = " + " ".join(termos).lstrip("+ "))
    st.latex("\\text{sujeito a:}")
    for i, row in enumerate(solver.A):
        ts = [_termo_latex(v, f"x_{{{j + 1}}}") for j, v in enumerate(row)]
        ts = [t for t in ts if t]
        st.latex(" ".join(ts).lstrip("+ ") + f" \\leq {format_fraction(solver.b[i])}")
    st.latex("x_j \\geq 0, \\quad j = 1, \\dots, " + str(solver.num_vars))

    if solver.optimal_value is not None:
        st.subheader("Resultado")
        st.metric("Valor otimo z*", format_fraction(solver.optimal_value))
        if solver.optimal_solution is not None:
            _metricas_solucao([format_fraction(v) for v in solver.optimal_solution])

    _render_tableau(solver)
    render_passos(solver.steps)


def _render_tableau(solver):
    if not solver.tableau:
        return
    with st.expander("Tableau", expanded=False):
        header = list(solver._var_names) + ["RHS"]
        rows = []
        for i, row in enumerate(solver.tableau):
            label = "z" if i == len(solver.tableau) - 1 else f"s{i + 1}"
            rows.append([label] + [format_fraction(v) for v in row])
        st.table([header] + rows)


def render_newton(nr):
    badge(nr.status)
    st.subheader("Resultado")
    cols = st.columns(3)
    if nr.solution is not None:
        cols[0].metric(
            "Raiz" if nr.is_scalar else "Solucao",
            f"{nr.solution[0]:.10g}" if nr.is_scalar else nr._fmt_vec(nr.solution),
        )
    else:
        cols[0].metric("Raiz", "-")
    cols[1].metric("Iteracoes", nr.iterations)
    cols[2].metric("Residuo ||F(x)||", f"{nr.residual:.3e}" if nr.residual is not None else "-")
    if nr.solution is not None and not nr.is_scalar:
        _metricas_solucao([f"{v:.10g}" for v in nr.solution])
    render_passos(nr.steps)


def render_otimizacao(opt):
    badge(opt.status)
    st.subheader("Resultado")
    if opt.solution is not None:
        _metricas_solucao([f"{v:.10g}" for v in opt.solution])
        if opt.optimal_value is not None:
            st.metric("Valor otimo z*", f"{opt.optimal_value:.10g}")
        cols = st.columns(2)
        cols[0].metric("Iteracoes", opt.iterations)
        cols[1].metric("Metodo", opt._choose_method())
        if opt.message:
            st.caption(opt.message)
    else:
        st.markdown("Falha ao encontrar solucao.")


def render_investimento(opt):
    badge(opt.status)
    st.subheader("Alocacao otima")
    if opt.allocation is not None:
        data = []
        for i, (val, f) in enumerate(zip(opt.allocation, opt.funcs)):
            pct = val / opt.budget * 100 if opt.budget > 0 else 0.0
            marg = opt.marginal_returns[i] if opt.marginal_returns is not None else 0.0
            data.append(
                [
                    f"Investimento {i + 1}",
                    f["label"],
                    f"{val:.6g}",
                    f"{pct:.2f}%",
                    f"{marg:.6g}",
                ]
            )
        st.table(
            [["Investimento", "Funcao de retorno", "Valor", "% do orcamento", "Retorno marginal"]]
            + data
        )
        st.metric("Retorno total otimo R*", f"{opt.optimal_return:.10g}" if opt.optimal_return is not None else "-")
        if opt.optimizer is not None:
            st.markdown(f"_Iteracoes do Simplex interno: {opt.optimizer.iterations}_")
    else:
        st.markdown("Falha ao encontrar alocacao.")