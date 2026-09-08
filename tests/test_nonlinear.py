import unittest

import numpy as np

from src.nonlinear_solver import NewtonRaphson, solve_scalar
from src.expression_parser import parse_multiple_expressions


class TestNewtonRaphsonScalar(unittest.TestCase):
    def test_sqrt_of_two(self):
        status, root = solve_scalar(lambda x: x ** 2 - 2, x0=1.0)
        self.assertEqual(status, "convergiu")
        self.assertAlmostEqual(root, np.sqrt(2), places=10)

    def test_cubic(self):
        status, root = solve_scalar(lambda x: x ** 3 - x - 2, x0=1.5)
        self.assertEqual(status, "convergiu")
        self.assertAlmostEqual(root, 1.521379706804568, places=10)

    def test_analytic_derivative(self):
        status, root = solve_scalar(
            lambda x: np.exp(x) - 2,
            x0=0.5,
            deriv=lambda x: np.exp(x),
        )
        self.assertEqual(status, "convergiu")
        self.assertAlmostEqual(root, np.log(2), places=10)


class TestNewtonRaphsonSystem(unittest.TestCase):
    def _system(self, funcs):
        def sistema(x):
            return [f(x) for f in funcs]

        return sistema

    def test_circle_line_intersection(self):
        funcs = parse_multiple_expressions(
            ["x1 + x2 - 3", "x1**2 + x2**2 - 5"], 2
        )
        solver = NewtonRaphson(func=self._system(funcs), x0=[0.5, 3.0])
        status, solution = solver.solve()
        self.assertEqual(status, "convergiu")
        np.testing.assert_allclose(solution, [1.0, 2.0], atol=1e-9)

    def test_quadratic_system(self):
        funcs = parse_multiple_expressions(
            ["x1**2 - 2*x1 + x2 - 4", "x1**2 + x2**2 - 26"], 2
        )
        solver = NewtonRaphson(func=self._system(funcs), x0=[0.0, 4.0])
        status, solution = solver.solve()
        self.assertEqual(status, "convergiu")
        np.testing.assert_allclose(solution, [1.0, 5.0], atol=1e-8)

    def test_analytic_jacobian(self):
        def sistema(x):
            return [x[0] ** 2 - 2, x[1] ** 3 - x[1] - 2]

        def jac(x):
            return [
                [2 * x[0], 0.0],
                [0.0, 3 * x[1] ** 2 - 1],
            ]

        solver = NewtonRaphson(func=sistema, x0=[1.0, 1.5], jac=jac)
        status, solution = solver.solve()
        self.assertEqual(status, "convergiu")
        np.testing.assert_allclose(
            solution, [np.sqrt(2), 1.521379706804568], atol=1e-9
        )

    def test_steps_recorded(self):
        solver = NewtonRaphson(
            func=lambda x: [x[0] ** 2 - 2], x0=[1.0]
        )
        solver.solve()
        self.assertGreater(len(solver.steps), 0)

    def test_norms_recorded(self):
        solver = NewtonRaphson(
            func=lambda x: [x[0] ** 2 - 2], x0=[1.0]
        )
        solver.solve()
        self.assertGreater(len(solver.norms), 0)
        self.assertTrue(all(n >= 0.0 for n in solver.norms))


if __name__ == "__main__":
    unittest.main()