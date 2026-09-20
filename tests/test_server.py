import unittest

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from server import app
from web.schema import EXAMPLE_ASSETS

client = TestClient(app)


def scenario_payload(**overrides):
    p = {
        "capital": 10000.0,
        "use_monthly": True,
        "monthly_contrib": 500.0,
        "hurdle_mode": "auto",
        "risk_free_pct": 4.0,
        "inflation_pct": 2.5,
        "hurdle_manual_pct": 5.5,
        "assets": EXAMPLE_ASSETS,
    }
    p.update(overrides)
    return p


class TestPages(unittest.TestCase):
    def test_dashboard_page(self):
        r = client.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertIn("dashboard", r.text.lower())

    def test_assets_page(self):
        r = client.get("/assets")
        self.assertEqual(r.status_code, 200)
        self.assertIn("assets", r.text.lower())

    def test_shared_js(self):
        r = client.get("/static/app.js")
        self.assertEqual(r.status_code, 200)


class TestExamplesApi(unittest.TestCase):
    def test_examples(self):
        r = client.get("/api/examples")
        self.assertEqual(r.status_code, 200)
        self.assertGreaterEqual(len(r.json()["assets"]), 4)

    def test_examples_are_us_only(self):
        r = client.get("/api/examples")
        names = " ".join(a["name"] for a in r.json()["assets"])
        self.assertNotIn("Bund", names)
        self.assertNotIn("Euro", names)


class TestOptimizeApi(unittest.TestCase):
    def test_optimizes_sample_portfolio(self):
        r = client.post("/api/optimize", json=scenario_payload())
        self.assertEqual(r.status_code, 200)
        j = r.json()
        self.assertIsNone(j["error"])
        self.assertEqual(j["scenario"]["initial_capital"], 10000.0)
        self.assertIsNotNone(j["portfolio"])
        self.assertGreater(j["portfolio"]["net_amount"], 0)
        self.assertTrue(j["metrics"])
        self.assertTrue(any(i["is_reserve"] for i in j["metrics"]))
        # charts as base64 PNG
        for k in ("allocation", "allocation_pie", "equity", "profit_vs_hurdle", "lp_max"):
            uri = j["charts"][k]
            self.assertTrue(uri.startswith("data:image/png;base64,"))
        # LP plane: objective, vertices, optimum, and resolution steps
        lp = j["lp_model"]
        self.assertTrue(lp["feasible"])
        self.assertIn("max Z", lp["objective"])
        self.assertTrue(lp["vertices"])
        self.assertIn("vertex", lp["optimum"])
        self.assertTrue(lp["steps"])

    def test_optimizes_manual_hurdle(self):
        r = client.post(
            "/api/optimize",
            json=scenario_payload(hurdle_mode="manual", hurdle_manual_pct=5.0, inflation_pct=3.0),
        )
        self.assertEqual(r.status_code, 200)
        j = r.json()
        self.assertAlmostEqual(j["scenario"]["hurdle_pct"], 5.0)
        self.assertAlmostEqual(j["scenario"]["inflation_pct"], 3.0)

    def test_minimums_above_capital_return_422(self):
        assets = [
            {**EXAMPLE_ASSETS[0], "initial_min": 20000.0, "initial_max": 0.0},
            {**EXAMPLE_ASSETS[1], "initial_min": 0.0, "initial_max": 0.0},
        ]
        r = client.post("/api/optimize", json=scenario_payload(capital=10000.0, assets=assets))
        self.assertEqual(r.status_code, 422)
        self.assertIn("error", r.json())

    def test_invalid_period_returns_422(self):
        assets = [{**EXAMPLE_ASSETS[0], "period": "decadal"}]
        r = client.post("/api/optimize", json=scenario_payload(assets=assets))
        self.assertEqual(r.status_code, 422)


if __name__ == "__main__":
    unittest.main()
