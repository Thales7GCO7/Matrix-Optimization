"""Alocação ótima de capital entre ativos.

Como as funções de retorno líquido são lineares em cada aporte (a renda
efetiva é proporcional ao capital), o problema de maximizar a riqueza
líquida final é um problema de programação linear com limites, cuja solução
ótima é encontrada por seleção gulosa: investir primeiro nos ativos com
maior retorno líquido anualizado, respeitando os limites mínimo e máximo
por ativo. O capital excedente (ou o capital que nenhum ativo consegue
alocar acima da taxa mínima) permanece em uma reserva rendendo a própria
taxa mínima (custo de oportunidade).
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np

from . import instrumentos
from . import desempenho
from . import matriz


def _criar_reserva(taxa_minima_anual: float):
    """Ativo virtual de reserva: rende a taxa mínima, sem imposto/taxas."""
    return instrumentos.Ativo(
        nome="Reserva (taxa mínima)",
        taxa=max(taxa_minima_anual, 0.0),
        periodo="anual",
        base="efetiva",
        prazo_meses=12,
        modo_imposto="isento",
        modo_taxa="nenhuma",
    )


@dataclass
class Alocacao:
    ativo: instrumentos.Ativo
    aporte_inicial: float
    aporte_mensal: float
    eh_reserva: bool = False


@dataclass
class ResultadoOtimizacao:
    capital_inicial: float
    mensal_disponivel: float
    taxa_minima_anual: float
    inflacao_anual: float
    alocacoes: List[Alocacao] = field(default_factory=list)
    metricas: List[desempenho.MetricasAtivo] = field(default_factory=list)
    carteira: Optional[desempenho.MetricasCarteira] = None
    erro: str = ""
    ativos: List[instrumentos.Ativo] = field(default_factory=list)


class OtimizadorCarteira:
    def __init__(
        self,
        ativos: List[instrumentos.Ativo],
        capital_inicial: float,
        taxa_minima_anual: float,
        inflacao_anual: float,
        aporte_mensal: float = 0.0,
        usar_mensal: bool = False,
    ):
        self.ativos = list(ativos)
        self.capital_inicial = float(capital_inicial)
        self.taxa_minima_anual = float(taxa_minima_anual)
        self.inflacao_anual = float(inflacao_anual)
        self.aporte_mensal = float(aporte_mensal) if usar_mensal else 0.0
        self.usar_mensal = bool(usar_mensal)

    def resolver(self) -> ResultadoOtimizacao:
        res = ResultadoOtimizacao(
            capital_inicial=self.capital_inicial,
            mensal_disponivel=self.aporte_mensal,
            taxa_minima_anual=self.taxa_minima_anual,
            inflacao_anual=self.inflacao_anual,
        )
        try:
            self._validar()
        except ValueError as exc:
            res.erro = str(exc)
            return res

        reserva = _criar_reserva(self.taxa_minima_anual)

        ordem_inicial = self._ordenar_por_retorno_liquido(self.ativos + [reserva])
        ordem_mensal = self._ordenar_por_retorno_liquido(
            [i for i in self.ativos if i.usa_mensal] + [reserva]
        )

        inicial = self._alocar(
            ordem_inicial,
            self.capital_inicial,
            fn_min=lambda a: a.minimo_inicial,
            fn_max=lambda a: a.maximo_inicial if a.maximo_inicial is not None else float("inf"),
        )
        mensal = {}
        if self.usar_mensal and self.aporte_mensal > 0.0:
            mensal = self._alocar(
                ordem_mensal,
                self.aporte_mensal,
                fn_min=lambda a: 0.0,
                fn_max=lambda a: a.maximo_mensal if a.maximo_mensal is not None else float("inf"),
            )

        # Combina as alocações de cada ativo (reserva incluída nos dois fluxos).
        # Todo ativo aparece nas métricas (mesmo com aportes zerados) para
        # mostrar na tela quais não receberam capital.
        nomes = list(dict.fromkeys([a.nome for a in self.ativos] + [reserva.nome]))
        por_nome = {a.nome: a for a in self.ativos + [reserva]}
        alocacoes: List[Alocacao] = []
        metricas: List[desempenho.MetricasAtivo] = []
        for nome in nomes:
            ativo = por_nome[nome]
            a_ini = inicial.get(ativo, 0.0)
            p_men = mensal.get(ativo, 0.0)
            eh_reserva = ativo is reserva
            alocacoes.append(Alocacao(ativo, a_ini, p_men, eh_reserva=eh_reserva))
            metricas.append(
                desempenho.calcular_ativo(
                    ativo, a_ini, p_men, self.taxa_minima_anual, self.inflacao_anual, eh_reserva=eh_reserva
                )
            )

        # Mantém só os ativos com aportes na lista de alocação (usada nos gráficos).
        res.alocacoes = [a for a in alocacoes if a.aporte_inicial > 0 or a.aporte_mensal > 0]
        res.metricas = metricas
        res.ativos = [por_nome[nome] for nome in nomes]
        res.carteira = desempenho.calcular_carteira(metricas, self.taxa_minima_anual)
        return res

    def _validar(self):
        for ativo in self.ativos:
            if ativo.minimo_inicial is None:
                continue
            if (
                ativo.maximo_inicial is not None
                and ativo.maximo_inicial < ativo.minimo_inicial
            ):
                raise ValueError(
                    f"Limite máximo abaixo do mínimo para o ativo {ativo.nome!r}."
                )
        total_minimos = sum(
            a.minimo_inicial for a in self.ativos if a.minimo_inicial is not None
        )
        if total_minimos > self.capital_inicial:
            raise ValueError("A soma dos aportes mínimos excede o capital disponível.")

    @staticmethod
    def _ordenar_por_retorno_liquido(ativos: List[instrumentos.Ativo]) -> List[instrumentos.Ativo]:
        """Ordem decrescente de retorno líquido anualizado (versão vetorizada)."""
        taxas = matriz.vetor_retornos_liquidos(ativos)
        ordem = np.argsort(-taxas)
        return [ativos[i] for i in ordem]

    @staticmethod
    def _alocar(
        ordem: List[instrumentos.Ativo],
        capital: float,
        fn_min,
        fn_max,
    ) -> Dict[instrumentos.Ativo, float]:
        """Alocação ótima com limites mínimo e máximo (vetorizada).

        1. Garante o mínimo de cada ativo (reserva obrigatória de diversificação).
        2. Distribui o restante por eficiência (gulosa): primeiro para os
           ativos de maior taxa líquida, até o máximo de cada um.
        """
        n = len(ordem)
        taxas = np.array([instrumentos.retorno_liquido_anualizado(a) for a in ordem])
        minimos = np.array([fn_min(a) or 0.0 for a in ordem])
        maximos_brutos = [fn_max(a) for a in ordem]
        # Preserva a semântica original: um ativo com máximo <= 0 é ignorado
        # (não recebe nem o mínimo).
        validos = np.array([not (m is not None and m <= 0.0) for m in maximos_brutos])
        minimos = np.where(validos, minimos, 0.0)
        maximos = np.array([m if m is not None else np.inf for m in maximos_brutos])
        maximos = np.where(validos, maximos, 0.0)

        vetor_aloc = matriz.alocacao_vetorizada(capital, taxas, minimos, maximos)

        aloc = {}
        for i, ativo in enumerate(ordem):
            if not validos[i]:
                continue
            if vetor_aloc[i] > 1e-9:
                aloc[ativo] = float(vetor_aloc[i])
            elif minimos[i] > 0:
                aloc[ativo] = float(minimos[i])
        return aloc
