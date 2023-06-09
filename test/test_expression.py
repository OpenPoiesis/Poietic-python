import unittest

# from poietic.flows.expression import UnboundExpression
from poietic.expression.parser import ExpressionParser

class TestExpression(unittest.TestCase):
    def test_variables(self):
        expr = ExpressionParser("min(a + b, c)").parse()

        vars = expr.all_variables()

        self.assertTrue("a" in vars)
        self.assertTrue("b" in vars)
        self.assertTrue("c" in vars)
        self.assertFalse("min" in vars)
        self.assertEqual(len(vars), 3)

    def test_variablesAreUnique(self):
        expr = ExpressionParser("sqrt(a*a + b*b) + min(a, a, b, b)").parse()

        vars = expr.all_variables()

        self.assertTrue("a" in vars)
        self.assertTrue("b" in vars)
        self.assertEqual(len(vars), 2)

        

