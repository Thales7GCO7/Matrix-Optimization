import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import streamlit as st

from main import EXEMPLOS_SISTEMAS_NAO_LINEARES, EXEMPLOS_OTIMIZACAO
from src.expression_parser import parse_expression, parse_multiple_expressions
from src.gaussian_elimination import GaussJordan
from src.investment_optimizer import (
    InvestmentOptimizer,
    default_portfolio,
    make_expreturn,
    make_logreturn,
    make_powerreturn,
    make_quadreturn,
)
from src.nonlinear_optimizer import NonlinearOptimizer
from src.nonlinear_solver import NewtonRaphson
from src.simplex import SimplexSolver
from web import forms, graficos, parsers, render

st.set_page_config(page_title="Matrix Optimization", page_icon=":triangular_ruler:", layout="wide")

TIPOS_RETORNO = {
    "L": ("Logaritmica  a*ln(x+c)", make_logreturn),
    "E": ("Exponencial  a*(1-e^(-bx))", make_expreturn),
    "P": ("Potencia  a*x^p", make_powerreturn),
    "Q": ("Quadratica  a*x - b*x^2", make_quadreturn),
}

EXEMPLO_GAUSS_2x2 = [[1, 2, 5], [3, 4, 11]]
EXEMPLO_GAUSS_3x3 = [[2, 1, -1, 8], [-3, -1, 2, -11], [-2, 1, 2, -3]]

EXEMPLOS_SIMPLEX = {
    "max z = 3x1 + 5x2 (2x1<=4, 2x2<=12, 3x1+2x2<=18)": {
        "c": [3, 5], "A": [[1, 0], [0, 2], [3, 2]], "b": [4, 6, 18],
    },
    "max z = 2x1 + 3x2 + x3 (x1+x2+x3<=10, 2x1+3x2+2x3<=15)": {
        "c": [2, 3, 1], "A": [[1, 1, 1], [2, 3, 2]], "b": [10, 15],
    },
}

TIPOS_LABEL = {t: v[0] for t, v in TIPOS_RETORNO.items()}


def main():
    st.sidebar.title("Matrix Optimization")
    st.sidebar.markdown("Escolha um modulo para comecar.")
    paginas = {
        "Inicio": pagina_inicio,
        "1. Gauss-Jordan": pagina_gauss,
        "2. Simplex": pagina_simplex,
        "3. Newton-Raphson": pagina_newton,
        "4. Otimizacao nao linear": pagina_otimizacao,
        "5. Portfolio de investimentos": pagina_investimento,
    }
    escolha = st.sidebar.radio("Modulos", list(paginas))
    paginas[escolha]()
    st.sidebar.markdown("---")
    st.sidebar.caption(
        "Dica: matrizes aceitam fracoes (ex: `1/3`). "
        "Para iniciar, digite `streamlit run app.py`."
    )


def pagina_inicio():
    render.explicacao("inicio")


def _seed_grid(prefix: str, valores, chave_m=None, chave_n=None, m=None, n=None):
    if chave_m is not None:
        st.session_state[chave_m] = m
    if chave_n is not None:
        st.session_state[chave_n] = n
    for i, row in enumerate(valores):
        for j, v in enumerate(row):
            st.session_state[f"{prefix}_{i}_{j}"] = str(v)


def _seed_vector(prefix: str, valores):
    for j, v in enumerate(valores):
        st.session_state[f"{prefix}_{j}"] = str(v)


def pagina_gauss():
    render.explicacao("gauss")

    ex1, ex2 = st.columns(2)
    if ex1.button("Carregar exemplo 2x2", help="x1 + 2x2 = 5  e  3x1 + 4x2 = 11", key="gauss_ex1"):
        _seed_grid("gauss_cell", EXEMPLO_GAUSS_2x2, "gauss_m", "gauss_n", 2, 2)
    if ex2.button("Carregar exemplo 3x3", help="Sistema clasico 3x3", key="gauss_ex2"):
        _seed_grid("gauss_cell", EXEMPLO_GAUSS_3x3, "gauss_m", "gauss_n", 3, 3)

    c1, c2 = st.columns(2)
    m = forms.number_field("Numero de equacoes (m)", key="gauss_m", default=2)
    n = forms.number_field("Numero de variaveis (n)", key="gauss_n", default=2)

    st.subheader("Matriz aumentada [A | b]")
    with st.form("form_gauss"):
        st.markdown("Preencha cada linha: **n coeficientes + termo independente**. Ex.: `2 1 8` = $2x_1 + x_2 = 8$.")
        cells = forms.grid_cells("gauss_cell", m, n + 1)
        submitted = st.form_submit_button("Resolver sistema")

    if submitted:
        matriz, err = parsers.parse_grid(cells, m, n + 1)
        if err:
            st.error(err)
        else:
            gj = GaussJordan(matriz)
            gj.solve()
            render.render_gauss(gj)


def pagina_simplex():
    render.explicacao("simplex")

    sel_col, btn_col = st.columns([2, 1])
    exemplo = sel_col.selectbox(
        "Carregar exemplo?", [None] + list(EXEMPLOS_SIMPLEX),
        format_func=lambda k: k or "— (entrada manual)", key="simp_ex_sel",
    )
    if btn_col.button("Carregar", key="simp_ex_btn", disabled=exemplo is None):
        if exemplo:
            data = EXEMPLOS_SIMPLEX[exemplo]
            _seed_grid("simp_A", data["A"], "simp_n", "simp_m", len(data["c"]), len(data["b"]))
            _seed_vector("simp_c", data["c"])
            _seed_vector("simp_b", data["b"])

    c1, c2 = st.columns(2)
    n = forms.number_field("Numero de variaveis (n)", key="simp_n", default=2)
    m = forms.number_field("Numero de restricoes (m)", key="simp_m", default=3)

    with st.form("form_simplex"):
        st.markdown("**Vetor de custos c** (lucro por unidade de cada variavel):")
        c_cells = forms.vector_cells("simp_c", n)
        st.markdown("**Matriz de coeficientes A** ($m \\times n$):")
        A_cells = forms.grid_cells("simp_A", m, n)
        st.markdown("**Vetor de limites b** (disponibilidade de cada recurso):")
        b_cells = forms.vector_cells("simp_b", m)
        submitted = st.form_submit_button("Resolver pelo Simplex")

    if submitted:
        c_vec, err1 = parsers.parse_vector(c_cells, n)
        A_mat, err2 = parsers.parse_grid(A_cells, m, n)
        b_vec, err3 = parsers.parse_vector(b_cells, m)
        erro = next((e for e in (err1, err2, err3) if e), "")
        if erro:
            st.error(erro)
        else:
            solver = SimplexSolver(c_vec, A_mat, b_vec)
            solver.solve()
            render.render_simplex(solver)
            if n == 2:
                fig = graficos.grafico_simplex(
                    [[float(v) for v in row] for row in A_mat],
                    [float(v) for v in b_vec],
                    [float(v) for v in c_vec],
                    [float(v) for v in solver.optimal_solution] if solver.optimal_solution else None,
                    float(solver.optimal_value) if solver.optimal_value is not None else None,
                )
                if fig is not None:
                    st.pyplot(fig)
            else:
                st.info("Grafico da regiao viavel disponivel apenas para 2 variaveis.")


def pagina_newton():
    render.explicacao("newton")

    modo = st.radio("Modo de entrada:", ["Entrada manual", "Exemplo predefinido"], horizontal=True, key="newt_modo")

    solver = None
    resultado = None

    if modo == "Exemplo predefinido":
        nomes = {k: v["nome"] for k, v in EXEMPLOS_SISTEMAS_NAO_LINEARES.items()}
        escolha = st.selectbox("Sistema:", list(nomes), format_func=lambda k: f"[{k}] {nomes[k]}", key="newt_ex_sel")
        if st.button("Resolver exemplo", key="newt_ex_run"):
            ex = EXEMPLOS_SISTEMAS_NAO_LINEARES[escolha]
            funcs = parse_multiple_expressions(ex["exprs"], len(ex["x0"]))
            solver = NewtonRaphson(func=lambda x: [f(x) for f in funcs], x0=ex["x0"])
            solver.solve()
            resultado = (solver, funcs)
    else:
        n = forms.number_field("Numero de variaveis (n)", key="newt_n", default=1, max_value=10)
        with st.form("form_newton"):
            exprs = forms.expression_fields("newt", n, "Expressao F_i (igualada a zero)")
            x0_txt = st.text_input("Chute inicial x0 (valores separados por espaco)", value="1", key="newt_x0")
            t1, t2, t3 = st.columns(3)
            tol = t1.number_input("Tolerancia", min_value=1e-15, max_value=1.0, value=1e-12, format="%.1e", key="newt_tol")
            max_iter = int(t2.number_input("Max iteracoes", min_value=1, max_value=500, value=200, key="newt_max"))
            ls = t3.checkbox("Line search (amortecido)", value=True, key="newt_ls")
            submitted = st.form_submit_button("Resolver")

        if submitted:
            if any(not e.strip() for e in exprs):
                st.error("Preencha todas as expressoes.")
            else:
                x0v, err = parsers.parse_float_sequence(x0_txt, n)
                if err:
                    st.error(err)
                else:
                    try:
                        funcs = parse_multiple_expressions(exprs, n)
                    except ValueError as exc:
                        st.error(str(exc))
                        return
                    solver = NewtonRaphson(
                        func=lambda x: [f(x) for f in funcs],
                        x0=x0v,
                        tol=float(tol),
                        max_iter=max_iter,
                        line_search=ls,
                    )
                    solver.solve()
                    resultado = (solver, funcs)

    if resultado is not None:
        solver, funcs = resultado
        render.render_newton(solver)
        if solver.solution is not None:
            if solver.is_scalar:
                fig1 = graficos.grafico_newton_escalar(funcs[0], float(solver.x0[0]), float(solver.solution[0]))
                if fig1 is not None:
                    st.pyplot(fig1)
            fig2 = graficos.grafico_convergencia(solver.norms)
            if fig2 is not None:
                st.pyplot(fig2)


def pagina_otimizacao():
    render.explicacao("otimizacao")

    modo = st.radio("Modo de entrada:", ["Entrada manual", "Exemplo predefinido"], horizontal=True, key="opt_modo")

    solver = None
    figura = None

    if modo == "Exemplo predefinido":
        nomes = {k: v["nome"] for k, v in EXEMPLOS_OTIMIZACAO.items()}
        escolha = st.selectbox("Problema:", list(nomes), format_func=lambda k: f"[{k}] {nomes[k]}", key="opt_ex_sel")
        if st.button("Resolver exemplo", key="opt_ex_run"):
            ex = EXEMPLOS_OTIMIZACAO[escolha]
            f_obj = parse_expression(ex["objetivo"], ex["n"])
            constraints = [
                {"type": "eq", "fun": lambda x, g=parse_expression(e, ex["n"]): [g(x)]}
                for e in ex["eq"]
            ] + [
                {"type": "ineq", "fun": lambda x, g=parse_expression(e, ex["n"]): [g(x)]}
                for e in ex["ineq"]
            ]
            solver = NonlinearOptimizer(
                objective=f_obj,
                x0=ex["x0"],
                bounds=ex["bounds"],
                constraints=constraints if constraints else None,
                maximize=ex["maximizar"],
                method="SLSQP",
            )
            solver.solve()
            if ex["n"] == 2 and solver.solution is not None:
                figura = graficos.grafico_contorno(f_obj, ex["x0"], solver.solution)
    else:
        n = forms.number_field("Numero de variaveis (n)", key="opt_n", default=2, max_value=10)
        with st.form("form_otimizacao"):
            objetivo = st.text_input(
                "Funcao objetivo (use x1, x2, ...)",
                value="-x1**2 - x2**2 + 4*x1 + 6*x2",
                key="opt_obj",
            )
            opcao_tipo = st.radio("Tipo:", ["Maximizar", "Minimizar"], horizontal=True, key="opt_tipo")
            c1, c2 = st.columns(2)
            n_eq = int(c1.number_input("Restricoes de igualdade (g=0)", min_value=0, max_value=10, value=0, key="opt_n_eq"))
            n_ineq = int(c2.number_input("Restricoes de desigualdade (h>=0)", min_value=0, max_value=10, value=0, key="opt_n_ineq"))
            eq = forms.expression_fields("opt_eq", n_eq, "Igualdade g_i")
            ineq = forms.expression_fields("opt_ineq", n_ineq, "Desigualdade h_i")
            usar_bounds = st.checkbox("Definir limites por variavel", value=True, key="opt_bounds_on")
            low, up = None, None
            if usar_bounds:
                low, up = forms.bounds_fields("opt_bounds", n)
            x0_txt = st.text_input(
                "Chute inicial x0",
                value=" ".join(["1"] * n),
                key="opt_x0",
            )
            submitted = st.form_submit_button("Otimizar")

        if submitted:
            try:
                f_obj = parse_expression(objetivo, n)
            except (SyntaxError, ValueError) as exc:
                st.error(f"Expressao invalida: {objetivo!r} ({exc})")
                return
            x0v, err = parsers.parse_float_sequence(x0_txt, n)
            if err:
                st.error(err)
                return
            eq_l, ineq_l = [], []
            for e in eq:
                if e.strip():
                    eq_l.append(parse_expression(e, n))
                else:
                    st.error("Preencha ou apague todas as igualdades.")
                    return
            for h in ineq:
                if h.strip():
                    ineq_l.append(parse_expression(h, n))
                else:
                    st.error("Preencha ou apague todas as desigualdades.")
                    return
            bounds, err_b = parsers.parse_bounds(low or [], up or [], n) if usar_bounds else (None, "")
            if err_b:
                st.error(err_b)
                return
            constraints = [
                {"type": "eq", "fun": lambda x, g=g: [g(x)]} for g in eq_l
            ] + [
                {"type": "ineq", "fun": lambda x, g=g: [g(x)]} for g in ineq_l
            ]
            solver = NonlinearOptimizer(
                objective=f_obj,
                x0=x0v,
                bounds=bounds,
                constraints=constraints if constraints else None,
                maximize=opcao_tipo == "Maximizar",
                method="SLSQP",
            )
            solver.solve()
            if n == 2 and solver.solution is not None:
                figura = graficos.grafico_contorno(f_obj, x0v, solver.solution)

    if solver is not None:
        render.render_otimizacao(solver)
        if figura is not None:
            st.pyplot(figura)
        else:
            st.info("Grafico de contorno disponivel apenas para 2 variaveis.")


def pagina_investimento():
    render.explicacao("investimento")

    budget = st.number_input("Orcamento total B", min_value=0.0, value=10000.0, step=100.0, key="inv_budget")
    modo = st.radio("Modo de entrada:", ["Portfolio de exemplo", "Portfolio manual"], horizontal=True, key="inv_modo")

    if modo == "Portfolio de exemplo":
        if st.button("Otimizar portfolio de exemplo", key="inv_ex_run"):
            opt = InvestmentOptimizer(return_functions=default_portfolio(), budget=float(budget), method="SLSQP")
            opt.solve()
            render.render_investimento(opt)
            fig = graficos.grafico_alocacao(opt)
            if fig is not None:
                st.pyplot(fig)
    else:
        n = forms.number_field("Numero de investimentos", key="inv_n", default=4, max_value=20)
        with st.form("form_invest"):
            funcs = []
            upper_texts = []
            for i in range(n):
                with st.container():
                    st.markdown(f"**Investimento {i + 1}**")
                    col_t, col_p = st.columns([1, 3])
                    tipo = col_t.selectbox(
                        "Tipo", list(TIPOS_RETORNO), index=0,
                        format_func=lambda t: TIPOS_RETORNO[t][0], key=f"inv_tipo_{i}",
                        label_visibility="collapsed",
                    )
                    pa, pb, pc, pd = col_p.columns(4)
                    if tipo == "L":
                        a = pa.number_input("a", value=40.0, key=f"inv_pa_{i}")
                        c = pb.number_input("c", value=1.0, min_value=0.0, key=f"inv_pc_{i}")
                        funcs.append(make_logreturn(a, c))
                    elif tipo == "E":
                        a = pa.number_input("a", value=60.0, key=f"inv_pa_{i}")
                        b = pb.number_input("b", value=0.05, key=f"inv_pb_{i}")
                        funcs.append(make_expreturn(a, b))
                    elif tipo == "P":
                        a = pa.number_input("a", value=10.0, key=f"inv_pa_{i}")
                        p = pb.number_input("p (0<p<=1)", value=0.5, min_value=0.01, max_value=1.0, key=f"inv_pp_{i}")
                        funcs.append(make_powerreturn(a, p))
                    else:
                        a = pa.number_input("a", value=0.08, key=f"inv_pa_{i}")
                        b = pb.number_input("b", value=2e-5, key=f"inv_pb_{i}")
                        funcs.append(make_quadreturn(a, b))
                    upper_texts.append(
                        col_p.text_input(
                            label=f"limite sup {i + 1}", value="",
                            key=f"inv_up_{i}", label_visibility="collapsed",
                        )
                    )
            submitted = st.form_submit_button("Otimizar portfolio")

        if submitted:
            upper = []
            ok = True
            for i, txt in enumerate(upper_texts):
                v = txt.strip()
                if not v:
                    upper.append(budget)
                else:
                    try:
                        upper.append(float(v))
                    except ValueError:
                        st.error(f"Limite superior invalido para investimento {i + 1}: '{txt}'.")
                        ok = False
                        break
            if ok:
                opt = InvestmentOptimizer(
                    return_functions=funcs,
                    budget=float(budget),
                    upper_bounds=upper,
                    method="SLSQP",
                )
                opt.solve()
                render.render_investimento(opt)
                fig = graficos.grafico_alocacao(opt)
                if fig is not None:
                    st.pyplot(fig)


if __name__ == "__main__":
    main()