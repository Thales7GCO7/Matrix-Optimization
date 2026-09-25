"""Contrato de dados da API e conversão para o modelo de domínio.

O front-end (HTML/JS) envia um JSON com o cenário e a lista de
ativos; este módulo valida o payload (pydantic) e o converte para
o modelo de domínio em `src.instrumentos.Ativo`, usado pelo otimizador.
"""

from typing import List

from pydantic import BaseModel, Field, field_validator

from src.instrumentos import Ativo, BASES_TAXA
from src.matematica_financeira import PERIODOS, taxa_minima_por_indicadores

TIPOS_IMPOSTO = ("isento", "fixo")
TIPOS_TAXA = ("nenhuma", "aporte", "patrimonio", "ganho")
PERIODOS_UI = list(PERIODOS)

#: Benchmarks brasileiros editáveis (taxa Selic e inflação IPCA,
#: em % a.a.). Valores ilustrativos, não cotações ao vivo.
BR_PADROES = {"taxa_livre_risco_pct": 15.0, "inflacao_pct": 5.0}

ATIVOS_EXEMPLO: List[dict] = [
    {
        "nome": "Tesouro Selic 15% a.a.",
        "rentabilidade_pct": 15.0, "periodo": "anual", "base": "efetiva", "prazo_meses": 24,
        "modo_imposto": "fixo", "imposto_pct": 20.0,
        "modo_taxa": "nenhuma", "taxa_pct": 0.0,
        "minimo_inicial": 0.0, "maximo_inicial": 5000.0,
        "usa_mensal": True, "maximo_mensal": 300.0,
    },
    {
        "nome": "CDB 13,5% a.a.",
        "rentabilidade_pct": 13.5, "periodo": "anual", "base": "efetiva", "prazo_meses": 36,
        "modo_imposto": "fixo", "imposto_pct": 20.0,
        "modo_taxa": "nenhuma", "taxa_pct": 0.0,
        "minimo_inicial": 0.0, "maximo_inicial": 3000.0,
        "usa_mensal": True, "maximo_mensal": 100.0,
    },
    {
        "nome": "LCI isenta 11,5% a.a.",
        "rentabilidade_pct": 11.5, "periodo": "anual", "base": "efetiva", "prazo_meses": 24,
        "modo_imposto": "isento", "imposto_pct": 0.0,
        "modo_taxa": "nenhuma", "taxa_pct": 0.0,
        "minimo_inicial": 0.0, "maximo_inicial": 2500.0,
        "usa_mensal": True, "maximo_mensal": 200.0,
    },
    {
        "nome": "Fundo DI (taxa adm. 0,5% a.a.)",
        "rentabilidade_pct": 14.0, "periodo": "anual", "base": "efetiva", "prazo_meses": 12,
        "modo_imposto": "fixo", "imposto_pct": 20.0,
        "modo_taxa": "patrimonio", "taxa_pct": 0.5,
        "minimo_inicial": 1000.0, "maximo_inicial": 2000.0,
        "usa_mensal": True, "maximo_mensal": 100.0,
    },
]


class PayloadAtivo(BaseModel):
    nome: str = Field(min_length=1, max_length=120)
    rentabilidade_pct: float = 0.0
    periodo: str = "anual"
    base: str = "efetiva"
    prazo_meses: int = Field(gt=0, le=600)
    modo_imposto: str = "isento"
    imposto_pct: float = Field(default=0.0, ge=0.0, le=100.0)
    modo_taxa: str = "nenhuma"
    taxa_pct: float = Field(default=0.0, ge=0.0, le=100.0)
    minimo_inicial: float = Field(default=0.0, ge=0.0)
    maximo_inicial: float = Field(default=0.0, ge=0.0)
    usa_mensal: bool = False
    maximo_mensal: float = Field(default=0.0, ge=0.0)

    @field_validator("periodo")
    @classmethod
    def _periodo_ok(cls, v: str) -> str:
        if v not in PERIODOS:
            raise ValueError(f"Período inválido: {v!r}. Use {list(PERIODOS)}.")
        return v

    @field_validator("base")
    @classmethod
    def _base_ok(cls, v: str) -> str:
        if v not in BASES_TAXA:
            raise ValueError(f"Base inválida: {v!r}.")
        return v

    @field_validator("modo_imposto")
    @classmethod
    def _imposto_ok(cls, v: str) -> str:
        if v not in TIPOS_IMPOSTO:
            raise ValueError(f"Tipo de imposto inválido: {v!r}.")
        return v

    @field_validator("modo_taxa")
    @classmethod
    def _taxa_ok(cls, v: str) -> str:
        if v not in TIPOS_TAXA:
            raise ValueError(f"Tipo de taxa inválido: {v!r}.")
        return v

    @field_validator("rentabilidade_pct")
    @classmethod
    def _rentabilidade_ok(cls, v: float) -> float:
        if v <= -100.0:
            raise ValueError("A rentabilidade deve ser maior que -100%.")
        return v


class PedidoOtimizacao(BaseModel):
    capital_inicial: float = Field(default=10000.0, ge=0.0)
    usar_mensal: bool = True
    aporte_mensal: float = Field(default=0.0, ge=0.0)
    modo_taxa_minima: str = "auto"
    taxa_livre_risco_pct: float = Field(default=15.0, ge=0.0)
    inflacao_pct: float = Field(default=5.0, ge=0.0)
    taxa_minima_manual_pct: float = Field(default=10.0, ge=0.0)
    ativos: List[PayloadAtivo]

    @field_validator("modo_taxa_minima")
    @classmethod
    def _modo_minima_ok(cls, v: str) -> str:
        if v not in ("auto", "manual"):
            raise ValueError("modo_taxa_minima deve ser 'auto' ou 'manual'.")
        return v


def para_ativo(p: PayloadAtivo) -> Ativo:
    """Converte um payload para o modelo de domínio Ativo."""
    return Ativo(
        nome=p.nome.strip() or "Ativo",
        taxa=p.rentabilidade_pct / 100.0,
        periodo=p.periodo,
        base=p.base,
        prazo_meses=p.prazo_meses,
        modo_imposto=p.modo_imposto,
        imposto_pct=p.imposto_pct / 100.0,
        modo_taxa=p.modo_taxa,
        taxa_pct=p.taxa_pct / 100.0,
        minimo_inicial=p.minimo_inicial,
        maximo_inicial=p.maximo_inicial if p.maximo_inicial > 0 else None,
        usa_mensal=p.usa_mensal,
        maximo_mensal=p.maximo_mensal if p.maximo_mensal > 0 else None,
    )


def resolver_taxa_minima(req: PedidoOtimizacao) -> float:
    """Determina a taxa mínima anual a partir do modo escolhido no payload."""
    if req.modo_taxa_minima == "auto":
        return taxa_minima_por_indicadores(req.taxa_livre_risco_pct / 100.0, req.inflacao_pct / 100.0)
    return req.taxa_minima_manual_pct / 100.0


def resolver_inflacao(req: PedidoOtimizacao) -> float:
    """Inflação anual usada no retorno real."""
    return req.inflacao_pct / 100.0
