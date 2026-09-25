"""Testes dos auxiliares matriciais (validados contra implementações escalares)."""

import unittest
import numpy as np

from src.instrumentos import Ativo
from src.desempenho import calcular_ativo, MetricasAtivo
from src import matriz
from src import matematica_financeira as mf
from src import instrumentos


def ativo_simples(nome, taxa, prazo=12, **extra) -> Ativo:
    padrao = dict(taxa=taxa, prazo_meses=prazo, modo_imposto="isento", modo_taxa="nenhuma")
    padrao.update(extra)
    return Ativo(nome=nome, **padrao)


class TesteVetorRetornosLiquidos(unittest.TestCase):
    def test_confere_com_escalar(self):
        ativos = [
            ativo_simples("A", 0.10),
            ativo_simples("B", 0.05),
            ativo_simples("C", 0.12, modo_imposto="fixo", imposto_pct=0.20),
        ]
        r_vet = matriz.vetor_retornos_liquidos(ativos)
        for i, a in enumerate(ativos):
            r_esc = instrumentos.retorno_liquido_anualizado(a)
            self.assertAlmostEqual(r_vet[i], r_esc, places=10)


class TesteMontarMatrizFluxos(unittest.TestCase):
    def test_formato_matriz(self):
        a = calcular_ativo(ativo_simples("A", 0.10), 1000.0, 0.0, 0.05, 0.04)
        b = calcular_ativo(ativo_simples("B", 0.06), 500.0, 100.0, 0.05, 0.04)
        mets = [a, b]
        H = max(len(i.projecao) - 1 for i in mets)
        P = matriz.montar_matriz_fluxos(mets, H)
        self.assertEqual(P.shape, (2, H + 1))
        self.assertEqual(P[0, 0], 0.0)
        self.assertEqual(P[1, 0], 0.0)

    def test_soma_eixo_zero_confere_com_laco(self):
        a = calcular_ativo(ativo_simples("A", 0.10), 1000.0, 0.0, 0.05, 0.04)
        b = calcular_ativo(ativo_simples("B", 0.06), 500.0, 100.0, 0.05, 0.04)
        mets = [a, b]
        H = max(len(i.projecao) - 1 for i in mets)
        P = matriz.montar_matriz_fluxos(mets, H)
        saidas_mat = P.sum(axis=0)

        # Referência por laço
        saidas_laco = [0.0] * (H + 1)
        prazos = [len(i.projecao) - 1 for i in mets]
        mensais = [i.aporte_mensal for i in mets]
        for idx, prazo in enumerate(prazos):
            for t in range(1, prazo + 1):
                saidas_laco[t] += mensais[idx]

        for t in range(H + 1):
            self.assertAlmostEqual(saidas_mat[t], saidas_laco[t], places=10)


class TesteVplCarteira(unittest.TestCase):
    def test_vpl_confere_com_laco(self):
        a = calcular_ativo(ativo_simples("A", 0.10), 800.0, 0.0, 0.05, 0.04)
        b = calcular_ativo(ativo_simples("B", 0.06), 200.0, 0.0, 0.05, 0.04)
        mets = [a, b]
        H = max(len(i.projecao) - 1 for i in mets)
        minima_mensal = mf.taxa_mensal_equivalente(0.05)

        P = matriz.montar_matriz_fluxos(mets, H)
        saidas = P.sum(axis=0)
        # Estende as projeções até H
        from src.desempenho import _estender_projecao, _taxa_mensal_por_metricas
        estendida = [_estender_projecao(i.projecao, H, _taxa_mensal_por_metricas(i)) for i in mets]
        liquido_h = sum(pj[H]["valor_liquido"] for pj in estendida)
        total_inicial = sum(i.aporte_inicial for i in mets)

        vpl_mat = matriz.vpl_carteira(saidas, liquido_h, total_inicial, 0.05, H)

        # Referência por laço
        vpl_laco = -total_inicial
        for t in range(1, H + 1):
            vpl_laco += -saidas[t] / (1.0 + minima_mensal) ** t
        vpl_laco += liquido_h / (1.0 + minima_mensal) ** H

        self.assertAlmostEqual(vpl_mat, vpl_laco, places=10)


class TesteAlocacaoVetorizada(unittest.TestCase):
    def test_alocacao_simples(self):
        taxas = np.array([0.10, 0.05, 0.03])
        minimos = np.array([0.0, 0.0, 0.0])
        maximos = np.array([np.inf, np.inf, np.inf])
        capital = 1000.0

        aloc = matriz.alocacao_vetorizada(capital, taxas, minimos, maximos)
        # Tudo deve ir para o primeiro (maior taxa)
        self.assertAlmostEqual(aloc[0], 1000.0)
        self.assertAlmostEqual(aloc[1], 0.0)
        self.assertAlmostEqual(aloc[2], 0.0)

    def test_respeita_maximo(self):
        taxas = np.array([0.10, 0.05])
        minimos = np.array([0.0, 0.0])
        maximos = np.array([600.0, np.inf])
        capital = 1000.0

        aloc = matriz.alocacao_vetorizada(capital, taxas, minimos, maximos)
        self.assertAlmostEqual(aloc[0], 600.0)
        self.assertAlmostEqual(aloc[1], 400.0)

    def test_respeita_minimo(self):
        taxas = np.array([0.10, 0.05])
        minimos = np.array([0.0, 400.0])
        maximos = np.array([np.inf, np.inf])
        capital = 1000.0

        aloc = matriz.alocacao_vetorizada(capital, taxas, minimos, maximos)
        self.assertAlmostEqual(aloc[1], 400.0)  # mínimo garantido
        self.assertAlmostEqual(aloc[0], 600.0)  # resto para o melhor

    def test_reserva_fica_com_resto(self):
        taxas = np.array([0.02, 0.03])  # mínima = 0.03, ativo 0 abaixo
        minimos = np.array([0.0, 0.0])
        maximos = np.array([np.inf, np.inf])
        capital = 500.0

        aloc = matriz.alocacao_vetorizada(capital, taxas, minimos, maximos)
        self.assertAlmostEqual(aloc[0], 0.0)
        self.assertAlmostEqual(aloc[1], 500.0)


class TesteValoresVetorizados(unittest.TestCase):
    def test_vetor_aporte_unico(self):
        principais = np.array([1000.0, 500.0, 200.0])
        taxas = np.array([0.10, 0.05, 0.12])
        prazos = np.array([12, 24, 6])

        res = matriz.vetor_aporte_unico(principais, taxas, prazos)
        for i in range(3):
            esperado = mf.valor_futuro_aporte_unico(principais[i], taxas[i], prazos[i])
            self.assertAlmostEqual(res[i], esperado, places=10)

    def test_vetor_serie(self):
        pmts = np.array([100.0, 200.0, 50.0])
        mensais = np.array([0.01, 0.005, 0.02])
        n_meses = np.array([12, 24, 6])

        res = matriz.vetor_serie_postecipada(pmts, mensais, n_meses)
        for i in range(3):
            esperado = mf.valor_futuro_serie_postecipada(pmts[i], mensais[i], n_meses[i])
            self.assertAlmostEqual(res[i], esperado, places=10)

    def test_vetor_fator_serie_descontada(self):
        mensais = np.array([0.01, 0.005, 0.0])
        n_meses = np.array([12, 24, 6])

        res = matriz.vetor_fator_serie_descontada(mensais, n_meses)
        for i in range(3):
            esperado = mf.fator_serie_descontada(mensais[i], n_meses[i])
            self.assertAlmostEqual(res[i], esperado, places=10)


class TesteMatrizFeatures(unittest.TestCase):
    def test_extrair_features(self):
        ativos = [
            ativo_simples("A", 0.10, prazo=12),
            ativo_simples("B", 0.05, prazo=24, modo_imposto="fixo", imposto_pct=0.20),
        ]
        X = matriz.extrair_caracteristicas_ativos(ativos)
        self.assertEqual(X.shape, (2, 8))
        self.assertAlmostEqual(X[0, 0], 0.10)  # taxa_anual
        self.assertAlmostEqual(X[0, 1], 12.0)  # prazo_meses
        self.assertAlmostEqual(X[1, 2], 0.20)  # aliquota


if __name__ == "__main__":
    unittest.main()
