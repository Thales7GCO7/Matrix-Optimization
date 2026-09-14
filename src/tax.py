"""Impostos e taxas administrativas aplicados sobre investimentos.

Tipos de imposto sobre o rendimento:
- "isento": sem tributacao (LCI/LCA, poupanca, dividendos isentos).
- "fixo": percentual unico sobre o rendimento bruto.
- "ir_tabela": aliquota regressiva do IR de renda fixa brasileiro,
  definida pelo prazo de permanencia (22,5% / 20% / 17,5% / 15%).

Tipos de taxa administrativa:
- "aporte": percentual unico sobre o valor aportado.
- "patrimonio": percentual anual sobre o patrimonio (taxa de
  administracao de fundos).
- "rendimento": percentual sobre o rendimento bruto (performance fee).
"""

from typing import List, Optional

#: Tabela regressiva do IR de renda fixa (Brasil), por prazo em dias.
TABELA_IR: List[dict] = [
    {"ate_dias": 180, "aliquota": 0.225, "rotulo": "ate 180 dias (22,5%)"},
    {"ate_dias": 360, "aliquota": 0.200, "rotulo": "181 a 360 dias (20%)"},
    {"ate_dias": 720, "aliquota": 0.175, "rotulo": "361 a 720 dias (17,5%)"},
    {"ate_dias": None, "aliquota": 0.150, "rotulo": "acima de 720 dias (15%)"},
]

MODOS_IMPOSTO = ["isento", "fixo", "ir_tabela"]
MODOS_ADMIN = ["nenhuma", "aporte", "patrimonio", "rendimento"]


def aliquota_ir_tabela(prazo_dias: int) -> float:
    """Aliquota do IR regressivo pelo prazo de permanencia em dias."""
    for faixa in TABELA_IR:
        if faixa["ate_dias"] is None or prazo_dias <= faixa["ate_dias"]:
            return faixa["aliquota"]
    return TABELA_IR[-1]["aliquota"]


def rotulo_ir_tabela(prazo_dias: int) -> str:
    """Descricao textual da faixa de IR para o prazo informado."""
    for faixa in TABELA_IR:
        if faixa["ate_dias"] is None or prazo_dias <= faixa["ate_dias"]:
            return faixa["rotulo"]
    return TABELA_IR[-1]["rotulo"]


def aliquota_imposto(
    modo: str,
    prazo_meses: int,
    percentual_fixo: Optional[float] = None,
) -> float:
    """Aliquota efetiva do imposto (0 para isento/fixo=None)."""
    if modo == "isento":
        return 0.0
    if modo == "fixo":
        return float(percentual_fixo if percentual_fixo is not None else 0.0)
    if modo == "ir_tabela":
        return aliquota_ir_tabela(prazo_meses * 30)
    return 0.0


def imposto_sobre_taxa(aliquota: float, rendimento_bruto: float) -> float:
    """Imposto em R$ sobre o rendimento bruto (nao tributa prejuizo)."""
    if rendimento_bruto <= 0.0:
        return 0.0
    return float(aliquota) * float(rendimento_bruto)


def taxa_admin_em_reais(
    modo: str,
    percentual: float,
    montante_bruto: float,
    rendimento_bruto: float,
    aportado_total: float,
    prazo_meses: int,
) -> float:
    """Taxa administrativa em R$ conforme o modo configurado."""
    if modo == "nenhuma" or percentual <= 0.0:
        return 0.0
    pct = float(percentual)
    if modo == "aporte":
        return pct * float(aportado_total)
    if modo == "patrimonio":
        anos = float(prazo_meses) / 12.0
        return float(montante_bruto) * (1.0 - (1.0 - pct) ** anos)
    if modo == "rendimento":
        return pct * max(float(rendimento_bruto), 0.0)
    return 0.0