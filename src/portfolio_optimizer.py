"""Alocacao otima de capital entre ativos.

Como as funcoes de retorno liquido sao lineares em cada aporte (a renda
real e proporcional ao capital), o problema de maximizar o patrimonio
liquido final e um problema de programacao linear com limites, cuja
solucao otima e obtida por selecao gulosa: aplicar primeiro nos ativos
de maior retorno liquido anualizado, respeitando limites minimos e
maximos. O capital que sobra (ou que nao atinge a TMA em nenhum ativo)
fica na reserva que rende a propria TMA (custo de oportunidade).
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from . import instruments
from . import performance
from . import math_finance as mf


def _criar_reserva(tma_anual: float):
    """Ativo virtual Reserva/TMA: rende a taxa minima, sem imposto/taxa."""
    return instruments.Ativo(
        nome="Reserva (TMA)",
        taxa=max(tma_anual, 0.0),
        periodo="anual",
        base="efetiva",
        prazo_meses=12,
        imposto_modo="isento",
        admin_modo="nenhuma",
    )


@dataclass
class Alocacao:
    ativo: instruments.Ativo
    aporte_inicial: float
    aporte_mensal: float
    reserva: bool = False


@dataclass
class ResultadoOtimizacao:
    capital_inicial: float
    aporte_mensal_disponivel: float
    tma_anual: float
    inflacao_anual: float
    alocacoes: List[Alocacao] = field(default_factory=list)
    indicadores: List[performance.IndicadoresAtivo] = field(default_factory=list)
    carteira: Optional[performance.IndicadoresCarteira] = None
    erro: str = ""


class PortfolioOptimizer:
    def __init__(
        self,
        ativos: List[instruments.Ativo],
        capital_inicial: float,
        tma_anual: float,
        inflacao_anual: float,
        aporte_mensal: float = 0.0,
        usar_aporte_mensal: bool = False,
    ):
        self.ativos = list(ativos)
        self.capital_inicial = float(capital_inicial)
        self.tma_anual = float(tma_anual)
        self.inflacao_anual = float(inflacao_anual)
        self.aporte_mensal = float(aporte_mensal) if usar_aporte_mensal else 0.0
        self.usar_aporte_mensal = bool(usar_aporte_mensal)

    def resolver(self) -> ResultadoOtimizacao:
        res = ResultadoOtimizacao(
            capital_inicial=self.capital_inicial,
            aporte_mensal_disponivel=self.aporte_mensal,
            tma_anual=self.tma_anual,
            inflacao_anual=self.inflacao_anual,
        )
        try:
            self._validar()
        except ValueError as exc:
            res.erro = str(exc)
            return res

        reserva = _criar_reserva(self.tma_anual)

        ordem_inicial = self._ordenar_por_taxa_liq(self.ativos + [reserva])
        ordem_mensal = self._ordenar_por_taxa_liq(
            [i for i in self.ativos if i.usa_aporte_mensal] + [reserva]
        )

        inicial = self._alocar(
            ordem_inicial,
            self.capital_inicial,
            min_fn=lambda a: a.aporte_inicial_min,
            max_fn=lambda a: a.aporte_inicial_max if a.aporte_inicial_max is not None else float("inf"),
        )
        mensal = {}
        if self.usar_aporte_mensal and self.aporte_mensal > 0.0:
            mensal = self._alocar(
                ordem_mensal,
                self.aporte_mensal,
                min_fn=lambda a: 0.0,
                max_fn=lambda a: a.aporte_mensal_max if a.aporte_mensal_max is not None else float("inf"),
            )

        # Junta alocacoes de cada ativo (inclui reserva em ambos os fluxos).
        # Todos os ativos entram nos indicadores (mesmo com aporte zero), para
        # evidenciar na tela quais nao receberam capital.
        nomes = list(dict.fromkeys([a.nome for a in self.ativos] + [reserva.nome]))
        mapa = {a.nome: a for a in self.ativos + [reserva]}
        alocacoes: List[Alocacao] = []
        indicadores: List[performance.IndicadoresAtivo] = []
        for nome in nomes:
            ativo = mapa[nome]
            a_ini = inicial.get(ativo, 0.0)
            p_men = mensal.get(ativo, 0.0)
            eh_reserva = ativo is reserva
            alocacoes.append(Alocacao(ativo, a_ini, p_men, reserva=eh_reserva))
            indicadores.append(
                performance.calcular_ativo(
                    ativo, a_ini, p_men, self.tma_anual, self.inflacao_anual, reserva=eh_reserva
                )
            )

        # Mantem na lista de alocacao apenas quem recebeu capital (uso nos graficos).
        res.alocacoes = [a for a in alocacoes if a.aporte_inicial > 0 or a.aporte_mensal > 0]
        res.indicadores = indicadores
        res.carteira = performance.calcular_carteira(indicadores, self.tma_anual)
        return res

    def _validar(self):
        for ativo in self.ativos:
            if ativo.aporte_inicial_min is None:
                continue
            if (
                ativo.aporte_inicial_max is not None
                and ativo.aporte_inicial_max < ativo.aporte_inicial_min
            ):
                raise ValueError(
                    f"Limite maximo menor que o minimo no ativo {ativo.nome!r}."
                )
        soma_mins = sum(
            a.aporte_inicial_min for a in self.ativos if a.aporte_inicial_min is not None
        )
        if soma_mins > self.capital_inicial:
            raise ValueError("A soma dos aportes minimos excede o capital disponivel.")

    @staticmethod
    def _ordenar_por_taxa_liq(ativos: List[instruments.Ativo]) -> List[instruments.Ativo]:
        """Ordem decrescente de retorno liquido anualizado."""
        return sorted(
            ativos, key=lambda a: instruments.taxa_liquida_anualizada(a), reverse=True
        )

    @staticmethod
    def _alocar(
        ordem: List[instruments.Ativo],
        capital: float,
        min_fn,
        max_fn,
    ) -> Dict[instruments.Ativo, float]:
        """Alocacao otima com limites minimos e maximos.

        1. Garante o minimo de cada ativo (reserva obrigatoria de diversificacao).
        2. Distribui o restante por eficiencia (guloso): primeiro nos ativos
           de maior taxa liquida, ate o limite maximo de cada um.
        """
        aloc: Dict[instruments.Ativo, float] = {}
        for ativo in ordem:
            minimo = min_fn(ativo) or 0.0
            maximo = max_fn(ativo)
            if maximo is not None and maximo <= 0.0:
                continue
            aloc[ativo] = minimo

        restante = float(capital) - sum(aloc.values())
        for ativo in ordem:
            if restante <= 1e-9:
                break
            minimo = min_fn(ativo) or 0.0
            maximo = max_fn(ativo)
            limite_extra = float("inf") if maximo is None else maximo - minimo
            if limite_extra <= 0.0:
                continue
            extra = min(limite_extra, restante)
            aloc[ativo] += extra
            restante -= extra
        return aloc