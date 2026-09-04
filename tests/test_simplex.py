import unittest
from fractions import Fraction
from src.simplex import SimplexSolver


F = Fraction


class TestSimplex(unittest.TestCase):
    def test_basic_problem(self):
        c = [F(5), F(4)]
        A = [
            [F(6), F(4)],
            [F(1), F(2)],
        ]
        b = [F(24), F(6)]
        solver = SimplexSolver(c, A, b)
        status, value, solution = solver.solve()
        self.assertEqual(status, "otimo")
        self.assertEqual(value, F(21))
        self.assertEqual(solution[0], F(3))
        self.assertEqual(solution[1], F(3) / F(2))

    def test_three_variables(self):
        c = [F(3), F(2), F(5)]
        A = [
            [F(1), F(2), F(1)],
            [F(3), F(0), F(2)],
            [F(1), F(4), F(0)],
        ]
        b = [F(4), F(6), F(8)]
        solver = SimplexSolver(c, A, b)
        status, value, solution = solver.solve()
        self.assertEqual(status, "otimo")
        self.assertIsNotNone(value)

    def test_two_variable_optimization(self):
        c = [F(2), F(3)]
        A = [
            [F(1), F(0)],
            [F(0), F(1)],
            [F(1), F(1)],
        ]
        b = [F(4), F(5), F(6)]
        solver = SimplexSolver(c, A, b)
        status, value, solution = solver.solve()
        self.assertEqual(status, "otimo")
        self.assertEqual(value, F(17))
        self.assertEqual(solution[0], F(1))
        self.assertEqual(solution[1], F(5))

    def test_unbounded(self):
        c = [F(1), F(1)]
        A = [
            [F(-1), F(1)],
        ]
        b = [F(1)]
        solver = SimplexSolver(c, A, b)
        status, value, solution = solver.solve()
        self.assertEqual(status, "ilimitado")

    def test_single_variable(self):
        c = [F(5)]
        A = [[F(1)]]
        b = [F(10)]
        solver = SimplexSolver(c, A, b)
        status, value, solution = solver.solve()
        self.assertEqual(status, "otimo")
        self.assertEqual(value, F(50))
        self.assertEqual(solution[0], F(10))


if __name__ == "__main__":
    unittest.main()
