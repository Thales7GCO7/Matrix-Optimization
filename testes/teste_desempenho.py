import unittest

from src.instrumentos import Ativo, resumo_ativo
from src.matematica_financeira import valor_futuro_aporte_unico
from src.desempenho import calcular_ativo, calcular_carteira


def ativo_simples(nome, taxa, prazo=12, **extra) -> Ativo:
    padrao = dict(taxa=taxa, prazo_meses=prazo, modo_imposto="isento", modo_taxa="nenhuma")
    padrao.update(extra)
    return Ativo(nome=nome, **padrao)


class TesteMetricasAporteUnico(unittest.TestCase):
    def test_minima_zero(self):
        at = ativo_simples("A", 0.10)
        met = calcular_ativo(at, 1000.0, 0.0, taxa_minima_anual=0.0, inflacao_anual=0.0)
        self.assertAlmostEqual(met.valor_liquido, 1100.0)
        self.assertAlmostEqual(met.lucro_liquido, 100.0)
        self.assertAlmostEqual(met.roi, 0.10)
        self.assertAlmostEqual(met.roi_anualizado, 0.10)
        self.assertAlmostEqual(met.vpl, 100.0)
        self.assertAlmostEqual(met.indice_lucratividade, 1.10)
        self.assertAlmostEqual(met.tir_anual, 0.10)
        self.assertEqual(met.payback_simples, 1.0)

    def test_vpl_descontado_na_minima(self):
        at = ativo_simples("A", 0.10)
        met = calcular_ativo(at, 1000.0, 0.0, taxa_minima_anual=0.05, inflacao_anual=0.0)
        self.assertAlmostEqual(met.vpl, -1000.0 + 1100.0 / 1.05, places=9)
        self.assertAlmostEqual(met.alpha, 0.05)

    def test_imposto_reduz_roi(self):
        at = ativo_simples("A", 0.10, modo_imposto="fixo", imposto_pct=0.20)
        res = resumo_ativo(at, 1000.0, 0.0)
        self.assertAlmostEqual(res["ganho_bruto"], 100.0)
        self.assertAlmostEqual(res["imposto"], 20.0)
        self.assertAlmostEqual(res["lucro_liquido"], 80.0)
        met = calcular_ativo(at, 1000.0, 0.0, taxa_minima_anual=0.0, inflacao_anual=0.0)
        self.assertAlmostEqual(met.roi, 0.08)

    def test_retorno_real(self):
        at = ativo_simples("A", 0.14)
        met = calcular_ativo(at, 1000.0, 0.0, taxa_minima_anual=0.05, inflacao_anual=0.04)
        self.assertAlmostEqual(met.retorno_real, 1.14 / 1.04 - 1.0)


class TesteMetricasSerie(unittest.TestCase):
    def test_serie_acumula(self):
        at = ativo_simples("A", 0.1268250301319698, prazo=12)
        met = calcular_ativo(at, 0.0, 100.0, taxa_minima_anual=0.0, inflacao_anual=0.0)
        # taxa mensal = 1% -> série postecipada
        self.assertAlmostEqual(met.valor_liquido, 100.0 * ((1.01 ** 12 - 1) / 0.01), places=6)
        self.assertAlmostEqual(met.total_aportado, 1200.0)
        self.assertGreater(met.lucro_liquido, 0.0)

    def test_payback_serie(self):
        at = ativo_simples("A", 0.1268250301319698, prazo=12)
        met = calcular_ativo(at, 0.0, 100.0, taxa_minima_anual=0.0, inflacao_anual=0.0)
        self.assertIsNotNone(met.payback_simples)
        self.assertLessEqual(met.payback_simples, 12.0)


class TesteCarteira(unittest.TestCase):
    def test_carteira_reserva_vpl_zero(self):
        # Uma reserva rendendo exatamente a taxa mínima -> VPL ~ 0.
        minima = 0.06
        ativo_reserva = Ativo(
            nome="Reserva", taxa=minima, prazo_meses=12,
            modo_imposto="isento", modo_taxa="nenhuma",
        )
        met = calcular_ativo(ativo_reserva, 1000.0, 0.0, taxa_minima_anual=minima, inflacao_anual=0.03, eh_reserva=True)
        self.assertAlmostEqual(met.vpl, 0.0, places=6)
        self.assertAlmostEqual(met.alpha, 0.0, places=6)

    def test_carteira_agrega(self):
        a = calcular_ativo(ativo_simples("A", 0.10), 800.0, 0.0, 0.05, 0.04)
        b = calcular_ativo(ativo_simples("B", 0.06), 200.0, 0.0, 0.05, 0.04)
        c = calcular_carteira([a, b], 0.05)
        self.assertAlmostEqual(c.capital_inicial, 1000.0)
        # A riqueza de B agora é projetada/reinvestida até o prazo máximo (12).
        self.assertGreater(c.valor_liquido, 1000.0)


if __name__ == "__main__":
    unittest.main()
