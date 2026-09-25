import unittest

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from servidor import app
from web.esquema import ATIVOS_EXEMPLO

cliente = TestClient(app)


def payload_cenario(**sobrescritas):
    p = {
        "capital_inicial": 10000.0,
        "usar_mensal": True,
        "aporte_mensal": 500.0,
        "modo_taxa_minima": "auto",
        "taxa_livre_risco_pct": 15.0,
        "inflacao_pct": 5.0,
        "taxa_minima_manual_pct": 10.0,
        "ativos": ATIVOS_EXEMPLO,
    }
    p.update(sobrescritas)
    return p


class TestePaginas(unittest.TestCase):
    def test_pagina_painel(self):
        r = cliente.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertIn("painel", r.text.lower())

    def test_pagina_ativos(self):
        r = cliente.get("/ativos")
        self.assertEqual(r.status_code, 200)
        self.assertIn("ativos", r.text.lower())

    def test_js_compartilhado(self):
        r = cliente.get("/static/app.js")
        self.assertEqual(r.status_code, 200)


class TesteApiExemplos(unittest.TestCase):
    def test_exemplos(self):
        r = cliente.get("/api/exemplos")
        self.assertEqual(r.status_code, 200)
        self.assertGreaterEqual(len(r.json()["ativos"]), 4)

    def test_exemplos_sao_br(self):
        r = cliente.get("/api/exemplos")
        nomes = " ".join(a["nome"] for a in r.json()["ativos"])
        self.assertIn("Tesouro", nomes)
        self.assertNotIn("Treasury", nomes)
        self.assertNotIn("S&P", nomes)


class TesteApiOtimizar(unittest.TestCase):
    def test_otimiza_carteira_exemplo(self):
        r = cliente.post("/api/otimizar", json=payload_cenario())
        self.assertEqual(r.status_code, 200)
        j = r.json()
        self.assertIsNone(j["erro"])
        self.assertEqual(j["cenario"]["capital_inicial"], 10000.0)
        self.assertIsNotNone(j["carteira"])
        self.assertGreater(j["carteira"]["valor_liquido"], 0)
        self.assertTrue(j["metricas"])
        self.assertTrue(any(i["eh_reserva"] for i in j["metricas"]))
        # gráficos em PNG base64
        for k in ("alocacao", "alocacao_pizza", "evolucao", "lucro_vs_taxa_minima", "pl_max"):
            uri = j["graficos"][k]
            self.assertTrue(uri.startswith("data:image/png;base64,"))
        # Plano do PL: objetivo, vértices, ótimo e passos de resolução
        pl = j["modelo_pl"]
        self.assertTrue(pl["viavel"])
        self.assertIn("máx Z", pl["objetivo"])
        self.assertTrue(pl["vertices"])
        self.assertIn("vertice", pl["otimo"])
        self.assertTrue(pl["passos"])

    def test_otimiza_minima_manual(self):
        r = cliente.post(
            "/api/otimizar",
            json=payload_cenario(modo_taxa_minima="manual", taxa_minima_manual_pct=5.0, inflacao_pct=3.0),
        )
        self.assertEqual(r.status_code, 200)
        j = r.json()
        self.assertAlmostEqual(j["cenario"]["taxa_minima_pct"], 5.0)
        self.assertAlmostEqual(j["cenario"]["inflacao_pct"], 3.0)

    def test_minimos_acima_do_capital_retorna_422(self):
        ativos = [
            {**ATIVOS_EXEMPLO[0], "minimo_inicial": 20000.0, "maximo_inicial": 0.0},
            {**ATIVOS_EXEMPLO[1], "minimo_inicial": 0.0, "maximo_inicial": 0.0},
        ]
        r = cliente.post("/api/otimizar", json=payload_cenario(capital_inicial=10000.0, ativos=ativos))
        self.assertEqual(r.status_code, 422)
        self.assertIn("erro", r.json())

    def test_periodo_invalido_retorna_422(self):
        ativos = [{**ATIVOS_EXEMPLO[0], "periodo": "decadal"}]
        r = cliente.post("/api/otimizar", json=payload_cenario(ativos=ativos))
        self.assertEqual(r.status_code, 422)


if __name__ == "__main__":
    unittest.main()
