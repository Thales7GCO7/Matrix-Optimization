import unittest

from src.instruments import Asset, asset_summary
from src.math_finance import lump_sum_future_value
from src.performance import compute_asset, compute_portfolio


def simple_asset(name, rate, term=12, **extra) -> Asset:
    defaults = dict(rate=rate, term_months=term, tax_mode="exempt", fee_mode="none")
    defaults.update(extra)
    return Asset(name=name, **defaults)


class TestLumpSumMetrics(unittest.TestCase):
    def test_zero_hurdle(self):
        at = simple_asset("A", 0.10)
        ind = compute_asset(at, 1000.0, 0.0, hurdle_annual=0.0, inflation_annual=0.0)
        self.assertAlmostEqual(ind.net_amount, 1100.0)
        self.assertAlmostEqual(ind.net_profit, 100.0)
        self.assertAlmostEqual(ind.roi, 0.10)
        self.assertAlmostEqual(ind.annualized_roi, 0.10)
        self.assertAlmostEqual(ind.npv, 100.0)
        self.assertAlmostEqual(ind.profitability_index, 1.10)
        self.assertAlmostEqual(ind.annual_irr, 0.10)
        self.assertEqual(ind.simple_payback, 1.0)

    def test_npv_discounted_at_hurdle(self):
        at = simple_asset("A", 0.10)
        ind = compute_asset(at, 1000.0, 0.0, hurdle_annual=0.05, inflation_annual=0.0)
        self.assertAlmostEqual(ind.npv, -1000.0 + 1100.0 / 1.05, places=9)
        self.assertAlmostEqual(ind.alpha, 0.05)

    def test_tax_reduces_roi(self):
        at = simple_asset("A", 0.10, tax_mode="fixed", tax_percent=0.20)
        res = asset_summary(at, 1000.0, 0.0)
        self.assertAlmostEqual(res["gross_gain"], 100.0)
        self.assertAlmostEqual(res["tax"], 20.0)
        self.assertAlmostEqual(res["net_profit"], 80.0)
        ind = compute_asset(at, 1000.0, 0.0, hurdle_annual=0.0, inflation_annual=0.0)
        self.assertAlmostEqual(ind.roi, 0.08)

    def test_real_return(self):
        at = simple_asset("A", 0.14)
        ind = compute_asset(at, 1000.0, 0.0, hurdle_annual=0.05, inflation_annual=0.04)
        self.assertAlmostEqual(ind.real_return, 1.14 / 1.04 - 1.0)


class TestSeriesMetrics(unittest.TestCase):
    def test_series_accumulates(self):
        at = simple_asset("A", 0.1268250301319698, term=12)
        ind = compute_asset(at, 0.0, 100.0, hurdle_annual=0.0, inflation_annual=0.0)
        # monthly rate = 1% -> in-arrears series
        self.assertAlmostEqual(ind.net_amount, 100.0 * ((1.01 ** 12 - 1) / 0.01), places=6)
        self.assertAlmostEqual(ind.total_contributed, 1200.0)
        self.assertGreater(ind.net_profit, 0.0)

    def test_series_payback(self):
        at = simple_asset("A", 0.1268250301319698, term=12)
        ind = compute_asset(at, 0.0, 100.0, hurdle_annual=0.0, inflation_annual=0.0)
        self.assertIsNotNone(ind.simple_payback)
        self.assertLessEqual(ind.simple_payback, 12.0)


class TestPortfolio(unittest.TestCase):
    def test_reserve_portfolio_zero_npv(self):
        # A reserve earning exactly the hurdle rate -> NPV ~ 0.
        hurdle = 0.06
        reserve_asset = Asset(
            name="Reserve", rate=hurdle, term_months=12,
            tax_mode="exempt", fee_mode="none",
        )
        ind = compute_asset(reserve_asset, 1000.0, 0.0, hurdle_annual=hurdle, inflation_annual=0.03, is_reserve=True)
        self.assertAlmostEqual(ind.npv, 0.0, places=6)
        self.assertAlmostEqual(ind.alpha, 0.0, places=6)

    def test_portfolio_aggregates(self):
        a = compute_asset(simple_asset("A", 0.10), 800.0, 0.0, 0.05, 0.04)
        b = compute_asset(simple_asset("B", 0.06), 200.0, 0.0, 0.05, 0.04)
        c = compute_portfolio([a, b], 0.05)
        self.assertAlmostEqual(c.initial_capital, 1000.0)
        # B's wealth is now projected/reinvested to the max term (12).
        self.assertGreater(c.net_amount, 1000.0)


if __name__ == "__main__":
    unittest.main()
