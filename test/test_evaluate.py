import unittest

from poietic.expression.parser import ExpressionParser
from poietic.flows.evaluate import bind_expression, evaluate_expression

class EvaluationTestCase(unittest.TestCase):
    def test_evaluateLiteral(self):
        uexpr = ExpressionParser("123").parse()
        expr = bind_expression(uexpr,
                               variables={},
                               functions={})

        value = evaluate_expression(expr, variables={}, functions={})

        self.assertEqual(value, 123.0)

    def test_evaluateVar(self):
        uexpr = ExpressionParser("x + y").parse()
        expr = bind_expression(uexpr,
                               variables={"x":1, "y":2},
                               functions={"+":"+"})

        value = evaluate_expression(expr,
                                    variables={1: 10.0, 2:100.0},
                                    functions={})

        self.assertEqual(value, 110.0)

