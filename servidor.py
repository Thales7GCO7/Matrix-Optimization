"""Servidor FastAPI do Otimizador de Investimentos.

Rotas:
- GET  /                painel (página principal do front-end)
- GET  /ativos          entrada de dados dos ativos + página de otimização
- GET  /api/exemplos    carteira de exemplo para preencher o formulário
- POST /api/otimizar    recebe um cenário + ativos e retorna alocação, métricas e gráficos
"""

import webbrowser
from dataclasses import asdict
from pathlib import Path
from threading import Timer
from typing import Any, Dict, List

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from src.instrumentos import Ativo, bruto_aporte_unico, bruto_serie_mensal
from src.desempenho import MetricasAtivo, MetricasCarteira
from src.otimizador_carteira import OtimizadorCarteira
from src import impostos as logica_impostos
from src import geometria_pl

from web import graficos
from web.esquema import PedidoOtimizacao, para_ativo, resolver_taxa_minima, resolver_inflacao

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "web" / "static"

app = FastAPI(title="Otimizador de Investimentos", version="1.0.0")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
def painel() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/ativos", include_in_schema=False)
def pagina_ativos() -> FileResponse:
    return FileResponse(STATIC_DIR / "assets.html")


@app.get("/api/exemplos")
def exemplos() -> Dict[str, Any]:
    from web.esquema import ATIVOS_EXEMPLO

    return {"ativos": ATIVOS_EXEMPLO}


@app.post("/api/otimizar")
def otimizar(req: PedidoOtimizacao):
    try:
        ativos = [para_ativo(p) for p in req.ativos]
    except ValueError as exc:
        return JSONResponse(status_code=422, content={"erro": str(exc)})

    taxa_minima = resolver_taxa_minima(req)
    inflacao = resolver_inflacao(req)
    usar_mensal = req.usar_mensal and req.aporte_mensal > 0

    res = OtimizadorCarteira(
        ativos,
        capital_inicial=req.capital_inicial,
        taxa_minima_anual=taxa_minima,
        inflacao_anual=inflacao,
        aporte_mensal=req.aporte_mensal,
        usar_mensal=usar_mensal,
    ).resolver()

    if res.erro:
        return JSONResponse(status_code=422, content={"erro": res.erro})

    return _construir_resposta(res)


def _carga_pl(res) -> Dict[str, Any]:
    """Projeção do PL de 2 ativos: gráfico + modelo completo (fórmulas, resolução)."""
    modelo = geometria_pl.construir_modelo_pl(res)
    if modelo is None:
        return {"grafico": None, "modelo": None}
    if not modelo.viavel:
        return {"grafico": None,
                "modelo": {"viavel": False, "motivo": modelo.motivo}}
    return {"grafico": graficos.grafico_max_pl(modelo),
            "modelo": geometria_pl.descrever_modelo_pl(modelo)}


def _construir_resposta(res) -> Dict[str, Any]:
    c = res.carteira
    assert c is not None
    total_inicial = sum(i.aporte_inicial for i in res.metricas)
    total_mensal = sum(i.aporte_mensal for i in res.metricas)
    pl = _carga_pl(res)

    avisos: List[str] = []
    if c.lucro_excedente <= 0 and c.capital_investido > 0:
        avisos.append(
            "A carteira investida rende menos que o capital mantido na taxa mínima. "
            "Considere revisar as taxas líquidas dos ativos."
        )
    if c.alpha is not None and c.alpha <= 0 and c.capital_investido > 0:
        avisos.append("O retorno anualizado da carteira não supera a taxa mínima (alpha <= 0).")

    return {
        "erro": None,
        "cenario": {
            "capital_inicial": res.capital_inicial,
            "mensal_disponivel": res.mensal_disponivel,
            "taxa_minima_pct": res.taxa_minima_anual * 100.0,
            "inflacao_pct": res.inflacao_anual * 100.0,
        },
        "carteira": _dicionario_carteira(c),
        "uso": {
            "capital_investido": total_inicial,
            "aportes_mensais": total_mensal,
            "reserva": c.reserva,
            "lucro_excedente": c.lucro_excedente,
            "lucro_taxa_minima": c.lucro_taxa_minima,
        },
        "metricas": [_dicionario_metrica(i) for i in res.metricas],
        "alocacoes": [
            {
                "nome": a.ativo.nome,
                "rotulo": a.ativo.rotulo(),
                "aporte_inicial": a.aporte_inicial,
                "aporte_mensal": a.aporte_mensal,
                "eh_reserva": a.eh_reserva,
            }
            for a in res.alocacoes
        ],
        "graficos": {
            "alocacao": graficos.grafico_alocacao(res),
            "alocacao_pizza": graficos.grafico_pizza_alocacao(res),
            "evolucao": graficos.grafico_evolucao_patrimonio(res),
            "lucro_vs_taxa_minima": graficos.grafico_lucro_vs_taxa_minima(res),
            "pl_max": pl["grafico"],
        },
        "modelo_pl": pl["modelo"],
        "logica_calculo": logica_impostos.descrever_logica_calculo(),
        "detalhamento": _detalhamento_por_resultado(res),
        "avisos": avisos,
    }


def _dicionario_carteira(c: MetricasCarteira) -> Dict[str, Any]:
    d = asdict(c)
    return d


def _dicionario_metrica(i: MetricasAtivo) -> Dict[str, Any]:
    d = {k: v for k, v in asdict(i).items() if k != "projecao"}
    return d


def _detalhamento_por_resultado(res) -> List[Dict[str, Any]]:
    """Passo a passo numérico por ativo da lógica genérica de valor líquido."""
    por_nome = {a.nome: a for a in (res.ativos or [])}
    saida: List[Dict[str, Any]] = []
    for m in res.metricas:
        ativo = por_nome.get(m.nome)
        if ativo is None:
            explicacao = logica_impostos.explicar_calculo_liquido(
                m.valor_bruto, m.total_aportado, nome_ativo=m.nome,
            )
        else:
            explicacao = logica_impostos.explicar_calculo_liquido(
                m.valor_bruto, m.total_aportado,
                modo_imposto=ativo.modo_imposto, imposto_pct=ativo.imposto_pct,
                modo_taxa=ativo.modo_taxa, taxa_pct=ativo.taxa_pct,
                prazo_meses=ativo.prazo_meses,
                tabela=ativo.tabela_imposto, chave_tabela=ativo.chave_tabela,
                nome_ativo=ativo.nome,
            )
            explicacao["detalhe_bruto"] = (
                f"bruto = aporte_único({m.aporte_inicial:.2f})"
                f" + série({m.aporte_mensal:.2f}/mês x {ativo.prazo_meses}m)"
                f" = {m.valor_bruto:.2f}"
            )
            explicacao["especificacao"] = {
                "modo_imposto": ativo.modo_imposto,
                "imposto_pct": ativo.imposto_pct,
                "modo_taxa": ativo.modo_taxa,
                "taxa_pct": ativo.taxa_pct,
                "prazo_meses": ativo.prazo_meses,
            }
        saida.append(explicacao)
    return saida


if __name__ == "__main__":
    import os
    import sys

    import uvicorn

    porta = int(os.environ.get("PORT", "8000"))
    Timer(1.5, lambda: webbrowser.open(f"http://localhost:{porta}")).start()
    uvicorn.run(app if "--reload" not in sys.argv else "servidor:app", host="0.0.0.0", port=porta)
