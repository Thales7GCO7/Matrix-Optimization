import unittest
from fractions import Fraction
from src.gaussian_elimination import GaussJordan


F = Fraction


class TestGaussJordan(unittest.TestCase):
    def test_2x2_system(self):
        matrix = [
            [F(2), F(3), F(8)],
            [F(1), F(2), F(5)],
        ]
        gj = GaussJordan(matrix)
        status, solution = gj.solve()
        self.assertEqual(status, "unica")
        self.assertEqual(solution[0], F(1))
        self.assertEqual(solution[1], F(2))

    def test_3x3_system(self):
        matrix = [
            [F(2), F(1), F(-1), F(8)],
            [F(-3), F(-1), F(2), F(-11)],
            [F(-2), F(1), F(2), F(-3)],
        ]
        gj = GaussJordan(matrix)
        status, solution = gj.solve()
        self.assertEqual(status, "unica")
        self.assertEqual(solution[0], F(2))
        self.assertEqual(solution[1], F(3))
        self.assertEqual(solution[2], F(-1))

    def test_inconsistent_system(self):
        matrix = [
            [F(1), F(1), F(1)],
            [F(0), F(0), F(5)],
        ]
        gj = GaussJordan(matrix)
        status, solution = gj.solve()
        self.assertEqual(status, "inconsistente")
        self.assertIsNone(solution)

    def test_underdetermined_system(self):
        matrix = [
            [F(1), F(2), F(0), F(3)],
            [F(0), F(0), F(1), F(1)],
        ]
        gj = GaussJordan(matrix)
        status, solution = gj.solve()
        self.assertEqual(status, "infinitas_solucoes")
        self.assertIsNone(solution)

    def test_identity_system(self):
        matrix = [
            [F(1), F(0), F(0), F(5)],
            [F(0), F(1), F(0), F(3)],
            [F(0), F(0), F(1), F(7)],
        ]
        gj = GaussJordan(matrix)
        status, solution = gj.solve()
        self.assertEqual(status, "unica")
        self.assertEqual(solution, [F(5), F(3), F(7)])

    def test_fractional_solution(self):
        matrix = [
            [F(2), F(1), F(3)],
            [F(1), F(-1), F(1)],
        ]
        gj = GaussJordan(matrix)
        status, solution = gj.solve()
        self.assertEqual(status, "unica")
        self.assertEqual(solution[0], F(4) / F(3))
        self.assertEqual(solution[1], F(1) / F(3))

    def test_pivot_structure(self):
        matrix = [
            [F(2), F(1), F(-1), F(8)],
            [F(-3), F(-1), F(2), F(-11)],
            [F(-2), F(1), F(2), F(-3)],
        ]
        gj = GaussJordan(matrix)
        gj.solve()
        for i in range(3):
            for j in range(3):
                expected = F(1) if i == j else F(0)
                self.assertEqual(
                    gj.matrix[i][j], expected,
                    f"Posicao ({i},{j}) esperado {expected}, obteve {gj.matrix[i][j]}"
                )


if __name__ == "__main__":
    unittest.main()
