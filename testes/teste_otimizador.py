import unittest

from src.instrumentos import Ativo
from src.otimizador_carteira import OtimizadorCarteira


def criar_ativo(nome, taxa, prazo=12, **extra) -> Ativo:
    padrao = dict(taxa=taxa, prazo_meses=prazo, modo_imposto="isento", modo_taxa="nenhuma")
    padrao.update(extra)
    return Ativo(nome=nome, **padrao)


class TesteAlocacaoInicial(unittest.TestCase):
    def test_tudo_para_melhor_ativo(self):
        a = criar_ativo("A", 0.10)
        b = criar_ativo("B", 0.05)
        res = OtimizadorCarteira([a, b], capital_inicial=1000.0, taxa_minima_anual=0.03, inflacao_anual=0.0).resolver()
        por_nome = {i.nome: i for i in res.metricas}
        self.assertAlmostEqual(por_nome["A"].aporte_inicial, 1000.0)
        self.assertAlmostEqual(por_nome["B"].aporte_inicial, 0.0)
        self.assertAlmostEqual(por_nome["Reserva (taxa mínima)"].aporte_inicial, 0.0)

    def test_respeita_teto_e_reserva_fica_com_resto(self):
        a = criar_ativo("A", 0.10, maximo_inicial=600.0)
        b = criar_ativo("B", 0.05, maximo_inicial=100.0)
        res = OtimizadorCarteira([a, b], capital_inicial=1000.0, taxa_minima_anual=0.03, inflacao_anual=0.0).resolver()
        por_nome = {i.nome: i for i in res.metricas}
        self.assertAlmostEqual(por_nome["A"].aporte_inicial, 600.0)
        self.assertAlmostEqual(por_nome["B"].aporte_inicial, 100.0)
        self.assertAlmostEqual(por_nome["Reserva (taxa mínima)"].aporte_inicial, 300.0)

    def test_reserva_supera_ativo_abaixo_da_minima(self):
        fraco = criar_ativo("Fraco", 0.02)  # taxa líquida abaixo da mínima de 3%
        res = OtimizadorCarteira([fraco], capital_inicial=500.0, taxa_minima_anual=0.03, inflacao_anual=0.0).resolver()
        por_nome = {i.nome: i for i in res.metricas}
        self.assertAlmostEqual(por_nome["Fraco"].aporte_inicial, 0.0)
        self.assertAlmostEqual(por_nome["Reserva (taxa mínima)"].aporte_inicial, 500.0)

    def test_minimo_e_diversificacao_obrigatoria(self):
        a = criar_ativo("A", 0.10)
        b = criar_ativo("B", 0.05, minimo_inicial=400.0)
        res = OtimizadorCarteira([a, b], capital_inicial=1000.0, taxa_minima_anual=0.03, inflacao_anual=0.0).resolver()
        por_nome = {i.nome: i for i in res.metricas}
        self.assertAlmostEqual(por_nome["B"].aporte_inicial, 400.0)  # mínimo garantido
        self.assertAlmostEqual(por_nome["A"].aporte_inicial, 600.0)  # resto para o melhor

    def test_minimo_acima_do_orcamento_da_erro(self):
        a = criar_ativo("A", 0.10)
        b = criar_ativo("B", 0.05, minimo_inicial=1200.0)
        res = OtimizadorCarteira([a, b], capital_inicial=1000.0, taxa_minima_anual=0.03, inflacao_anual=0.0).resolver()
        self.assertTrue(res.erro)


class TesteAlocacaoMensal(unittest.TestCase):
    def test_distribui_aporte_mensal(self):
        a = criar_ativo("A", 0.10, usa_mensal=True, maximo_mensal=200.0)
        b = criar_ativo("B", 0.05, usa_mensal=True, maximo_mensal=150.0)
        res = OtimizadorCarteira(
            [a, b], capital_inicial=0.0, taxa_minima_anual=0.03, inflacao_anual=0.0,
            aporte_mensal=300.0, usar_mensal=True,
        ).resolver()
        por_nome = {i.nome: i for i in res.metricas}
        self.assertAlmostEqual(por_nome["A"].aporte_mensal, 200.0)
        self.assertAlmostEqual(por_nome["B"].aporte_mensal, 100.0)
        self.assertAlmostEqual(por_nome["Reserva (taxa mínima)"].aporte_mensal, 0.0)

    def test_ativo_sem_mensal_e_ignorado(self):
        a = criar_ativo("A", 0.10, usa_mensal=False, maximo_mensal=200.0)
        res = OtimizadorCarteira(
            [a], capital_inicial=1000.0, taxa_minima_anual=0.03, inflacao_anual=0.0,
            aporte_mensal=300.0, usar_mensal=True,
        ).resolver()
        por_nome = {i.nome: i for i in res.metricas}
        self.assertAlmostEqual(por_nome["A"].aporte_inicial, 1000.0)
        self.assertAlmostEqual(por_nome["A"].aporte_mensal, 0.0)
        self.assertAlmostEqual(por_nome["Reserva (taxa mínima)"].aporte_mensal, 300.0)


class TesteComImposto(unittest.TestCase):
    def test_imposto_maior_reduz_prioridade(self):
        a = criar_ativo("A", 0.15, modo_imposto="fixo", imposto_pct=0.5)  # taxa líquida reduzida
        b = criar_ativo("B", 0.09)  # isento
        res = OtimizadorCarteira([a, b], capital_inicial=1000.0, taxa_minima_anual=0.03, inflacao_anual=0.0).resolver()
        por_nome = {i.nome: i for i in res.metricas}
        # 15% bruto com 50% de imposto -> ~8,1% líquido; B isento a 9% -> B leva tudo.
        self.assertAlmostEqual(por_nome["A"].aporte_inicial, 0.0)
        self.assertAlmostEqual(por_nome["B"].aporte_inicial, 1000.0)


class TesteCarteiraComposta(unittest.TestCase):
    def test_metricas_carteira_consistentes(self):
        a = criar_ativo("A", 0.10, maximo_inicial=500.0, usa_mensal=True, maximo_mensal=100.0)
        res = OtimizadorCarteira(
            [a], capital_inicial=800.0, taxa_minima_anual=0.05, inflacao_anual=0.04,
            aporte_mensal=100.0, usar_mensal=True,
        ).resolver()
        self.assertEqual(res.erro, "")
        c = res.carteira
        # capital inicial = 500 (ativo A) + 300 (reserva) = 800
        self.assertAlmostEqual(c.capital_inicial, 800.0)
        self.assertAlmostEqual(c.reserva, 300.0)
        self.assertGreater(c.valor_liquido, 0.0)
        self.assertIsNotNone(c.tir_anual)


if __name__ == "__main__":
    unittest.main()
