import unittest

from src.instruments import Ativo, resumo_ativo
from src.math_finance import montante_aporte_unico
from src.performance import calcular_ativo, calcular_carteira


def ativo_simples(nome, taxa, prazo=12, **extra) -> Ativo:
    defaults = dict(taxa=taxa, prazo_meses=prazo, imposto_modo="isento", admin_modo="nenhuma")
    defaults.update(extra)
    return Ativo(nome=nome, **defaults)


class TestIndicadoresAporteUnico(unittest.TestCase):
    def test_tma_zero(self):
        at = ativo_simples("A", 0.10)
        ind = calcular_ativo(at, 1000.0, 0.0, tma_anual=0.0, inflacao_anual=0.0)
        self.assertAlmostEqual(ind.montante_liquido, 1100.0)
        self.assertAlmostEqual(ind.lucro_liquido, 100.0)
        self.assertAlmostEqual(ind.roi, 0.10)
        self.assertAlmostEqual(ind.roi_anualizado, 0.10)
        self.assertAlmostEqual(ind.vpl, 100.0)
        self.assertAlmostEqual(ind.il, 1.10)
        self.assertAlmostEqual(ind.tir_anual, 0.10)
        self.assertEqual(ind.payback_simples, 1.0)

    def test_vpl_descontado_na_tma(self):
        at = ativo_simples("A", 0.10)
        ind = calcular_ativo(at, 1000.0, 0.0, tma_anual=0.05, inflacao_anual=0.0)
        self.assertAlmostEqual(ind.vpl, -1000.0 + 1100.0 / 1.05, places=9)
        self.assertAlmostEqual(ind.alfa, 0.05)

    def test_imposto_reduz_roi(self):
        at = ativo_simples("A", 0.10, imposto_modo="fixo", imposto_percentual=0.20)
        res = resumo_ativo(at, 1000.0, 0.0)
        self.assertAlmostEqual(res["rendimento_bruto"], 100.0)
        self.assertAlmostEqual(res["imposto"], 20.0)
        self.assertAlmostEqual(res["lucro_liquido"], 80.0)
        ind = calcular_ativo(at, 1000.0, 0.0, tma_anual=0.0, inflacao_anual=0.0)
        self.assertAlmostEqual(ind.roi, 0.08)

    def test_retorno_real(self):
        at = ativo_simples("A", 0.14)
        ind = calcular_ativo(at, 1000.0, 0.0, tma_anual=0.05, inflacao_anual=0.04)
        self.assertAlmostEqual(ind.retorno_real, 1.14 / 1.04 - 1.0)


class TestIndicadoresSerie(unittest.TestCase):
    def test_serie_acumula(self):
        at = ativo_simples("A", 0.1268250301319698, prazo=12)
        ind = calcular_ativo(at, 0.0, 100.0, tma_anual=0.0, inflacao_anual=0.0)
        # i_mensal = 1% -> serie postecipada
        self.assertAlmostEqual(ind.montante_liquido, 100.0 * ((1.01 ** 12 - 1) / 0.01), places=6)
        self.assertAlmostEqual(ind.aportado_total, 1200.0)
        self.assertGreater(ind.lucro_liquido, 0.0)

    def test_payback_serie(self):
        at = ativo_simples("A", 0.1268250301319698, prazo=12)
        ind = calcular_ativo(at, 0.0, 100.0, tma_anual=0.0, inflacao_anual=0.0)
        self.assertIsNotNone(ind.payback_simples)
        self.assertLessEqual(ind.payback_simples, 12.0)


class TestCarteira(unittest.TestCase):
    def test_carteira_reserva_vpl_nulo(self):
        # Reserva rende exatamente a TMA -> VPL ~ 0.
        tma = 0.06
        res_ativo = Ativo(
            nome="Reserva", taxa=tma, prazo_meses=12,
            imposto_modo="isento", admin_modo="nenhuma",
        )
        ind = calcular_ativo(res_ativo, 1000.0, 0.0, tma_anual=tma, inflacao_anual=0.03, reserva=True)
        self.assertAlmostEqual(ind.vpl, 0.0, places=6)
        self.assertAlmostEqual(ind.alfa, 0.0, places=6)

    def test_carteira_agrega(self):
        a = calcular_ativo(ativo_simples("A", 0.10), 800.0, 0.0, 0.05, 0.04)
        b = calcular_ativo(ativo_simples("B", 0.06), 200.0, 0.0, 0.05, 0.04)
        c = calcular_carteira([a, b], 0.05)
        self.assertAlmostEqual(c.capital_inicial, 1000.0)
        # Desta vez o patrim. de B e projetado/reinvestido ate o prazo maximo (12).
        self.assertGreater(c.montante_liquido, 1000.0)


if __name__ == "__main__":
    unittest.main()