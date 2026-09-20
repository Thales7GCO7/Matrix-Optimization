"""Tests for the matrix helpers (validated against scalar implementations)."""

import unittest
import numpy as np

from src.instruments import Asset
from src.performance import compute_asset, AssetMetrics
from src import matrix
from src import math_finance as mf
from src import instruments


def simple_asset(name, rate, term=12, **extra) -> Asset:
    defaults = dict(rate=rate, term_months=term, tax_mode="exempt", fee_mode="none")
    defaults.update(extra)
    return Asset(name=name, **defaults)


class TestNetReturnsVector(unittest.TestCase):
    def test_matches_scalar(self):
        assets = [
            simple_asset("A", 0.10),
            simple_asset("B", 0.05),
            simple_asset("C", 0.12, tax_mode="fixed", tax_percent=0.20),
        ]
        r_vec = matrix.net_returns_vector(assets)
        for i, a in enumerate(assets):
            r_scalar = instruments.annualized_net_return(a)
            self.assertAlmostEqual(r_vec[i], r_scalar, places=10)


class TestBuildCashflowMatrix(unittest.TestCase):
    def test_matrix_shape(self):
        a = compute_asset(simple_asset("A", 0.10), 1000.0, 0.0, 0.05, 0.04)
        b = compute_asset(simple_asset("B", 0.06), 500.0, 100.0, 0.05, 0.04)
        inds = [a, b]
        H = max(len(i.projection) - 1 for i in inds)
        P = matrix.build_cashflow_matrix(inds, H)
        self.assertEqual(P.shape, (2, H + 1))
        self.assertEqual(P[0, 0], 0.0)
        self.assertEqual(P[1, 0], 0.0)

    def test_axis_zero_sum_matches_loop(self):
        a = compute_asset(simple_asset("A", 0.10), 1000.0, 0.0, 0.05, 0.04)
        b = compute_asset(simple_asset("B", 0.06), 500.0, 100.0, 0.05, 0.04)
        inds = [a, b]
        H = max(len(i.projection) - 1 for i in inds)
        P = matrix.build_cashflow_matrix(inds, H)
        outflows_mat = P.sum(axis=0)

        # Loop reference
        outflows_loop = [0.0] * (H + 1)
        terms = [len(i.projection) - 1 for i in inds]
        monthly = [i.monthly_contrib for i in inds]
        for idx, term in enumerate(terms):
            for t in range(1, term + 1):
                outflows_loop[t] += monthly[idx]

        for t in range(H + 1):
            self.assertAlmostEqual(outflows_mat[t], outflows_loop[t], places=10)


class TestPortfolioNpv(unittest.TestCase):
    def test_npv_matches_loop(self):
        a = compute_asset(simple_asset("A", 0.10), 800.0, 0.0, 0.05, 0.04)
        b = compute_asset(simple_asset("B", 0.06), 200.0, 0.0, 0.05, 0.04)
        inds = [a, b]
        H = max(len(i.projection) - 1 for i in inds)
        hurdle_monthly = mf.equivalent_monthly_rate(0.05)

        P = matrix.build_cashflow_matrix(inds, H)
        outflows = P.sum(axis=0)
        # Extend projections to H
        from src.performance import _extend_projection, _monthly_rate_from_metrics
        extended = [_extend_projection(i.projection, H, _monthly_rate_from_metrics(i)) for i in inds]
        net_h = sum(pj[H]["net_amount"] for pj in extended)
        total_initial = sum(i.initial_contrib for i in inds)

        npv_mat = matrix.portfolio_npv(outflows, net_h, total_initial, 0.05, H)

        # Loop reference
        npv_loop = -total_initial
        for t in range(1, H + 1):
            npv_loop += -outflows[t] / (1.0 + hurdle_monthly) ** t
        npv_loop += net_h / (1.0 + hurdle_monthly) ** H

        self.assertAlmostEqual(npv_mat, npv_loop, places=10)


class TestVectorizedAllocate(unittest.TestCase):
    def test_simple_allocation(self):
        rates = np.array([0.10, 0.05, 0.03])
        mins = np.array([0.0, 0.0, 0.0])
        maxs = np.array([np.inf, np.inf, np.inf])
        capital = 1000.0

        alloc = matrix.vectorized_allocate(capital, rates, mins, maxs)
        # Everything should go to the first (highest rate)
        self.assertAlmostEqual(alloc[0], 1000.0)
        self.assertAlmostEqual(alloc[1], 0.0)
        self.assertAlmostEqual(alloc[2], 0.0)

    def test_honors_maximum(self):
        rates = np.array([0.10, 0.05])
        mins = np.array([0.0, 0.0])
        maxs = np.array([600.0, np.inf])
        capital = 1000.0

        alloc = matrix.vectorized_allocate(capital, rates, mins, maxs)
        self.assertAlmostEqual(alloc[0], 600.0)
        self.assertAlmostEqual(alloc[1], 400.0)

    def test_honors_minimum(self):
        rates = np.array([0.10, 0.05])
        mins = np.array([0.0, 400.0])
        maxs = np.array([np.inf, np.inf])
        capital = 1000.0

        alloc = matrix.vectorized_allocate(capital, rates, mins, maxs)
        self.assertAlmostEqual(alloc[1], 400.0)  # guaranteed minimum
        self.assertAlmostEqual(alloc[0], 600.0)  # remainder to the best

    def test_reserve_takes_remainder(self):
        rates = np.array([0.02, 0.03])  # hurdle = 0.03, asset 0 below
        mins = np.array([0.0, 0.0])
        maxs = np.array([np.inf, np.inf])
        capital = 500.0

        alloc = matrix.vectorized_allocate(capital, rates, mins, maxs)
        self.assertAlmostEqual(alloc[0], 0.0)
        self.assertAlmostEqual(alloc[1], 500.0)


class TestVectorizedAmounts(unittest.TestCase):
    def test_lump_sum_vector(self):
        principals = np.array([1000.0, 500.0, 200.0])
        rates = np.array([0.10, 0.05, 0.12])
        terms = np.array([12, 24, 6])

        res = matrix.lump_sum_vector(principals, rates, terms)
        for i in range(3):
            expected = mf.lump_sum_future_value(principals[i], rates[i], terms[i])
            self.assertAlmostEqual(res[i], expected, places=10)

    def test_series_vector(self):
        pmts = np.array([100.0, 200.0, 50.0])
        monthly = np.array([0.01, 0.005, 0.02])
        n_months = np.array([12, 24, 6])

        res = matrix.arrears_series_vector(pmts, monthly, n_months)
        for i in range(3):
            expected = mf.arrears_series_future_value(pmts[i], monthly[i], n_months[i])
            self.assertAlmostEqual(res[i], expected, places=10)

    def test_discounted_series_factor_vector(self):
        monthly = np.array([0.01, 0.005, 0.0])
        n_months = np.array([12, 24, 6])

        res = matrix.discounted_series_factor_vector(monthly, n_months)
        for i in range(3):
            expected = mf.discounted_series_factor(monthly[i], n_months[i])
            self.assertAlmostEqual(res[i], expected, places=10)


class TestFeatureMatrix(unittest.TestCase):
    def test_extract_features(self):
        assets = [
            simple_asset("A", 0.10, term=12),
            simple_asset("B", 0.05, term=24, tax_mode="fixed", tax_percent=0.20),
        ]
        X = matrix.extract_asset_features(assets)
        self.assertEqual(X.shape, (2, 8))
        self.assertAlmostEqual(X[0, 0], 0.10)  # annual_rate
        self.assertAlmostEqual(X[0, 1], 12.0)  # term_months
        self.assertAlmostEqual(X[1, 2], 0.20)  # tax_rate


if __name__ == "__main__":
    unittest.main()
