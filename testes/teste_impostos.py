import unittest

from src.impostos import (
    aliquota_imposto,
    imposto_sobre_ganho,
    valor_taxa_adm,
    MODOS_IMPOSTO,
)


class TesteImpostoRenda(unittest.TestCase):
    def test_somente_modos_genericos(self):
        self.assertEqual(MODOS_IMPOSTO, ["isento", "fixo"])

    def test_fixo_e_isento(self):
        self.assertAlmostEqual(aliquota_imposto("isento", None), 0.0)
        self.assertAlmostEqual(aliquota_imposto("isento", 0.25), 0.0)
        self.assertAlmostEqual(aliquota_imposto("fixo", 0.15), 0.15)
        self.assertAlmostEqual(aliquota_imposto("fixo", None), 0.0)

    def test_aliquotas_tipicas_ir(self):
        # Tabela regressiva do IR: 22,5%/20%/17,5%/15% conforme o prazo.
        self.assertAlmostEqual(aliquota_imposto("fixo", 0.15), 0.15)
        self.assertAlmostEqual(aliquota_imposto("fixo", 0.25), 0.25)
        self.assertAlmostEqual(aliquota_imposto("fixo", 0.30), 0.30)

    def test_imposto_nao_incide_sobre_prejuizo(self):
        self.assertEqual(imposto_sobre_ganho(0.2, -50.0), 0.0)
        self.assertAlmostEqual(imposto_sobre_ganho(0.2, 100.0), 20.0)


class TesteTaxaAdm(unittest.TestCase):
    def test_sobre_aporte(self):
        d = valor_taxa_adm("aporte", 0.02, 0.0, 0.0, 1000.0, 12)
        self.assertAlmostEqual(d, 20.0)

    def test_sobre_patrimonio_um_ano(self):
        d = valor_taxa_adm("patrimonio", 0.10, 1000.0, 0.0, 1000.0, 12)
        self.assertAlmostEqual(d, 100.0)

    def test_sobre_patrimonio_dois_anos(self):
        d = valor_taxa_adm("patrimonio", 0.10, 1000.0, 0.0, 1000.0, 24)
        self.assertAlmostEqual(d, 1000.0 * (1 - 0.9 ** 2))

    def test_escala_taxa_adm(self):
        # Uma taxa de administração de 0,03% sobre R$ 10 mil por 1 ano ≈ R$ 3.
        d = valor_taxa_adm("patrimonio", 0.0003, 10000.0, 0.0, 10000.0, 12)
        self.assertAlmostEqual(d, 3.0, places=6)

    def test_sobre_ganho(self):
        d = valor_taxa_adm("ganho", 0.20, 0.0, 500.0, 1000.0, 12)
        self.assertAlmostEqual(d, 100.0)

    def test_sem_taxa(self):
        self.assertEqual(valor_taxa_adm("nenhuma", 0.5, 100.0, 50.0, 10.0, 12), 0.0)


if __name__ == "__main__":
    unittest.main()
