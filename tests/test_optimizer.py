import unittest

import numpy as np

from src.nonlinear_optimizer import (
    NonlinearOptimizer,
    optimize_unconstrained,
    numerical_hessian,
    numerical_gradient,
)
from src.investment_optimizer import (
    InvestmentOptimizer,
    make_logreturn,
    default_portfolio,
)
from src.expression_parser import parse_expression


class TestNumericalDerivatives(unittest.TestCase):
    def _f(self, x):
        return x[0] ** 2 + 3.0 * x[0] * x[1] + 2.0 * x[1] ** 2

    def test_numerical_hessian(self):
        H = numerical_hessian(self._f, np.array([1.0, 1.0]))
        np.testing.assert_allclose(H, [[2.0, 3.0], [3.0, 4.0]], atol=1e-6)

    def test_numerical_gradient(self):
        g = numerical_gradient(self._f, np.array([1.0, 1.0]))
        np.testing.assert_allclose(g, [5.0, 7.0], atol=1e-8)

    def test_numerical_hessian_single_variable(self):
        H = numerical_hessian(lambda x: x[0] ** 3, np.array([2.0]))
        np.testing.assert_allclose(H, [[12.0]], atol=1e-5)


class TestUnconstrainedOptimization(unittest.TestCase):
    def test_maximize_quadratic(self):
        f = parse_expression("-x1**2 - x2**2 + 4*x1 + 6*x2", 2)
        solver = NonlinearOptimizer(objective=f, x0=[0.0, 0.0], maximize=True)
        status, solution = solver.solve()
        self.assertEqual(status, "otimo")
        np.testing.assert_allclose(solution, [2.0, 3.0], atol=1e-6)
        self.assertAlmostEqual(solver.optimal_value, 13.0, places=6)

    def test_minimize_rosenbrock(self):
        def rosen(x):
            return (
                100.0 * (x[1] - x[0] ** 2) ** 2
                + (1.0 - x[0]) ** 2
            )

        status, solution = optimize_unconstrained(
            objective=rosen, x0=[-1.2, 1.0], maximize=False
        )
        self.assertEqual(status, "otimo")
        np.testing.assert_allclose(solution, [1.0, 1.0], atol=1e-4)

    def test_analytic_gradient(self):
        def f(x):
            return -((x[0] - 3) ** 2) - (x[1] - 5) ** 2

        def grad(x):
            return [-2.0 * (x[0] - 3), -2.0 * (x[1] - 5)]

        status, solution = optimize_unconstrained(
            objective=f, x0=[0.0, 0.0], gradient=grad, maximize=True
        )
        self.assertEqual(status, "otimo")
        np.testing.assert_allclose(solution, [3.0, 5.0], atol=1e-6)


class TestConstrainedOptimization(unittest.TestCase):
    def test_equality_constraint(self):
        f = parse_expression("x1*x2", 2)
        constraints = [
            {"type": "eq", "fun": lambda x: [x[0] + 2 * x[1] - 10]}
        ]
        solver = NonlinearOptimizer(
            objective=f,
            x0=[1.0, 1.0],
            bounds=[(0, None), (0, None)],
            constraints=constraints,
            maximize=True,
        )
        status, solution = solver.solve()
        self.assertEqual(status, "otimo")
        np.testing.assert_allclose(solution, [5.0, 2.5], atol=1e-6)
        self.assertAlmostEqual(solver.optimal_value, 12.5, places=6)

    def test_inequality_constraint(self):
        f = parse_expression("x1*x2", 2)
        constraints = [
            {"type": "ineq", "fun": lambda x: [8 - x[0] ** 2 - x[1] ** 2]}
        ]
        solver = NonlinearOptimizer(
            objective=f,
            x0=[0.5, 0.5],
            bounds=[(0, None), (0, None)],
            constraints=constraints,
            maximize=True,
        )
        status, solution = solver.solve()
        self.assertEqual(status, "otimo")
        np.testing.assert_allclose(solution, [2.0, 2.0], atol=1e-6)


class TestInvestmentOptimizer(unittest.TestCase):
    def test_symmetric_log_returns(self):
        funcs = [make_logreturn(10.0, 1.0), make_logreturn(10.0, 1.0)]
        opt = InvestmentOptimizer(funcs, budget=20.0)
        status, solution = opt.solve()
        self.assertEqual(status, "otimo")
        np.testing.assert_allclose(solution, [10.0, 10.0], atol=1e-6)
        self.assertAlmostEqual(opt.optimal_return, 20.0 * np.log(11.0), places=8)

    def test_budget_fully_allocated(self):
        opt = InvestmentOptimizer(default_portfolio(), budget=1000.0)
        status, solution = opt.solve()
        self.assertEqual(status, "otimo")
        self.assertAlmostEqual(np.sum(solution), 1000.0, places=6)
        self.assertTrue(np.all(solution >= 0.0))

    def test_returns_with_upper_bounds(self):
        funcs = [make_logreturn(10.0, 1.0), make_logreturn(10.0, 1.0)]
        opt = InvestmentOptimizer(funcs, budget=20.0, upper_bounds=[5.0, 20.0])
        status, solution = opt.solve()
        self.assertEqual(status, "otimo")
        np.testing.assert_allclose(solution, [5.0, 15.0], atol=1e-6)

    def test_display(self):
        opt = InvestmentOptimizer([make_logreturn(10.0, 1.0)], budget=10.0)
        opt.solve()
        display = opt.get_display()
        self.assertIn("Alocacao otima", display)
        self.assertIn("Retorno total otimo", display)


if __name__ == "__main__":
    unittest.main()