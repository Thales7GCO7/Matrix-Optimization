import unittest

from src.instruments import Asset
from src.portfolio_optimizer import PortfolioOptimizer


def make_asset(name, rate, term=12, **extra) -> Asset:
    defaults = dict(rate=rate, term_months=term, tax_mode="exempt", fee_mode="none")
    defaults.update(extra)
    return Asset(name=name, **defaults)


class TestInitialAllocation(unittest.TestCase):
    def test_all_to_best_asset(self):
        a = make_asset("A", 0.10)
        b = make_asset("B", 0.05)
        res = PortfolioOptimizer([a, b], initial_capital=1000.0, hurdle_annual=0.03, inflation_annual=0.0).solve()
        by_name = {i.name: i for i in res.metrics}
        self.assertAlmostEqual(by_name["A"].initial_contrib, 1000.0)
        self.assertAlmostEqual(by_name["B"].initial_contrib, 0.0)
        self.assertAlmostEqual(by_name["Reserve (hurdle)"].initial_contrib, 0.0)

    def test_honors_cap_and_reserve_takes_remainder(self):
        a = make_asset("A", 0.10, initial_max=600.0)
        b = make_asset("B", 0.05, initial_max=100.0)
        res = PortfolioOptimizer([a, b], initial_capital=1000.0, hurdle_annual=0.03, inflation_annual=0.0).solve()
        by_name = {i.name: i for i in res.metrics}
        self.assertAlmostEqual(by_name["A"].initial_contrib, 600.0)
        self.assertAlmostEqual(by_name["B"].initial_contrib, 100.0)
        self.assertAlmostEqual(by_name["Reserve (hurdle)"].initial_contrib, 300.0)

    def test_reserve_beats_asset_below_hurdle(self):
        weak = make_asset("Weak", 0.02)  # net rate below the 3% hurdle
        res = PortfolioOptimizer([weak], initial_capital=500.0, hurdle_annual=0.03, inflation_annual=0.0).solve()
        by_name = {i.name: i for i in res.metrics}
        self.assertAlmostEqual(by_name["Weak"].initial_contrib, 0.0)
        self.assertAlmostEqual(by_name["Reserve (hurdle)"].initial_contrib, 500.0)

    def test_minimum_and_mandatory_diversification(self):
        a = make_asset("A", 0.10)
        b = make_asset("B", 0.05, initial_min=400.0)
        res = PortfolioOptimizer([a, b], initial_capital=1000.0, hurdle_annual=0.03, inflation_annual=0.0).solve()
        by_name = {i.name: i for i in res.metrics}
        self.assertAlmostEqual(by_name["B"].initial_contrib, 400.0)  # guaranteed minimum
        self.assertAlmostEqual(by_name["A"].initial_contrib, 600.0)  # remainder to the best

    def test_minimum_above_budget_gives_error(self):
        a = make_asset("A", 0.10)
        b = make_asset("B", 0.05, initial_min=1200.0)
        res = PortfolioOptimizer([a, b], initial_capital=1000.0, hurdle_annual=0.03, inflation_annual=0.0).solve()
        self.assertTrue(res.error)


class TestMonthlyAllocation(unittest.TestCase):
    def test_distributes_monthly_contrib(self):
        a = make_asset("A", 0.10, uses_monthly=True, monthly_max=200.0)
        b = make_asset("B", 0.05, uses_monthly=True, monthly_max=150.0)
        res = PortfolioOptimizer(
            [a, b], initial_capital=0.0, hurdle_annual=0.03, inflation_annual=0.0,
            monthly_contrib=300.0, use_monthly=True,
        ).solve()
        by_name = {i.name: i for i in res.metrics}
        self.assertAlmostEqual(by_name["A"].monthly_contrib, 200.0)
        self.assertAlmostEqual(by_name["B"].monthly_contrib, 100.0)
        self.assertAlmostEqual(by_name["Reserve (hurdle)"].monthly_contrib, 0.0)

    def test_asset_without_monthly_is_skipped(self):
        a = make_asset("A", 0.10, uses_monthly=False, monthly_max=200.0)
        res = PortfolioOptimizer(
            [a], initial_capital=1000.0, hurdle_annual=0.03, inflation_annual=0.0,
            monthly_contrib=300.0, use_monthly=True,
        ).solve()
        by_name = {i.name: i for i in res.metrics}
        self.assertAlmostEqual(by_name["A"].initial_contrib, 1000.0)
        self.assertAlmostEqual(by_name["A"].monthly_contrib, 0.0)
        self.assertAlmostEqual(by_name["Reserve (hurdle)"].monthly_contrib, 300.0)


class TestWithTax(unittest.TestCase):
    def test_higher_tax_lowers_priority(self):
        a = make_asset("A", 0.15, tax_mode="fixed", tax_percent=0.5)  # reduced net rate
        b = make_asset("B", 0.09)  # exempt
        res = PortfolioOptimizer([a, b], initial_capital=1000.0, hurdle_annual=0.03, inflation_annual=0.0).solve()
        by_name = {i.name: i for i in res.metrics}
        # 15% gross with 50% tax -> ~8.1% net; exempt B at 9% -> B takes all.
        self.assertAlmostEqual(by_name["A"].initial_contrib, 0.0)
        self.assertAlmostEqual(by_name["B"].initial_contrib, 1000.0)


class TestCompositePortfolio(unittest.TestCase):
    def test_portfolio_metrics_are_consistent(self):
        a = make_asset("A", 0.10, initial_max=500.0, uses_monthly=True, monthly_max=100.0)
        res = PortfolioOptimizer(
            [a], initial_capital=800.0, hurdle_annual=0.05, inflation_annual=0.04,
            monthly_contrib=100.0, use_monthly=True,
        ).solve()
        self.assertEqual(res.error, "")
        c = res.portfolio
        # initial capital = 500 (asset A) + 300 (reserve) = 800
        self.assertAlmostEqual(c.initial_capital, 800.0)
        self.assertAlmostEqual(c.reserve, 300.0)
        self.assertGreater(c.net_amount, 0.0)
        self.assertIsNotNone(c.annual_irr)


if __name__ == "__main__":
    unittest.main()
