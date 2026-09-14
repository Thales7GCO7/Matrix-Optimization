"""Contrato de dados da API e conversao para o modelo de dominio.

O front-end (HTML/JS) envia um JSON com o cenario e a lista de ativos;
este modulo valida o payload (pydantic) e converte para o modelo do
dominio em `src.instruments.Ativo`, usado pelo otimizador.
"""

from typing import List

from pydantic import BaseModel, Field, field_validator

from src.instruments import Ativo, BASES_TAXA
from src.math_finance import PERIODOS, tma_por_indicadores

TIPOS_IMPOSTO = ("isento", "fixo", "ir_tabela")
TIPOS_ADMIN = ("nenhuma", "aporte", "patrimonio", "rendimento")
PERIODOS_UI = list(PERIODOS)

ATIVOS_EXEMPLO: List[dict] = [
    {
        "nome": "CDB 13% a.a. (nom., cap. mensal)",
        "taxa_pct": 13.0, "periodo": "mensal", "base": "nominal", "prazo_meses": 24,
        "imposto_modo": "ir_tabela", "imposto_pct": 0.0,
        "admin_modo": "nenhuma", "admin_pct": 0.0,
        "inicial_min": 0.0, "inicial_max": 5000.0,
        "usa_mensal": True, "mensal_max": 300.0,
    },
    {
        "nome": "Tesouro SELIC (IR tabela)",
        "taxa_pct": 10.4, "periodo": "anual", "base": "efetiva", "prazo_meses": 18,
        "imposto_modo": "ir_tabela", "imposto_pct": 0.0,
        "admin_modo": "nenhuma", "admin_pct": 0.0,
        "inicial_min": 0.0, "inicial_max": 2500.0,
        "usa_mensal": True, "mensal_max": 100.0,
    },
    {
        "nome": "LCI isenta 9,5% a.a.",
        "taxa_pct": 9.5, "periodo": "anual", "base": "efetiva", "prazo_meses": 12,
        "imposto_modo": "isento", "imposto_pct": 0.0,
        "admin_modo": "nenhuma", "admin_pct": 0.0,
        "inicial_min": 0.0, "inicial_max": 1500.0,
        "usa_mensal": True, "mensal_max": 100.0,
    },
    {
        "nome": "Fundo RF (taxa adm. 1,5% a.a.)",
        "taxa_pct": 11.0, "periodo": "anual", "base": "efetiva", "prazo_meses": 18,
        "imposto_modo": "ir_tabela", "imposto_pct": 0.0,
        "admin_modo": "patrimonio", "admin_pct": 1.5,
        "inicial_min": 1000.0, "inicial_max": 2000.0,
        "usa_mensal": True, "mensal_max": 100.0,
    },
]


class AtivoPayload(BaseModel):
    nome: str = Field(min_length=1, max_length=120)
    taxa_pct: float = 0.0
    periodo: str = "anual"
    base: str = "efetiva"
    prazo_meses: int = Field(gt=0, le=600)
    imposto_modo: str = "isento"
    imposto_pct: float = Field(default=0.0, ge=0.0, le=100.0)
    admin_modo: str = "nenhuma"
    admin_pct: float = Field(default=0.0, ge=0.0, le=100.0)
    inicial_min: float = Field(default=0.0, ge=0.0)
    inicial_max: float = Field(default=0.0, ge=0.0)
    usa_mensal: bool = False
    mensal_max: float = Field(default=0.0, ge=0.0)

    @field_validator("periodo")
    @classmethod
    def _periodo_ok(cls, v: str) -> str:
        if v not in PERIODOS:
            raise ValueError(f"Periodo invalido: {v!r}. Use {list(PERIODOS)}.")
        return v

    @field_validator("base")
    @classmethod
    def _base_ok(cls, v: str) -> str:
        if v not in BASES_TAXA:
            raise ValueError(f"Base invalida: {v!r}.")
        return v

    @field_validator("imposto_modo")
    @classmethod
    def _imposto_ok(cls, v: str) -> str:
        if v not in TIPOS_IMPOSTO:
            raise ValueError(f"Tipo de imposto invalido: {v!r}.")
        return v

    @field_validator("admin_modo")
    @classmethod
    def _admin_ok(cls, v: str) -> str:
        if v not in TIPOS_ADMIN:
            raise ValueError(f"Tipo de taxa administrativa invalido: {v!r}.")
        return v

    @field_validator("taxa_pct")
    @classmethod
    def _taxa_ok(cls, v: float) -> float:
        if v <= -100.0:
            raise ValueError("Taxa deve ser maior que -100%.")
        return v


class OtimizarRequest(BaseModel):
    capital: float = Field(default=10000.0, ge=0.0)
    usar_mensal: bool = True
    aporte_mensal: float = Field(default=0.0, ge=0.0)
    tma_modo: str = "auto"
    selic_pct: float = Field(default=10.5, ge=0.0)
    ipca_pct: float = Field(default=4.5, ge=0.0)
    tma_manual_pct: float = Field(default=5.5, ge=0.0)
    inflacao_pct: float = Field(default=4.5, ge=0.0)
    ativos: List[AtivoPayload]

    @field_validator("tma_modo")
    @classmethod
    def _tma_modo_ok(cls, v: str) -> str:
        if v not in ("auto", "manual"):
            raise ValueError("tma_modo deve ser 'auto' ou 'manual'.")
        return v


def para_ativo(p: AtivoPayload) -> Ativo:
    """Converte um payload para o modelo de dominio Ativo."""
    return Ativo(
        nome=p.nome.strip() or "Ativo",
        taxa=p.taxa_pct / 100.0,
        periodo=p.periodo,
        base=p.base,
        prazo_meses=p.prazo_meses,
        imposto_modo=p.imposto_modo,
        imposto_percentual=p.imposto_pct / 100.0,
        admin_modo=p.admin_modo,
        admin_percentual=p.admin_pct / 100.0,
        aporte_inicial_min=p.inicial_min,
        aporte_inicial_max=p.inicial_max if p.inicial_max > 0 else None,
        usa_aporte_mensal=p.usa_mensal,
        aporte_mensal_max=p.mensal_max if p.mensal_max > 0 else None,
    )


def calcular_tma(req: OtimizarRequest) -> float:
    """Determina a TMA anual a partir do modo escolhido no payload."""
    if req.tma_modo == "auto":
        return tma_por_indicadores(req.selic_pct / 100.0, req.ipca_pct / 100.0)
    return req.tma_manual_pct / 100.0


def inflacao_usada(req: OtimizarRequest) -> float:
    """Inflacao anual usada no retorno real."""
    if req.tma_modo == "auto":
        return req.ipca_pct / 100.0
    return req.inflacao_pct / 100.0