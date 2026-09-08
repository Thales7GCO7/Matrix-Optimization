import unittest
from fractions import Fraction

import numpy as np

from src.nonlinear_solver import NewtonRaphson
from web import explicacoes
from web.graficos import _polygon_feasivel, grafico_convergencia, grafico_simplex
from web.parsers import (
    parse_bounds,
    parse_float_sequence,
    parse_flex_fraction,
    parse_grid,
    parse_vector,
)


class TestParsers(unittest.TestCase):
    def test_inteiro(self):
        self.assertEqual(parse_flex_fraction("2"), Fraction(2))

    def test_fracao(self):
        self.assertEqual(parse_flex_fraction("1/3"), Fraction(1, 3))

    def test_fracao_negativa(self):
        self.assertEqual(parse_flex_fraction("-5/7"), Fraction(-5, 7))

    def test_decimal(self):
        self.assertEqual(parse_flex_fraction("1.5"), Fraction(3, 2))

    def test_invalido(self):
        self.assertIsNone(parse_flex_fraction("abc"))
        self.assertIsNone(parse_flex_fraction("1/0"))
        self.assertIsNone(parse_flex_fraction(""))
        self.assertIsNone(parse_flex_fraction("1/2/3"))

    def test_grid_ok(self):
        grid, err = parse_grid([["1", "2", "3"], ["4", "5", "6"]], 2, 3)
        self.assertEqual(err, "")
        self.assertEqual(grid[0][2], Fraction(3))

    def test_grid_dimensao_errada(self):
        _, err = parse_grid([["1"]], 2, 1)
        self.assertTrue(err)

    def test_grid_valor_invalido(self):
        _, err = parse_grid([["1", "abc"]], 1, 2)
        self.assertIn("Valor invalido", err)

    def test_vector_ok(self):
        vec, err = parse_vector(["1", "1/2"], 2)
        self.assertEqual(err, "")
        self.assertEqual(vec, [Fraction(1), Fraction(1, 2)])

    def test_vector_tamanho_errado(self):
        _, err = parse_vector(["1", "2"], 3)
        self.assertIn("Esperado", err)

    def test_float_sequence_ok(self):
        vec, err = parse_float_sequence("1.5 2 -0.25", 3)
        self.assertEqual(err, "")
        self.assertEqual(vec, [1.5, 2.0, -0.25])

    def test_float_sequence_erro(self):
        _, err = parse_float_sequence("1 x", 2)
        self.assertTrue(err)

    def test_bounds_vazios(self):
        bounds, err = parse_bounds(["", "0"], ["", "10"], 2)
        self.assertEqual(err, "")
        self.assertEqual(bounds, [(None, None), (0.0, 10.0)])

    def test_bounds_inf(self):
        bounds, err = parse_bounds(["inf", "-inf"], ["5", "inf"], 2)
        self.assertEqual(err, "")
        self.assertEqual(bounds, [(None, 5.0), (None, None)])

    def test_bounds_invalido(self):
        _, err = parse_bounds(["abc"], ["10"], 1)
        self.assertTrue(err)


class TestExplicacoes(unittest.TestCase):
    def test_telas_presentes(self):
        for tela in ["inicio", "gauss", "simplex", "newton", "otimizacao", "investimento"]:
            self.assertIn(tela, explicacoes.EXPLICACOES)
            cont = explicacoes.obter(tela)
            self.assertTrue(cont["titulo"])
            self.assertTrue(cont["resumo"])

    def test_formulas_e_variaveis(self):
        for tela in ["gauss", "simplex", "newton", "otimizacao", "investimento"]:
            cont = explicacoes.obter(tela)
            self.assertTrue(cont.get("formula"), tela)
            self.assertTrue(cont.get("variaveis"), tela)


class TestGraficos(unittest.TestCase):
    def test_polygon_feasivel(self):
        A = [[1, 0], [0, 2], [3, 2]]
        b = [4, 6, 18]
        hull = _polygon_feasivel(A, b)
        self.assertIsNotNone(hull)
        self.assertTrue(any(np.allclose(v, [4, 3], atol=1e-6) for v in hull))

    def test_polygon_feasivel_dimensao(self):
        self.assertIsNone(_polygon_feasivel([[1, 2, 3], [4, 5, 6]], [1, 1]))

    def test_grafico_simplex_2var(self):
        fig = grafico_simplex([[1, 0], [0, 2], [3, 2]], [4, 6, 18], [3, 5], [4, 3], 27)
        self.assertIsNotNone(fig)

    def test_grafico_simplex_3var(self):
        fig = grafico_simplex([[1, 1, 1], [2, 3, 2]], [10, 15], [2, 3, 1], None, None)
        self.assertIsNone(fig)

    def test_grafico_convergencia(self):
        fig = grafico_convergencia([1e0, 1e-2, 1e-4, 1e-8])
        self.assertIsNotNone(fig)


class TestSolversFrontend(unittest.TestCase):
    def test_newton_norms_para_grafico(self):
        solver = NewtonRaphson(func=lambda x: [x[0] ** 2 - 2], x0=[1.0])
        status, _ = solver.solve()
        self.assertEqual(status, "convergiu")
        self.assertGreater(len(solver.norms), 0)


if __name__ == "__main__":
    unittest.main()