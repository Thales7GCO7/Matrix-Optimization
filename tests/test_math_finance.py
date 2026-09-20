import unittest

from src.math_finance import (
    discounted_series_factor,
    arrears_series_factor,
    lump_sum_future_value,
    arrears_series_future_value,
    effective_annual_rate,
    equivalent_annual_rate,
    equivalent_monthly_rate,
    cashflow_irr,
    hurdle_from_indicators,
)


class TestRateConversion(unittest.TestCase):
    def test_effective_monthly_to_annual(self):
        self.assertAlmostEqual(effective_annual_rate(0.01, "monthly", "effective"), 0.1268250301319698)

    def test_effective_semiannual_to_annual(self):
        self.assertAlmostEqual(effective_annual_rate(0.06, "semiannual", "effective"), 0.1236)

    def test_nominal_annual_with_monthly_compounding(self):
        r = effective_annual_rate(0.13, "monthly", "nominal")
        self.assertAlmostEqual(r, (1 + 0.13 / 12) ** 12 - 1)

    def test_mutual_equivalence(self):
        monthly_rate = equivalent_monthly_rate(0.12)
        self.assertAlmostEqual(equivalent_annual_rate(monthly_rate, 12), 0.12, places=12)


class TestFutureValues(unittest.TestCase):
    def test_lump_sum(self):
        self.assertAlmostEqual(lump_sum_future_value(1000.0, 0.10, 12), 1100.0)

    def test_lump_sum_two_years(self):
        self.assertAlmostEqual(lump_sum_future_value(1000.0, 0.10, 24), 1210.0)

    def test_series_zero_rate(self):
        self.assertEqual(arrears_series_future_value(100.0, 0.0, 12), 1200.0)

    def test_monthly_series_1pct(self):
        fv = arrears_series_future_value(100.0, 0.01, 12)
        expected = 100.0 * ((1.01 ** 12 - 1) / 0.01)
        self.assertAlmostEqual(fv, expected)

    def test_discounted_series_factor(self):
        self.assertAlmostEqual(discounted_series_factor(0.01, 12), sum((1.01) ** -t for t in range(1, 13)))

    def test_series_accumulates_principal_in_installments(self):
        f = arrears_series_factor(0.01, 12)
        self.assertGreater(f, 12.0)  # interest accrues on the 12 installments


class TestIrr(unittest.TestCase):
    def test_simple_flow(self):
        r = cashflow_irr([-1000.0, 1100.0])
        self.assertIsNotNone(r)
        self.assertAlmostEqual(r, 0.10, places=9)

    def test_flow_without_positive_root(self):
        # No positive root (loss-making flow): returns the negative root.
        r = cashflow_irr([-100.0, -50.0, 10.0])
        self.assertIsNotNone(r)
        self.assertLess(r, 0.0)

    def test_series_flow(self):
        flow = [-500.0] * 12
        flow[0] = -1000.0
        flow.append(8000.0 - 500.0)  # month 12: deposit + redemption
        r = cashflow_irr(flow)
        self.assertIsNotNone(r)
        self.assertGreater(r, 0.0)


class TestHurdle(unittest.TestCase):
    def test_real_rate(self):
        hurdle = hurdle_from_indicators(0.04, 0.025)
        self.assertAlmostEqual(hurdle, (1.04 / 1.025) - 1)

    def test_risk_free_equal_inflation_gives_zero(self):
        self.assertAlmostEqual(hurdle_from_indicators(0.05, 0.05), 0.0)


if __name__ == "__main__":
    unittest.main()
