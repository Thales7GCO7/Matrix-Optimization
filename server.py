"""Servidor FastAPI do Otimizador de Investimentos.

Rotas:
- GET  /                pagina HTML (front-end unico)
- GET  /api/exemplos    carteira de exemplo para preencher o formulario
- POST /api/otimizar    recebe cenario + ativos e devolve alocacao, indices e graficos
"""

import webbrowser
from dataclasses import asdict
from pathlib import Path
from threading import Timer
from typing import Any, Dict, List, Optional

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse

from src.instruments import Ativo
from src.performance import IndicadoresAtivo, IndicadoresCarteira
from src.portfolio_optimizer import PortfolioOptimizer

from web import graficos
from web.schema import OtimizarRequest, para_ativo, calcular_tma, inflacao_usada

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "web" / "static"

app = FastAPI(title="Otimizador de Investimentos", version="1.0.0")


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/exemplos")
def exemplos() -> Dict[str, Any]:
    from web.schema import ATIVOS_EXEMPLO

    return {"ativos": ATIVOS_EXEMPLO}


@app.post("/api/otimizar")
def otimizar(req: OtimizarRequest):
    try:
        ativos = [para_ativo(p) for p in req.ativos]
    except ValueError as exc:
        return JSONResponse(status_code=422, content={"erro": str(exc)})

    tma = calcular_tma(req)
    inflacao = inflacao_usada(req)
    usar_mensal = req.usar_mensal and req.aporte_mensal > 0

    res = PortfolioOptimizer(
        ativos,
        capital_inicial=req.capital,
        tma_anual=tma,
        inflacao_anual=inflacao,
        aporte_mensal=req.aporte_mensal,
        usar_aporte_mensal=usar_mensal,
    ).resolver()

    if res.erro:
        return JSONResponse(status_code=422, content={"erro": res.erro})

    return _resposta(res)


def _resposta(res) -> Dict[str, Any]:
    c = res.carteira
    assert c is not None
    total_inicial = sum(i.aporte_inicial for i in res.indicadores)
    total_mensal = sum(i.aporte_mensal for i in res.indicadores)

    avisos: List[str] = []
    if c.ganho_adicional <= 0 and c.capital_aplicado > 0:
        avisos.append(
            "A carteira aplicada rende menos que o capital mantido na TMA. "
            "Considere rever as taxas liquidas dos ativos."
        )
    if c.alfa is not None and c.alfa <= 0 and c.capital_aplicado > 0:
        avisos.append("O retorno anualizado da carteira nao supera a TMA (alfa <= 0).")

    return {
        "erro": None,
        "cenario": {
            "capital_inicial": res.capital_inicial,
            "aporte_mensal_disponivel": res.aporte_mensal_disponivel,
            "tma_pct": res.tma_anual * 100.0,
            "inflacao_pct": res.inflacao_anual * 100.0,
        },
        "carteira": _carteira_dict(c),
        "uso": {
            "capital_aplicado": total_inicial,
            "aportes_mensais": total_mensal,
            "reserva": c.reserva,
            "ganho_adicional": c.ganho_adicional,
            "lucro_tma": c.lucro_tma,
        },
        "indicadores": [_indicador_dict(i) for i in res.indicadores],
        "alocacoes": [
            {
                "nome": a.ativo.nome,
                "label": a.ativo.label(),
                "aporte_inicial": a.aporte_inicial,
                "aporte_mensal": a.aporte_mensal,
                "reserva": a.reserva,
            }
            for a in res.alocacoes
        ],
        "graficos": {
            "alocacao": graficos.grafico_alocacao(res),
            "patrimonio": graficos.grafico_evolucao_patrimonio(res),
            "lucro_tma": graficos.grafico_lucro_versus_tma(res),
        },
        "avisos": avisos,
    }


def _carteira_dict(c: IndicadoresCarteira) -> Dict[str, Any]:
    d = asdict(c)
    return d


def _indicador_dict(i: IndicadoresAtivo) -> Dict[str, Any]:
    d = {k: v for k, v in asdict(i).items() if k != "projecao"}
    return d


if __name__ == "__main__":
    import os
    import sys

    import uvicorn

    port = int(os.environ.get("PORT", "8000"))
    Timer(1.5, lambda: webbrowser.open(f"http://localhost:{port}")).start()
    uvicorn.run(app if "--reload" not in sys.argv else "server:app", host="0.0.0.0", port=port)