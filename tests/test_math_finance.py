import unittest

from src.math_finance import (
    fator_serie_descontada,
    fator_serie_postecipada,
    montante_aporte_unico,
    montante_serie_postecipada,
    taxa_anual_efetiva,
    taxa_anual_equivalente,
    taxa_mensal_equivalente,
    tir_de_fluxo,
    tma_por_indicadores,
)


class TestConversaoDeTaxas(unittest.TestCase):
    def test_efetiva_mensal_para_anual(self):
        self.assertAlmostEqual(taxa_anual_efetiva(0.01, "mensal", "efetiva"), 0.1268250301319698)

    def test_efetiva_semestral_para_anual(self):
        self.assertAlmostEqual(taxa_anual_efetiva(0.06, "semestral", "efetiva"), 0.1236)

    def test_nominal_anual_com_capitalizacao_mensal(self):
        r = taxa_anual_efetiva(0.13, "mensal", "nominal")
        self.assertAlmostEqual(r, (1 + 0.13 / 12) ** 12 - 1)

    def test_equivalencia_mutua(self):
        taxa_mensal = taxa_mensal_equivalente(0.12)
        self.assertAlmostEqual(taxa_anual_equivalente(taxa_mensal, 12), 0.12, places=12)


class TestMontantes(unittest.TestCase):
    def test_aporte_unico(self):
        self.assertAlmostEqual(montante_aporte_unico(1000.0, 0.10, 12), 1100.0)

    def test_aporte_unico_dois_anos(self):
        self.assertAlmostEqual(montante_aporte_unico(1000.0, 0.10, 24), 1210.0)

    def test_serie_taxa_zero(self):
        self.assertEqual(montante_serie_postecipada(100.0, 0.0, 12), 1200.0)

    def test_serie_mensal_1pct(self):
        ml = montante_serie_postecipada(100.0, 0.01, 12)
        esperado = 100.0 * ((1.01 ** 12 - 1) / 0.01)
        self.assertAlmostEqual(ml, esperado)

    def test_fator_serie_descontada(self):
        self.assertAlmostEqual(fator_serie_descontada(0.01, 12), sum((1.01) ** -t for t in range(1, 13)))

    def test_serie_acumula_principal_nas_parcelas(self):
        ml = fator_serie_postecipada(0.01, 12)
        self.assertGreater(ml, 12.0)  # acrescimo de juros sobre as 12 parcelas


class TestTir(unittest.TestCase):
    def test_fluxo_simples(self):
        r = tir_de_fluxo([-1000.0, 1100.0])
        self.assertIsNotNone(r)
        self.assertAlmostEqual(r, 0.10, places=9)

    def test_fluxo_sem_raiz_positiva(self):
        # Sem raiz positiva (fluxo com prejuizo): retorna a raiz negativa.
        r = tir_de_fluxo([-100.0, -50.0, 10.0])
        self.assertIsNotNone(r)
        self.assertLess(r, 0.0)

    def test_fluxo_serie(self):
        fluxo = [-500.0] * 12
        fluxo[0] = -1000.0
        fluxo.append(8000.0 - 500.0)  # mes 12: aporte + resgate
        r = tir_de_fluxo(fluxo)
        self.assertIsNotNone(r)
        self.assertGreater(r, 0.0)


class TestTma(unittest.TestCase):
    def test_juro_real(self):
        tma = tma_por_indicadores(0.105, 0.045)
        self.assertAlmostEqual(tma, (1.105 / 1.045) - 1)

    def test_selic_igual_ipca_retorno_zero(self):
        self.assertAlmostEqual(tma_por_indicadores(0.05, 0.05), 0.0)


if __name__ == "__main__":
    unittest.main()