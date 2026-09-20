import unittest

from src.instruments import Asset
from src.lp_geometry import build_lp_model, describe_lp_model
from src.portfolio_optimizer import PortfolioOptimizer
from web import charts


def make_asset(name, rate, term=12, **extra) -> Asset:
    defaults = dict(rate=rate, term_months=term, tax_mode="exempt", fee_mode="none")
    defaults.update(extra)
    return Asset(name=name, **defaults)


class TestLPGeometry(unittest.TestCase):
    def _solve(self, assets, capital, **kw):
        kw.setdefault("hurdle_annual", 0.03)
        kw.setdefault("inflation_annual", 0.0)
        return PortfolioOptimizer(assets, initial_capital=capital, **kw).solve()

    def test_vertices_and_optimum_two_assets(self):
        a = make_asset("A", 0.10)
        b = make_asset("B", 0.05)
        res = self._solve([a, b], 1000.0)
        model = build_lp_model(res)
        self.assertTrue(model.feasible)
        self.assertEqual(model.asset_x, "A")  # most efficient on x-axis
        self.assertEqual(model.asset_y, "B")
        # Box [0,1000]^2 cut by x1+x2<=1000 -> triangle (0,0),(1000,0),(0,1000).
        self.assertEqual(len(model.vertices), 3)
        # All capital to A: optimum (1000, 0) with Z = 100.
        self.assertAlmostEqual(model.optimum["x1"], 1000.0)
        self.assertAlmostEqual(model.optimum["x2"], 0.0)
        self.assertAlmostEqual(model.optimum["z"], 100.0)
        self.assertFalse(model.edge_optimal)

    def test_optimum_matches_greedy_allocation(self):
        a = make_asset("A", 0.10, initial_max=600.0)
        b = make_asset("B", 0.05, initial_max=100.0)
        res = self._solve([a, b], 1000.0)
        model = build_lp_model(res)
        self.assertTrue(model.feasible)
        by_name = {m.name: m for m in res.metrics}
        # Projected optimum coincides with greedy on these axes here.
        self.assertAlmostEqual(model.optimum["x1"], by_name["A"].initial_contrib)
        self.assertAlmostEqual(model.optimum["x2"], by_name["B"].initial_contrib)

    def test_edge_optimal_equal_rates(self):
        a = make_asset("A", 0.08)
        b = make_asset("B", 0.08)
        res = self._solve([a, b], 1000.0)
        model = build_lp_model(res)
        self.assertTrue(model.feasible)
        self.assertTrue(model.edge_optimal)
        self.assertTrue(all(v["optimal"] or v["z"] <= model.z_star + 1e-6
                            for v in model.vertices))

    def test_single_asset_falls_back_to_reserve(self):
        a = make_asset("A", 0.10)
        res = self._solve([a], 500.0)
        model = build_lp_model(res)
        self.assertTrue(model.feasible)
        self.assertIn("Reserve", model.asset_y)

    def test_no_capital_returns_none(self):
        res = self._solve([make_asset("A", 0.10)], 0.0)
        self.assertIsNone(build_lp_model(res))

    def test_describe_is_json_serializable(self):
        import json
        a = make_asset("A", 0.10)
        b = make_asset("B", 0.05)
        res = self._solve([a, b], 1000.0)
        d = describe_lp_model(build_lp_model(res))
        json.dumps(d)  # must not raise
        self.assertIn("max Z", d["objective"])
        self.assertTrue(d["constraints"])
        self.assertTrue(d["vertices"])
        self.assertTrue(d["steps"])
        self.assertIn("tangent", d)

    def test_chart_renders_png(self):
        a = make_asset("A", 0.10)
        b = make_asset("B", 0.05)
        res = self._solve([a, b], 1000.0)
        uri = charts.lp_max_chart(build_lp_model(res))
        self.assertTrue(uri.startswith("data:image/png;base64,"))

    def test_chart_none_without_model(self):
        self.assertIsNone(charts.lp_max_chart(None))


if __name__ == "__main__":
    unittest.main()
