import unittest

from src.tax import (
    aliquota_imposto,
    aliquota_ir_tabela,
    imposto_sobre_taxa,
    taxa_admin_em_reais,
)


class TestImposto(unittest.TestCase):
    def test_ir_tabela_faixas(self):
        self.assertAlmostEqual(aliquota_ir_tabela(180), 0.225)
        self.assertAlmostEqual(aliquota_ir_tabela(181), 0.200)
        self.assertAlmostEqual(aliquota_ir_tabela(360), 0.200)
        self.assertAlmostEqual(aliquota_ir_tabela(361), 0.175)
        self.assertAlmostEqual(aliquota_ir_tabela(720), 0.175)
        self.assertAlmostEqual(aliquota_ir_tabela(721), 0.150)

    def test_aliquota_tabela_por_prazo_meses(self):
        self.assertAlmostEqual(aliquota_imposto("ir_tabela", 6, None), aliquota_ir_tabela(180))
        self.assertAlmostEqual(aliquota_imposto("isento", 12, None), 0.0)
        self.assertAlmostEqual(aliquota_imposto("fixo", 12, 0.15), 0.15)

    def test_imposto_nao_incide_sobre_prejuizo(self):
        self.assertEqual(imposto_sobre_taxa(0.2, -50.0), 0.0)
        self.assertAlmostEqual(imposto_sobre_taxa(0.2, 100.0), 20.0)


class TestTaxaAdministrativa(unittest.TestCase):
    def test_sobre_aporte(self):
        d = taxa_admin_em_reais("aporte", 0.02, 0.0, 0.0, 1000.0, 12)
        self.assertAlmostEqual(d, 20.0)

    def test_sobre_patrimonio_anual(self):
        d = taxa_admin_em_reais("patrimonio", 0.10, 1000.0, 0.0, 1000.0, 12)
        self.assertAlmostEqual(d, 100.0)

    def test_sobre_patrimonio_dois_anos(self):
        d = taxa_admin_em_reais("patrimonio", 0.10, 1000.0, 0.0, 1000.0, 24)
        self.assertAlmostEqual(d, 1000.0 * (1 - 0.9 ** 2))

    def test_sobre_rendimento(self):
        d = taxa_admin_em_reais("rendimento", 0.20, 0.0, 500.0, 1000.0, 12)
        self.assertAlmostEqual(d, 100.0)

    def test_sem_taxa(self):
        self.assertEqual(taxa_admin_em_reais("nenhuma", 0.5, 100.0, 50.0, 10.0, 12), 0.0)


if __name__ == "__main__":
    unittest.main()