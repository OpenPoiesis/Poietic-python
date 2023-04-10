# evaluate.py
#
# Expression evaluation
#
# Created by: Stefan Urbanek
# Date: 2023-04-09

from typing import cast
from ..db import ObjectID

from .expression import *

__all__ = [
        "VariableReference",
        "FunctionReference",
        "BoundExpression",
        "bind_expression",
        "evaluate_expression",
]

VariableReference = ObjectID
FunctionReference = str

BoundExpression = ExpressionNode[VariableReference, FunctionReference]

def bind_expression(expr: UnboundExpression,
                    variables: dict[str, VariableReference],
                    functions: dict[str, FunctionReference]) -> BoundExpression:
    """
    Binds the unbound expression to concrete variable and function references.

    :param variables: Mapping of variable names to variable references.
    :param functions: Mapping of function names to function references.

    :return: Expression bound to the references.
    :raises: Exception when variable or function is not found.
    """
    # TODO: Use custom exceptions and distinguish between missing variable and missing function.
    # NOTE: This would be better with enum, but this is all we have in Python

    if isinstance(expr, NullExpressionNode):
        return cast(BoundExpression, expr)

    elif isinstance(expr, ValueExpressionNode):
        return cast(BoundExpression, expr)

    elif isinstance(expr, UnaryExpressionNode):
        new = UnaryExpressionNode(operator=functions[expr.operator],
                                  operand=bind_expression(expr.operand,
                                                       variables,
                                                       functions))
        return new

    elif isinstance(expr, BinaryExpressionNode):
        new = BinaryExpressionNode(operator=functions[expr.operator],
                                  left=bind_expression(expr.left,
                                                       variables,
                                                       functions),
                                  right=bind_expression(expr.right,
                                                       variables,
                                                       functions))
        return new

    elif isinstance(expr, FunctionExpressionNode):
        args: list[BoundExpression] = list()

        for arg in expr.args:
            args.append(bind_expression(arg, variables, functions))

        new = FunctionExpressionNode(function=functions[expr.function],
                                     args=args)
        return new

    elif isinstance(expr, VariableExpressionNode):
        new = VariableExpressionNode(variables[expr.variable])
        return new
    else:
        raise RuntimeError(f"Unknown expression node type: {expr}")



def evaluate_expression(expr: BoundExpression,
                    variables: dict[ObjectID, float],
                    functions: dict[str, FunctionReference]) -> float:
    """
    Binds the unbound expression to concrete variable and function references.

    :param variables: Mapping of variable names to variable references.
    :param functions: Mapping of function names to function references.

    :return: Expression bound to the references.
    :raises: Exception when variable or function is not found.
    """
    # TODO: Use custom exceptions and distinguish between missing variable and missing function.
    # NOTE: This would be better with enum, but this is all we have in Python

    if isinstance(expr, NullExpressionNode):
        raise RuntimeError

    elif isinstance(expr, ValueExpressionNode):
        # TODO: value_to_float()
        return float(expr.value)

    elif isinstance(expr, UnaryExpressionNode):
        operand = evaluate_expression(expr.operand, variables, functions)
        match expr.operator:
            case "-": return -operand
            case _: raise RuntimeError

    elif isinstance(expr, BinaryExpressionNode):
        lhs = evaluate_expression(expr.left, variables, functions)
        rhs = evaluate_expression(expr.right, variables, functions)
        match expr.operator:
            case "+": return lhs + rhs
            case "-": return lhs - rhs
            case "*": return lhs * rhs
            case "/": return lhs / rhs
            case "%": return lhs % rhs
            case _: raise RuntimeError

    elif isinstance(expr, FunctionExpressionNode):
        args: list[float] = list()

        for arg in expr.args:
            evaluated = evaluate_expression(arg, variables, functions)
            args.append(evaluated)

        raise NotImplementedError

    elif isinstance(expr, VariableExpressionNode):
        return variables[expr.variable]

    else:
        raise RuntimeError


