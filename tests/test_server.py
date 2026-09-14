import unittest

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from server import app
from web.schema import ATIVOS_EXEMPLO

client = TestClient(app)


def payload_cenario(**over):
    p = {
        "capital": 10000.0,
        "usar_mensal": True,
        "aporte_mensal": 500.0,
        "tma_modo": "auto",
        "selic_pct": 10.5,
        "ipca_pct": 4.5,
        "tma_manual_pct": 5.5,
        "inflacao_pct": 4.5,
        "ativos": ATIVOS_EXEMPLO,
    }
    p.update(over)
    return p


class TestApiExemplos(unittest.TestCase):
    def test_exemplos(self):
        r = client.get("/api/exemplos")
        self.assertEqual(r.status_code, 200)
        self.assertGreaterEqual(len(r.json()["ativos"]), 4)


class TestApiOtimizar(unittest.TestCase):
    def test_otimiza_carteira_exemplo(self):
        r = client.post("/api/otimizar", json=payload_cenario())
        self.assertEqual(r.status_code, 200)
        j = r.json()
        self.assertIsNone(j["erro"])
        self.assertEqual(j["cenario"]["capital_inicial"], 10000.0)
        self.assertIsNotNone(j["carteira"])
        self.assertGreater(j["carteira"]["montante_liquido"], 0)
        self.assertTrue(j["indicadores"])
        self.assertTrue(any(i["reserva"] for i in j["indicadores"]))
        # graficos em PNG base64
        for k in ("alocacao", "patrimonio", "lucro_tma"):
            uri = j["graficos"][k]
            self.assertTrue(uri.startswith("data:image/png;base64,"))

    def test_otimiza_tma_manual(self):
        r = client.post(
            "/api/otimizar",
            json=payload_cenario(tma_modo="manual", tma_manual_pct=5.0, inflacao_pct=3.0),
        )
        self.assertEqual(r.status_code, 200)
        j = r.json()
        self.assertAlmostEqual(j["cenario"]["tma_pct"], 5.0)
        self.assertAlmostEqual(j["cenario"]["inflacao_pct"], 3.0)

    def test_minimos_excedem_capital_retorna_422(self):
        ativos = [
            {**ATIVOS_EXEMPLO[0], "inicial_min": 20000.0, "inicial_max": 0.0},
            {**ATIVOS_EXEMPLO[1], "inicial_min": 0.0, "inicial_max": 0.0},
        ]
        r = client.post("/api/otimizar", json=payload_cenario(capital=10000.0, ativos=ativos))
        self.assertEqual(r.status_code, 422)
        self.assertIn("erro", r.json())

    def test_periodo_invalido_retorna_422(self):
        ativos = [{**ATIVOS_EXEMPLO[0], "periodo": "decadal"}]
        r = client.post("/api/otimizar", json=payload_cenario(ativos=ativos))
        self.assertEqual(r.status_code, 422)


if __name__ == "__main__":
    unittest.main()