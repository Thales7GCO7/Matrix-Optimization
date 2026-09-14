import unittest

from src.instruments import Ativo
from src.portfolio_optimizer import PortfolioOptimizer


def ativo(nome, taxa, prazo=12, **extra) -> Ativo:
    defaults = dict(taxa=taxa, prazo_meses=prazo, imposto_modo="isento", admin_modo="nenhuma")
    defaults.update(extra)
    return Ativo(nome=nome, **defaults)


class TestAlocacaoInicial(unittest.TestCase):
    def test_tudo_no_melhor_ativo(self):
        a = ativo("A", 0.10)
        b = ativo("B", 0.05)
        res = PortfolioOptimizer([a, b], capital_inicial=1000.0, tma_anual=0.03, inflacao_anual=0.0).resolver()
        mapa = {i.nome: i for i in res.indicadores}
        self.assertAlmostEqual(mapa["A"].aporte_inicial, 1000.0)
        self.assertAlmostEqual(mapa["B"].aporte_inicial, 0.0)
        self.assertAlmostEqual(mapa["Reserva (TMA)"].aporte_inicial, 0.0)

    def test_respeita_maximo_e_reserva_leva_resto(self):
        a = ativo("A", 0.10, aporte_inicial_max=600.0)
        b = ativo("B", 0.05, aporte_inicial_max=100.0)
        res = PortfolioOptimizer([a, b], capital_inicial=1000.0, tma_anual=0.03, inflacao_anual=0.0).resolver()
        mapa = {i.nome: i for i in res.indicadores}
        self.assertAlmostEqual(mapa["A"].aporte_inicial, 600.0)
        self.assertAlmostEqual(mapa["B"].aporte_inicial, 100.0)
        self.assertAlmostEqual(mapa["Reserva (TMA)"].aporte_inicial, 300.0)

    def test_reserva_vence_ate_ativo_abaixo_da_tma(self):
        abaixo = ativo("Ruim", 0.02)  # taxa liquida abaixo da TMA 3%
        res = PortfolioOptimizer([abaixo], capital_inicial=500.0, tma_anual=0.03, inflacao_anual=0.0).resolver()
        mapa = {i.nome: i for i in res.indicadores}
        self.assertAlmostEqual(mapa["Ruim"].aporte_inicial, 0.0)
        self.assertAlmostEqual(mapa["Reserva (TMA)"].aporte_inicial, 500.0)

    def test_minimo_e_diversificacao_obrigatoria(self):
        a = ativo("A", 0.10)
        b = ativo("B", 0.05, aporte_inicial_min=400.0)
        res = PortfolioOptimizer([a, b], capital_inicial=1000.0, tma_anual=0.03, inflacao_anual=0.0).resolver()
        mapa = {i.nome: i for i in res.indicadores}
        self.assertAlmostEqual(mapa["B"].aporte_inicial, 400.0)  # minimo garantido
        self.assertAlmostEqual(mapa["A"].aporte_inicial, 600.0)  # resto no melhor

    def test_minimo_acima_do_budget_da_erro(self):
        a = ativo("A", 0.10)
        b = ativo("B", 0.05, aporte_inicial_min=1200.0)
        res = PortfolioOptimizer([a, b], capital_inicial=1000.0, tma_anual=0.03, inflacao_anual=0.0).resolver()
        self.assertTrue(res.erro)


class TestAlocacaoMensal(unittest.TestCase):
    def test_distribui_aporte_mensal(self):
        a = ativo("A", 0.10, usa_aporte_mensal=True, aporte_mensal_max=200.0)
        b = ativo("B", 0.05, usa_aporte_mensal=True, aporte_mensal_max=150.0)
        res = PortfolioOptimizer(
            [a, b], capital_inicial=0.0, tma_anual=0.03, inflacao_anual=0.0,
            aporte_mensal=300.0, usar_aporte_mensal=True,
        ).resolver()
        mapa = {i.nome: i for i in res.indicadores}
        self.assertAlmostEqual(mapa["A"].aporte_mensal, 200.0)
        self.assertAlmostEqual(mapa["B"].aporte_mensal, 100.0)
        self.assertAlmostEqual(mapa["Reserva (TMA)"].aporte_mensal, 0.0)

    def test_sem_aporte_mensal_e_ignorado(self):
        a = ativo("A", 0.10, usa_aporte_mensal=False, aporte_mensal_max=200.0)
        res = PortfolioOptimizer(
            [a], capital_inicial=1000.0, tma_anual=0.03, inflacao_anual=0.0,
            aporte_mensal=300.0, usar_aporte_mensal=True,
        ).resolver()
        mapa = {i.nome: i for i in res.indicadores}
        self.assertAlmostEqual(mapa["A"].aporte_inicial, 1000.0)
        self.assertAlmostEqual(mapa["A"].aporte_mensal, 0.0)
        self.assertAlmostEqual(mapa["Reserva (TMA)"].aporte_mensal, 300.0)


class TestComImposto(unittest.TestCase):
    def test_imposto_maior_reduz_prioridade(self):
        a = ativo("A", 0.15, imposto_modo="fixo", imposto_percentual=0.5)  # taixa liquida reduzida
        b = ativo("B", 0.09)  # isento
        res = PortfolioOptimizer([a, b], capital_inicial=1000.0, tma_anual=0.03, inflacao_anual=0.0).resolver()
        mapa = {i.nome: i for i in res.indicadores}
        # 15% bruto com IR 50% -> liquido ~8,1%; B isento 9% -> B deve receber tudo.
        self.assertAlmostEqual(mapa["A"].aporte_inicial, 0.0)
        self.assertAlmostEqual(mapa["B"].aporte_inicial, 1000.0)


class TestCarteiraComposta(unittest.TestCase):
    def test_carteira_indicadores_sao_coerentes(self):
        a = ativo("A", 0.10, aporte_inicial_max=500.0, usa_aporte_mensal=True, aporte_mensal_max=100.0)
        res = PortfolioOptimizer(
            [a], capital_inicial=800.0, tma_anual=0.05, inflacao_anual=0.04,
            aporte_mensal=100.0, usar_aporte_mensal=True,
        ).resolver()
        self.assertEqual(res.erro, "")
        c = res.carteira
        # capital inicial = 500 (ativo A) + 300 (reserva) = 800
        self.assertAlmostEqual(c.capital_inicial, 800.0)
        self.assertAlmostEqual(c.reserva, 300.0)
        self.assertGreater(c.montante_liquido, 0.0)
        self.assertIsNotNone(c.tir_anual)


if __name__ == "__main__":
    unittest.main()