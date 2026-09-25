"""Projeção em dois ativos do programa linear de maximização do lucro.

O problema completo é N-dimensional::

    máx  Z = SOMA p_i * x_i            (lucro líquido, linear em cada aporte)
    s.t. SOMA x_i <= B                 (capital inicial disponível)
         l_i <= x_i <= u_i             (mínimo/máximo por ativo)

onde ``p_i`` é o lucro líquido de R$ 1 aplicado no ativo ``i``
(``resumo_ativo(ativo, 1.0, 0.0)["lucro_liquido"]``), ``B`` o capital
inicial e ``l_i``/``u_i`` os limites iniciais do ativo. Como o objetivo
e todas as restrições são lineares, o ótimo está em um vértice do
politopo viável — daí o solver guloso (caminhar na direção do
gradiente ``(p_1..p_N)`` até um limite travar).

Este módulo projeta essa geometria no plano dos dois ativos mais
eficientes (``x1`` horizontal, ``x2`` vertical) para poder desenhá-la:
retas de restrição, polígono viável, vértices enumerados com seus
valores de ``Z``, isolinhas de isolucro, o gradiente e a reta tangente
(ótima) de isolucro tocando o polígono no vértice ótimo.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from . import instrumentos
from . import matriz

EPS = 1e-9


@dataclass
class ModeloPL:
    viavel: bool = False
    ativo_x: str = ""
    ativo_y: str = ""
    c1: float = 0.0
    c2: float = 0.0
    orcamento: float = 0.0
    l1: float = 0.0
    u1: float = 0.0
    l2: float = 0.0
    u2: float = 0.0
    efetiva: Tuple[float, float] = (0.0, 0.0)
    poligono: List[Tuple[float, float]] = field(default_factory=list)
    vertices: List[Dict[str, Any]] = field(default_factory=list)
    otimo: Dict[str, Any] = field(default_factory=dict)
    niveis_iso: List[float] = field(default_factory=list)
    z_estrela: float = 0.0
    otimo_aresta: bool = False
    funcoes_lucro: List[Dict[str, Any]] = field(default_factory=list)
    motivo: str = ""


def _lucro_unitario(ativo: instrumentos.Ativo) -> Tuple[float, Dict[str, Any]]:
    """Lucro líquido de R$ 1 de aporte inicial mais sua decomposição em fórmula."""
    s = instrumentos.resumo_ativo(ativo, 1.0, 0.0)
    fator_bruto = s["valor_bruto"]  # G para x = 1
    info = {
        "ativo": ativo.nome,
        "formula": (
            f"L(x) = p*x, p = G - 1 - imposto_1 - taxa_1 "
            f"= {fator_bruto:.6g} - 1 - {s['imposto']:.6g} - {s['taxa']:.6g} "
            f"= {s['lucro_liquido']:.6g}"
        ),
        "lucro_unitario": float(s["lucro_liquido"]),
        "fator_bruto": float(fator_bruto),
        "imposto_unitario": float(s["imposto"]),
        "taxa_unitaria": float(s["taxa"]),
        "prazo_meses": ativo.prazo_meses,
    }
    return float(s["lucro_liquido"]), info


def _escolher_eixos(ativos: List[instrumentos.Ativo]) -> Optional[Tuple[Any, Any]]:
    """Os dois ativos não-reserva mais eficientes; recai em melhor + reserva."""
    cand = [a for a in ativos if a.nome != "Reserva (taxa mínima)"]
    if len(cand) >= 2:
        taxas = matriz.vetor_retornos_liquidos(cand)
        ordem = sorted(range(len(cand)), key=lambda i: -taxas[i])
        return cand[ordem[0]], cand[ordem[1]]
    if len(cand) == 1:
        reserva = next((a for a in ativos if a.nome == "Reserva (taxa mínima)"), None)
        if reserva is not None:
            return cand[0], reserva
        return None
    return None


def construir_modelo_pl(resultado) -> Optional[ModeloPL]:
    """Projeta um ResultadoOtimizacao no seu plano do PL de 2 ativos."""
    ativos = list(getattr(resultado, "ativos", []) or [])
    eixos = _escolher_eixos(ativos)
    if eixos is None:
        return None
    ax, ay = eixos
    B = float(resultado.capital_inicial)
    if B <= 0.0:
        return None

    c1, info_x = _lucro_unitario(ax)
    c2, info_y = _lucro_unitario(ay)

    l1 = max(float(ax.minimo_inicial or 0.0), 0.0)
    u1 = float(ax.maximo_inicial) if ax.maximo_inicial else B
    u1 = min(u1, B)
    l2 = max(float(ay.minimo_inicial or 0.0), 0.0)
    u2 = float(ay.maximo_inicial) if ay.maximo_inicial else B
    u2 = min(u2, B)

    modelo = ModeloPL(
        ativo_x=ax.nome, ativo_y=ay.nome, c1=c1, c2=c2, orcamento=B,
        l1=l1, u1=u1, l2=l2, u2=u2,
        funcoes_lucro=[info_x, info_y],
    )
    if l1 + l2 > B + EPS:
        modelo.motivo = "Projeção de 2 ativos inviável: l1 + l2 > orçamento."
        return modelo

    pontos = _vertices_viaveis(l1, u1, l2, u2, B)
    if not pontos:
        modelo.motivo = "Polígono viável vazio."
        return modelo

    modelo.viavel = True
    modelo.poligono = _ordenar_poligono(pontos)
    # Vértices com valores de Z, do melhor para o pior.
    ordenados = sorted(pontos, key=lambda p: -(c1 * p[0] + c2 * p[1]))
    z_estrela = c1 * ordenados[0][0] + c2 * ordenados[0][1]
    modelo.z_estrela = z_estrela
    modelo.vertices = [
        {"rotulo": f"V{k + 1}", "x1": p[0], "x2": p[1],
         "z": c1 * p[0] + c2 * p[1],
         "otimo": (c1 * p[0] + c2 * p[1]) >= z_estrela - 1e-6}
        for k, p in enumerate(ordenados)
    ]
    modelo.otimo_aresta = sum(1 for v in modelo.vertices if v["otimo"]) > 1
    melhor = modelo.vertices[0]
    modelo.otimo = {"x1": melhor["x1"], "x2": melhor["x2"], "z": melhor["z"],
                    "vertice": melhor["rotulo"]}
    modelo.niveis_iso = [z_estrela * f for f in (0.25, 0.55, 0.85) if z_estrela > 0]

    por_nome = {m.nome: m for m in (resultado.metricas or [])}
    mx = por_nome.get(ax.nome)
    my = por_nome.get(ay.nome)
    if mx is not None and my is not None:
        modelo.efetiva = (float(mx.aporte_inicial), float(my.aporte_inicial))
    return modelo


def _vertices_viaveis(l1, u1, l2, u2, B) -> List[Tuple[float, float]]:
    """Cantos da caixa dentro do semiplano do orçamento + cruzamentos com a reta do orçamento."""
    brutos: List[Tuple[float, float]] = [
        (l1, l2), (l1, u2), (u1, l2), (u1, u2),
        (B - l2, l2), (B - u2, u2), (l1, B - l1), (u1, B - u1),
    ]
    saida: List[Tuple[float, float]] = []
    for x1, x2 in brutos:
        if not (l1 - EPS <= x1 <= u1 + EPS and l2 - EPS <= x2 <= u2 + EPS):
            continue
        if x1 + x2 > B + EPS:
            continue
        saida.append((max(x1, 0.0), max(x2, 0.0)))
    # Remove duplicados (arredondados) preservando a ordem.
    vistos, unicos = set(), []
    for p in saida:
        chave = (round(p[0], 6), round(p[1], 6))
        if chave not in vistos:
            vistos.add(chave)
            unicos.append(p)
    return unicos


def _ordenar_poligono(pontos: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
    """Ordena os vértices no sentido anti-horário ao redor do centroide (para sombrear)."""
    cx = sum(p[0] for p in pontos) / len(pontos)
    cy = sum(p[1] for p in pontos) / len(pontos)
    import math
    return sorted(pontos, key=lambda p: math.atan2(p[1] - cy, p[0] - cx))


def descrever_modelo_pl(modelo: ModeloPL) -> Dict[str, Any]:
    """Modelo serializável em JSON: fórmulas, restrições, vértices, resolução."""
    def _f(v: float) -> float:
        return round(float(v), 2)
    restricoes = [
        f"x1 + x2 <= {_f(modelo.orcamento)}  (orçamento)",
        f"{_f(modelo.l1)} <= x1 <= {_f(modelo.u1) if modelo.u1 < float('inf') else float('inf')}  ({modelo.ativo_x})",
        f"{_f(modelo.l2)} <= x2 <= {_f(modelo.u2) if modelo.u2 < float('inf') else float('inf')}  ({modelo.ativo_y})",
        "x1 >= 0, x2 >= 0",
    ]
    passos = [
        f"Escreva cada função de lucro: L1(x1) = {modelo.c1:.6g}*x1, "
        f"L2(x2) = {modelo.c2:.6g}*x2 (lucro líquido por R$ 1 após imposto/taxas).",
        f"Objetivo: máx Z = {modelo.c1:.6g}*x1 + {modelo.c2:.6g}*x2; "
        f"gradiente vZ = ({modelo.c1:.6g}, {modelo.c2:.6g}).",
        "Cruze a caixa de limites com o semiplano do orçamento x1 + x2 <= B: "
        "o polígono viável (sombreado).",
        "Avalie Z em cada vértice " + ", ".join(
            f"{v['rotulo']}({_f(v['x1'])}, {_f(v['x2'])}) -> Z={_f(v['z'])}"
            for v in modelo.vertices) + ".",
        f"Ótimo em {modelo.otimo.get('vertice')}: "
        f"x1*={_f(modelo.otimo.get('x1', 0.0))}, "
        f"x2*={_f(modelo.otimo.get('x2', 0.0))}, "
        f"Z*={_f(modelo.otimo.get('z', 0.0))} — a reta tangente de isolucro "
        f"{modelo.c1:.6g}*x1 + {modelo.c2:.6g}*x2 = {_f(modelo.z_estrela)} "
        "toca o polígono ali"
        + (" ao longo de uma aresta inteira (qualquer ponto dela é ótimo)." if modelo.otimo_aresta
           else " (vértice único)."),
        "O solver guloso de N ativos faz exatamente esta caminhada em N dimensões: "
        "garante os mínimos, depois empurra o capital restante ao longo de vZ para o "
        "ativo mais íngreme até um teto travar. O PL dos aportes mensais é "
        "análogo (variáveis P_i, tetos mensais).",
    ]
    return {
        "viavel": modelo.viavel,
        "ativo_x": modelo.ativo_x,
        "ativo_y": modelo.ativo_y,
        "objetivo": f"máx Z = {modelo.c1:.6g}*x1 + {modelo.c2:.6g}*x2",
        "c1": modelo.c1,
        "c2": modelo.c2,
        "gradiente": [modelo.c1, modelo.c2],
        "orcamento": modelo.orcamento,
        "limites": {"l1": modelo.l1, "u1": modelo.u1,
                    "l2": modelo.l2, "u2": modelo.u2},
        "restricoes": restricoes,
        "funcoes_lucro": modelo.funcoes_lucro,
        "vertices": [{**v, "x1": _f(v["x1"]), "x2": _f(v["x2"]),
                      "z": _f(v["z"])} for v in modelo.vertices],
        "otimo": {k: (_f(v) if isinstance(v, float) else v)
                  for k, v in modelo.otimo.items()},
        "tangente": f"{modelo.c1:.6g}*x1 + {modelo.c2:.6g}*x2 = {_f(modelo.z_estrela)}",
        "z_estrela": _f(modelo.z_estrela),
        "otimo_aresta": modelo.otimo_aresta,
        "efetiva": {"x1": _f(modelo.efetiva[0]), "x2": _f(modelo.efetiva[1])},
        "passos": passos,
        "observacao": ("Projeção de 2 ativos sobre os dois ativos mais eficientes; "
                       "com 3+ ativos com aportes, o verdadeiro ótimo vive em N dimensões "
                       "e este plano mostra a geometria do método. Ponto branco = "
                       "alocação gulosa efetiva nestes eixos."),
    }
