"""Impostos e taxas administrativas aplicados aos investimentos.

Lógica genérica de valor líquido (vale para qualquer tipo de investimento):

.. code-block:: text

    ganho_bruto   = valor_bruto - total_aportado
    imposto       = imposto_sobre_ganho(resolver_aliquota(...), ganho_bruto)
    taxa          = valor_taxa_adm(modo_taxa, taxa_pct, ...)
    valor_liquido = valor_bruto - imposto - taxa
    lucro_liquido = valor_liquido - total_aportado

Especificações de imposto de renda (``modo_imposto`` + ``imposto_pct`` + ``tabela`` opcional):

- ``"isento"``: sem tributação (ex. LCI/LCA, CRI/CRA, debêntures incentivadas).
  ``imposto_pct`` e ``tabela`` são ignorados.
- ``"fixo"``: uma alíquota única sobre o ganho bruto (ex. tabela regressiva
  do IR informada pelo usuário: 22,5%/20%/17,5%/15% conforme o prazo).
- ``"tabela"``: tabela progressiva/regressiva selecionada pelo prazo de
  permanência ou pelo tamanho do ganho. ``tabela`` é uma lista de pares
  ``(limite, aliquota)`` ordenada de forma crescente; o primeiro ``limite``
  que cobre o valor de consulta vence, senão vence a última alíquota. Duas
  chaves de consulta são suportadas:

  - ``("prazo", meses)``: ex. tabelas regressivas ``[(6, 0.225),
    (12, 0.20), (24, 0.175), (inf, 0.15)]``;
  - ``("ganho", valor)``: ex. faixas progressivas sobre o ganho.

  Qualquer outro ``modo`` recai em 0.0 (sem imposto), de modo que tipos
  futuros desconhecidos de investimento nunca quebram o cálculo.

Especificações de taxa administrativa (``modo_taxa`` + ``taxa_pct``):

- ``"nenhuma"``: sem taxa.
- ``"aporte"``: ``taxa_pct`` único sobre os aportes (taxa de entrada).
- ``"patrimonio"``: ``taxa_pct`` a.a. sobre o patrimônio sob gestão
  (taxa de administração de fundos), aplicado geometricamente ao longo do prazo.
- ``"ganho"``: ``taxa_pct`` sobre o ganho bruto (taxa de performance).

Use :func:`calcular_valor_liquido` como ponto de entrada genérico único e
:func:`explicar_calculo_liquido` quando o front-end precisar mostrar as
fórmulas, as variáveis e o passo a passo numérico por ativo.
"""

from typing import Any, Dict, List, Optional, Sequence, Tuple

MODOS_IMPOSTO = ["isento", "fixo"]
#: Modos estendidos aceitos pelo resolvedor genérico (superconjunto de MODOS_IMPOSTO).
#: Mantido em separado para a constante legada ``MODOS_IMPOSTO`` continuar estável.
MODOS_IMPOSTO_ESTENDIDO = ["isento", "fixo", "tabela"]
MODOS_TAXA = ["nenhuma", "aporte", "patrimonio", "ganho"]


def aliquota_imposto(modo: str, percentual_fixo: Optional[float] = None) -> float:
    """Alíquota efetiva de imposto de renda (0 para isento / fixo=None)."""
    if modo == "isento":
        return 0.0
    if modo == "fixo":
        return float(percentual_fixo if percentual_fixo is not None else 0.0)
    return 0.0


def resolver_aliquota(
    modo: str,
    percentual_fixo: Optional[float] = None,
    tabela: Optional[Sequence[Tuple[float, float]]] = None,
    chave_tabela: str = "prazo",
    valor_consulta: float = 0.0,
) -> float:
    """Alíquota efetiva de imposto de renda para qualquer tipo de investimento.

    - ``isento``/``fixo`` comportam-se exatamente como :func:`aliquota_imposto`.
    - ``tabela`` escolhe a alíquota de uma tabela ``[(limite, aliquota), ...]``
      usando ``valor_consulta`` (prazo em meses quando ``chave_tabela="prazo"``,
      ganho bruto quando ``chave_tabela="ganho"``). Modos desconhecidos retornam 0.0.
    """
    if modo == "tabela":
        return _aliquota_tabela(tabela, valor_consulta)
    return aliquota_imposto(modo, percentual_fixo)


def _aliquota_tabela(
    tabela: Optional[Sequence[Tuple[float, float]]], valor_consulta: float
) -> float:
    if not tabela:
        return 0.0
    try:
        ordenada = sorted(tabela, key=lambda b: b[0])
    except Exception:
        return 0.0
    valor = float(valor_consulta)
    for limite, aliquota in ordenada:
        try:
            if valor <= float(limite):
                return float(aliquota)
        except Exception:
            continue
    try:
        return float(ordenada[-1][1])
    except Exception:
        return 0.0


def imposto_sobre_ganho(aliquota: float, ganho_bruto: float) -> float:
    """Imposto em moeda sobre o ganho bruto (prejuízos não são tributados)."""
    if ganho_bruto <= 0.0:
        return 0.0
    return float(aliquota) * float(ganho_bruto)


def valor_taxa_adm(
    modo: str,
    percentual: float,
    valor_bruto: float,
    ganho_bruto: float,
    total_aportado: float,
    prazo_meses: int,
) -> float:
    """Taxa administrativa em moeda para o modo configurado."""
    if modo == "nenhuma" or percentual <= 0.0:
        return 0.0
    pct = float(percentual)
    if modo == "aporte":
        return pct * float(total_aportado)
    if modo == "patrimonio":
        anos = float(prazo_meses) / 12.0
        return float(valor_bruto) * (1.0 - (1.0 - pct) ** anos)
    if modo == "ganho":
        return pct * max(float(ganho_bruto), 0.0)
    return 0.0


def calcular_valor_liquido(
    valor_bruto: float,
    total_aportado: float,
    modo_imposto: str = "isento",
    imposto_pct: float = 0.0,
    modo_taxa: str = "nenhuma",
    taxa_pct: float = 0.0,
    prazo_meses: int = 12,
    tabela: Optional[Sequence[Tuple[float, float]]] = None,
    chave_tabela: str = "prazo",
) -> Dict[str, float]:
    """Cálculo genérico de valor líquido para qualquer tipo de investimento.

    Aplica, em ordem: ``ganho_bruto = bruto - aportado``,
    ``imposto = aliquota * max(ganho, 0)``, ``taxa = f(modo, ...)``,
    ``liquido = bruto - imposto - taxa``, ``lucro = liquido - aportado``.
    """
    bruto = float(valor_bruto)
    aportado = float(total_aportado)
    ganho_bruto = bruto - aportado
    consulta = float(prazo_meses) if chave_tabela == "prazo" else max(ganho_bruto, 0.0)
    aliquota = resolver_aliquota(modo_imposto, imposto_pct, tabela, chave_tabela, consulta)
    imposto = imposto_sobre_ganho(aliquota, ganho_bruto)
    taxa = valor_taxa_adm(
        modo_taxa, taxa_pct, bruto, ganho_bruto, aportado, int(prazo_meses)
    )
    valor_liquido = bruto - imposto - taxa
    return {
        "valor_bruto": bruto,
        "total_aportado": aportado,
        "ganho_bruto": ganho_bruto,
        "aliquota": float(aliquota),
        "imposto": float(imposto),
        "taxa": float(taxa),
        "valor_liquido": float(valor_liquido),
        "lucro_liquido": float(valor_liquido - aportado),
    }


def descrever_logica_calculo() -> Dict[str, Any]:
    """Descrição estática das fórmulas, funções e variáveis genéricas.

    Retornada tal qual pela API (``logica_calculo``) e renderizada pelo
    front-end, de modo que a interface sempre documenta a lógica exata do código.
    """
    return {
        "etapas": [
            "valor_bruto = bruto_aporte_unico(A) + bruto_serie_mensal(P)",
            "ganho_bruto = valor_bruto - total_aportado, onde total_aportado = A + P * prazo_meses",
            "aliquota = resolver_aliquota(modo_imposto, imposto_pct[, tabela])",
            "imposto = aliquota * max(ganho_bruto, 0)  [prejuízos não são tributados]",
            "taxa = valor_taxa_adm(modo_taxa, taxa_pct, valor_bruto, ganho_bruto, total_aportado, prazo_meses)",
            "valor_liquido = valor_bruto - imposto - taxa",
            "lucro_liquido = valor_liquido - total_aportado",
        ],
        "funcoes": [
            {
                "nome": "bruto_aporte_unico / bruto_serie_mensal",
                "modulo": "src/instrumentos.py",
                "papel": "Capitaliza os aportes à taxa anual efetiva do ativo até o mês de resgate (bruto, antes das deduções).",
            },
            {
                "nome": "resolver_aliquota",
                "modulo": "src/impostos.py",
                "papel": "Mapeia qualquer especificação de imposto em uma alíquota efetiva: isento -> 0, fixo -> % fixa, tabela -> consulta à tabela por prazo ou ganho.",
            },
            {
                "nome": "imposto_sobre_ganho",
                "modulo": "src/impostos.py",
                "papel": "Converte a alíquota em moeda: alíquota * ganho, ou 0 quando ganho <= 0.",
            },
            {
                "nome": "valor_taxa_adm",
                "modulo": "src/impostos.py",
                "papel": "Converte qualquer especificação de taxa em moeda: aporte (% dos aportes), patrimonio (% a.a. geométrico), ganho (% do ganho).",
            },
            {
                "nome": "calcular_valor_liquido",
                "modulo": "src/impostos.py",
                "papel": "Ponto de entrada genérico único que encadeia os passos acima; usado por todo tipo de ativo, incluindo a reserva da taxa mínima.",
            },
        ],
        "variaveis": [
            {"nome": "A", "significado": "Aporte inicial único alocado hoje."},
            {"nome": "P", "significado": "Aporte mensal recorrente (postecipado)."},
            {"nome": "prazo_meses", "significado": "Meses até o resgate; também dimensiona o horizonte da taxa e a consulta à tabela."},
            {"nome": "valor_bruto", "significado": "Valor acumulado antes de impostos/taxas."},
            {"nome": "total_aportado", "significado": "Dinheiro efetivamente aportado: A + P * prazo_meses."},
            {"nome": "ganho_bruto", "significado": "valor_bruto - total_aportado; a única base de imposto/taxa ligada ao lucro."},
            {"nome": "modo_imposto / imposto_pct", "significado": "Especificação de imposto do investimento: isento | fixo % sobre ganhos | tabela."},
            {"nome": "modo_taxa / taxa_pct", "significado": "Especificação de taxa do investimento: nenhuma | aporte | patrimonio (% a.a.) | ganho."},
            {"nome": "valor_liquido", "significado": "Riqueza final disponível: bruto - imposto - taxa."},
            {"nome": "lucro_liquido", "significado": "valor_liquido - total_aportado; maximizado pelo otimizador."},
        ],
    }


def explicar_calculo_liquido(
    valor_bruto: float,
    total_aportado: float,
    modo_imposto: str = "isento",
    imposto_pct: float = 0.0,
    modo_taxa: str = "nenhuma",
    taxa_pct: float = 0.0,
    prazo_meses: int = 12,
    tabela: Optional[Sequence[Tuple[float, float]]] = None,
    chave_tabela: str = "prazo",
    nome_ativo: str = "Ativo",
) -> Dict[str, Any]:
    """Passo a passo numérico por ativo da lógica genérica de valor líquido."""
    res = calcular_valor_liquido(
        valor_bruto, total_aportado, modo_imposto, imposto_pct,
        modo_taxa, taxa_pct, prazo_meses, tabela, chave_tabela,
    )
    if modo_imposto == "isento":
        formula_imposto = "imposto = 0 (isento)"
    elif modo_imposto == "tabela":
        formula_imposto = (
            f"imposto = consulta_tabela({chave_tabela}={res['aliquota']:.4g} alíquota) * "
            f"max(ganho, 0) = {res['imposto']:.2f}"
        )
    else:
        formula_imposto = (
            f"imposto = {res['aliquota']:.4g} * max({res['ganho_bruto']:.2f}, 0)"
            f" = {res['imposto']:.2f}"
        )
    if modo_taxa == "aporte":
        formula_taxa = f"taxa = {float(taxa_pct):.4g} * aportado = {res['taxa']:.2f}"
    elif modo_taxa == "patrimonio":
        formula_taxa = (
            f"taxa = bruto * (1 - (1 - {float(taxa_pct):.4g})^({float(prazo_meses)/12.0:.4g}a))"
            f" = {res['taxa']:.2f}"
        )
    elif modo_taxa == "ganho":
        formula_taxa = f"taxa = {float(taxa_pct):.4g} * max(ganho, 0) = {res['taxa']:.2f}"
    else:
        formula_taxa = "taxa = 0 (nenhuma)"
    passos: List[str] = [
        f"{nome_ativo}: aportado = A + P*n = {res['total_aportado']:.2f}",
        f"{nome_ativo}: ganho_bruto = {res['valor_bruto']:.2f} - {res['total_aportado']:.2f} = {res['ganho_bruto']:.2f}",
        f"{nome_ativo}: {formula_imposto}",
        f"{nome_ativo}: {formula_taxa}",
        f"{nome_ativo}: valor_liquido = {res['valor_bruto']:.2f} - {res['imposto']:.2f} - {res['taxa']:.2f} = {res['valor_liquido']:.2f}",
        f"{nome_ativo}: lucro_liquido = {res['valor_liquido']:.2f} - {res['total_aportado']:.2f} = {res['lucro_liquido']:.2f}",
    ]
    return {**res, "ativo": nome_ativo, "formula_imposto": formula_imposto,
            "formula_taxa": formula_taxa, "passos": passos}
