import unittest

from src.instrumentos import Ativo
from src.geometria_pl import construir_modelo_pl, descrever_modelo_pl
from src.otimizador_carteira import OtimizadorCarteira
from web import graficos


def criar_ativo(nome, taxa, prazo=12, **extra) -> Ativo:
    padrao = dict(taxa=taxa, prazo_meses=prazo, modo_imposto="isento", modo_taxa="nenhuma")
    padrao.update(extra)
    return Ativo(nome=nome, **padrao)


class TesteGeometriaPL(unittest.TestCase):
    def _resolver(self, ativos, capital, **kw):
        kw.setdefault("taxa_minima_anual", 0.03)
        kw.setdefault("inflacao_anual", 0.0)
        return OtimizadorCarteira(ativos, capital_inicial=capital, **kw).resolver()

    def test_vertices_e_otimo_dois_ativos(self):
        a = criar_ativo("A", 0.10)
        b = criar_ativo("B", 0.05)
        res = self._resolver([a, b], 1000.0)
        modelo = construir_modelo_pl(res)
        self.assertTrue(modelo.viavel)
        self.assertEqual(modelo.ativo_x, "A")  # mais eficiente no eixo x
        self.assertEqual(modelo.ativo_y, "B")
        # Caixa [0,1000]^2 cortada por x1+x2<=1000 -> triângulo (0,0),(1000,0),(0,1000).
        self.assertEqual(len(modelo.vertices), 3)
        # Todo o capital em A: ótimo (1000, 0) com Z = 100.
        self.assertAlmostEqual(modelo.otimo["x1"], 1000.0)
        self.assertAlmostEqual(modelo.otimo["x2"], 0.0)
        self.assertAlmostEqual(modelo.otimo["z"], 100.0)
        self.assertFalse(modelo.otimo_aresta)

    def test_otimo_confere_com_guloso(self):
        a = criar_ativo("A", 0.10, maximo_inicial=600.0)
        b = criar_ativo("B", 0.05, maximo_inicial=100.0)
        res = self._resolver([a, b], 1000.0)
        modelo = construir_modelo_pl(res)
        self.assertTrue(modelo.viavel)
        por_nome = {m.nome: m for m in res.metricas}
        # O ótimo projetado coincide com o guloso nestes eixos aqui.
        self.assertAlmostEqual(modelo.otimo["x1"], por_nome["A"].aporte_inicial)
        self.assertAlmostEqual(modelo.otimo["x2"], por_nome["B"].aporte_inicial)

    def test_aresta_otima_taxas_iguais(self):
        a = criar_ativo("A", 0.08)
        b = criar_ativo("B", 0.08)
        res = self._resolver([a, b], 1000.0)
        modelo = construir_modelo_pl(res)
        self.assertTrue(modelo.viavel)
        self.assertTrue(modelo.otimo_aresta)
        self.assertTrue(all(v["otimo"] or v["z"] <= modelo.z_estrela + 1e-6
                            for v in modelo.vertices))

    def test_ativo_unico_recai_na_reserva(self):
        a = criar_ativo("A", 0.10)
        res = self._resolver([a], 500.0)
        modelo = construir_modelo_pl(res)
        self.assertTrue(modelo.viavel)
        self.assertIn("Reserva", modelo.ativo_y)

    def test_sem_capital_retorna_none(self):
        res = self._resolver([criar_ativo("A", 0.10)], 0.0)
        self.assertIsNone(construir_modelo_pl(res))

    def test_descricao_e_serializavel(self):
        import json
        a = criar_ativo("A", 0.10)
        b = criar_ativo("B", 0.05)
        res = self._resolver([a, b], 1000.0)
        d = descrever_modelo_pl(construir_modelo_pl(res))
        json.dumps(d)  # não deve lançar
        self.assertIn("máx Z", d["objetivo"])
        self.assertTrue(d["restricoes"])
        self.assertTrue(d["vertices"])
        self.assertTrue(d["passos"])
        self.assertIn("tangente", d)

    def test_grafico_renderiza_png(self):
        a = criar_ativo("A", 0.10)
        b = criar_ativo("B", 0.05)
        res = self._resolver([a, b], 1000.0)
        uri = graficos.grafico_max_pl(construir_modelo_pl(res))
        self.assertTrue(uri.startswith("data:image/png;base64,"))

    def test_grafico_none_sem_modelo(self):
        self.assertIsNone(graficos.grafico_max_pl(None))


if __name__ == "__main__":
    unittest.main()
