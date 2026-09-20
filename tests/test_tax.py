import unittest

from src.tax import (
    tax_rate,
    tax_on_gain,
    admin_fee_amount,
    TAX_MODES,
)


class TestIncomeTax(unittest.TestCase):
    def test_only_generic_modes(self):
        self.assertEqual(TAX_MODES, ["exempt", "fixed"])

    def test_fixed_and_exempt(self):
        self.assertAlmostEqual(tax_rate("exempt", None), 0.0)
        self.assertAlmostEqual(tax_rate("exempt", 0.25), 0.0)
        self.assertAlmostEqual(tax_rate("fixed", 0.15), 0.15)
        self.assertAlmostEqual(tax_rate("fixed", None), 0.0)

    def test_typical_us_eu_rates(self):
        # US brackets: long-term 15%, short-term marginal e.g. 22%/32%.
        self.assertAlmostEqual(tax_rate("fixed", 0.15), 0.15)
        self.assertAlmostEqual(tax_rate("fixed", 0.25), 0.25)
        self.assertAlmostEqual(tax_rate("fixed", 0.30), 0.30)

    def test_tax_not_levied_on_losses(self):
        self.assertEqual(tax_on_gain(0.2, -50.0), 0.0)
        self.assertAlmostEqual(tax_on_gain(0.2, 100.0), 20.0)


class TestAdminFee(unittest.TestCase):
    def test_on_contribution(self):
        d = admin_fee_amount("contribution", 0.02, 0.0, 0.0, 1000.0, 12)
        self.assertAlmostEqual(d, 20.0)

    def test_on_assets_one_year(self):
        d = admin_fee_amount("assets", 0.10, 1000.0, 0.0, 1000.0, 12)
        self.assertAlmostEqual(d, 100.0)

    def test_on_assets_two_years(self):
        d = admin_fee_amount("assets", 0.10, 1000.0, 0.0, 1000.0, 24)
        self.assertAlmostEqual(d, 1000.0 * (1 - 0.9 ** 2))

    def test_expense_ratio_scale(self):
        # A 0.03% ETF expense ratio on $10k for 1 year ≈ $3.
        d = admin_fee_amount("assets", 0.0003, 10000.0, 0.0, 10000.0, 12)
        self.assertAlmostEqual(d, 3.0, places=6)

    def test_on_gain(self):
        d = admin_fee_amount("gain", 0.20, 0.0, 500.0, 1000.0, 12)
        self.assertAlmostEqual(d, 100.0)

    def test_no_fee(self):
        self.assertEqual(admin_fee_amount("none", 0.5, 100.0, 50.0, 10.0, 12), 0.0)


if __name__ == "__main__":
    unittest.main()
