"""Testes das funcoes matriciais (validacao contra implementacoes escalares)."""

import unittest
import numpy as np

from src.instruments import Ativo
from src.performance import calcular_ativo, IndicadoresAtivo
from src import matrix
from src import math_finance as mf
from src import instruments


def ativo_simples(nome, taxa, prazo=12, **extra) -> Ativo:
    defaults = dict(taxa=taxa, prazo_meses=prazo, imposto_modo="isento", admin_modo="nenhuma")
    defaults.update(extra)
    return Ativo(nome=nome, **defaults)


class TestTaxasLiquidasVetor(unittest.TestCase):
    def test_bate_com_escalar(self):
        ativos = [
            ativo_simples("A", 0.10),
            ativo_simples("B", 0.05),
            ativo_simples("C", 0.12, imposto_modo="fixo", imposto_percentual=0.20),
        ]
        r_vec = matrix.taxas_liquidas_vetor(ativos)
        for i, a in enumerate(ativos):
            r_esc = instruments.taxa_liquida_anualizada(a)
            self.assertAlmostEqual(r_vec[i], r_esc, places=10)


class TestConstruirMatrizFluxos(unittest.TestCase):
    def test_matriz_formato_correto(self):
        a = calcular_ativo(ativo_simples("A", 0.10), 1000.0, 0.0, 0.05, 0.04)
        b = calcular_ativo(ativo_simples("B", 0.06), 500.0, 100.0, 0.05, 0.04)
        inds = [a, b]
        H = max(len(i.projecao) - 1 for i in inds)
        P = matrix.construir_matriz_fluxos(inds, H)
        self.assertEqual(P.shape, (2, H + 1))
        self.assertEqual(P[0, 0], 0.0)
        self.assertEqual(P[1, 0], 0.0)

    def test_soma_eixo_zero_bate_com_loop(self):
        a = calcular_ativo(ativo_simples("A", 0.10), 1000.0, 0.0, 0.05, 0.04)
        b = calcular_ativo(ativo_simples("B", 0.06), 500.0, 100.0, 0.05, 0.04)
        inds = [a, b]
        H = max(len(i.projecao) - 1 for i in inds)
        P = matrix.construir_matriz_fluxos(inds, H)
        outflows_mat = P.sum(axis=0)

        # Referencia loop
        outflows_loop = [0.0] * (H + 1)
        prazos = [len(i.projecao) - 1 for i in inds]
        p_meses = [i.aporte_mensal for i in inds]
        for idx, prazo in enumerate(prazos):
            for t in range(1, prazo + 1):
                outflows_loop[t] += p_meses[idx]

        for t in range(H + 1):
            self.assertAlmostEqual(outflows_mat[t], outflows_loop[t], places=10)


class TestVPLCarteira(unittest.TestCase):
    def test_vpl_bate_com_loop(self):
        a = calcular_ativo(ativo_simples("A", 0.10), 800.0, 0.0, 0.05, 0.04)
        b = calcular_ativo(ativo_simples("B", 0.06), 200.0, 0.0, 0.05, 0.04)
        inds = [a, b]
        H = max(len(i.projecao) - 1 for i in inds)
        i_tma = mf.taxa_mensal_equivalente(0.05)

        P = matrix.construir_matriz_fluxos(inds, H)
        outflows = P.sum(axis=0)
        ml_h = sum(pj[H]["montante_liquido"] for pj in [
            a.projecao, b.projecao
        ])
        # Ajustar projecao ate H
        from src.performance import _projecao_ate, _taxa_mensal_do_indicador
        proj_est = [_projecao_ate(i.projecao, H, _taxa_mensal_do_indicador(i)) for i in inds]
        ml_h = sum(pj[H]["montante_liquido"] for pj in proj_est)
        a_tot = sum(i.aporte_inicial for i in inds)

        vpl_mat = matrix.vpl_carteira(outflows, ml_h, a_tot, 0.05, H)

        # Referencia loop
        vpl_loop = -a_tot
        for t in range(1, H + 1):
            vpl_loop += -outflows[t] / (1.0 + i_tma) ** t
        vpl_loop += ml_h / (1.0 + i_tma) ** H

        self.assertAlmostEqual(vpl_mat, vpl_loop, places=10)


class TestAlocarVetorizada(unittest.TestCase):
    def test_alocacao_simples(self):
        taxas = np.array([0.10, 0.05, 0.03])
        mins = np.array([0.0, 0.0, 0.0])
        maxs = np.array([np.inf, np.inf, np.inf])
        capital = 1000.0

        aloc = matrix.alocar_vetorizada(capital, taxas, mins, maxs)
        # Tudo deve ir para o primeiro (maior taxa)
        self.assertAlmostEqual(aloc[0], 1000.0)
        self.assertAlmostEqual(aloc[1], 0.0)
        self.assertAlmostEqual(aloc[2], 0.0)

    def test_respeita_maximo(self):
        taxas = np.array([0.10, 0.05])
        mins = np.array([0.0, 0.0])
        maxs = np.array([600.0, np.inf])
        capital = 1000.0

        aloc = matrix.alocar_vetorizada(capital, taxas, mins, maxs)
        self.assertAlmostEqual(aloc[0], 600.0)
        self.assertAlmostEqual(aloc[1], 400.0)

    def test_respeita_minimo(self):
        taxas = np.array([0.10, 0.05])
        mins = np.array([0.0, 400.0])
        maxs = np.array([np.inf, np.inf])
        capital = 1000.0

        aloc = matrix.alocar_vetorizada(capital, taxas, mins, maxs)
        self.assertAlmostEqual(aloc[1], 400.0)  # minimo garantido
        self.assertAlmostEqual(aloc[0], 600.0)  # resto no melhor

    def test_reserva_recebe_resto(self):
        taxas = np.array([0.02, 0.03])  # TMA = 0.03, ativo 0 abaixo
        mins = np.array([0.0, 0.0])
        maxs = np.array([np.inf, np.inf])
        capital = 500.0

        aloc = matrix.alocar_vetorizada(capital, taxas, mins, maxs)
        self.assertAlmostEqual(aloc[0], 0.0)
        self.assertAlmostEqual(aloc[1], 500.0)


class TestMontanteVetorizado(unittest.TestCase):
    def test_montante_aporte_unico_vetor(self):
        valores = np.array([1000.0, 500.0, 200.0])
        taxas = np.array([0.10, 0.05, 0.12])
        prazos = np.array([12, 24, 6])

        res = matrix.montante_aporte_unico_vetor(valores, taxas, prazos)
        for i in range(3):
            esper = mf.montante_aporte_unico(valores[i], taxas[i], prazos[i])
            self.assertAlmostEqual(res[i], esper, places=10)

    def test_montante_serie_vetor(self):
        pmts = np.array([100.0, 200.0, 50.0])
        taxas_m = np.array([0.01, 0.005, 0.02])
        n_meses = np.array([12, 24, 6])

        res = matrix.montante_serie_postecipada_vetor(pmts, taxas_m, n_meses)
        for i in range(3):
            esper = mf.montante_serie_postecipada(pmts[i], taxas_m[i], n_meses[i])
            self.assertAlmostEqual(res[i], esper, places=10)

    def test_fator_serie_descontada_vetor(self):
        taxas_m = np.array([0.01, 0.005, 0.0])
        n_meses = np.array([12, 24, 6])

        res = matrix.fator_serie_descontada_vetor(taxas_m, n_meses)
        for i in range(3):
            esper = mf.fator_serie_descontada(taxas_m[i], n_meses[i])
            self.assertAlmostEqual(res[i], esper, places=10)


class TestMatrizAtributos(unittest.TestCase):
    def test_extrair_atributos(self):
        ativos = [
            ativo_simples("A", 0.10, prazo=12),
            ativo_simples("B", 0.05, prazo=24, imposto_modo="fixo", imposto_percentual=0.20),
        ]
        X = matrix.extrair_atributos_ativos(ativos)
        self.assertEqual(X.shape, (2, 8))
        self.assertAlmostEqual(X[0, 0], 0.10)  # taxa_anual
        self.assertAlmostEqual(X[0, 1], 12.0)  # prazo_meses
        self.assertAlmostEqual(X[1, 2], 0.20)  # aliquota_imposto


if __name__ == "__main__":
    unittest.main()