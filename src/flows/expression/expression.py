from typing import TypeVar, Generic, Any, ClassVar, cast
from abc import abstractmethod
from enum import Enum, auto

__all__ = [
    "NullExpressionNode",
    "ValueExpressionNode",
    "VariableExpressionNode",
    "UnaryExpressionNode",
    "BinaryExpressionNode",
    "FunctionExpressionNode",

    "UnboundExpression",
]

ValueProtocol = Any

V = TypeVar('V')
"""Type representing a variable or a variable reference"""
F = TypeVar('F')
"""Type representing a function or a function reference"""

class ExpressionKind(Enum):
    """Type of the expression node.

    This enum exists for convenience to overcome non-existence of enums
    with properties (tagged unions, sum algebraic data types) in Python.
    """
    NULL = auto()
    VALUE = auto()
    VARIABLE = auto()
    UNARY = auto()
    BINARY = auto()
    FUNCTION = auto()


class ExpressionNode(Generic[V, F]):
    kind: ClassVar[ExpressionKind]

    @abstractmethod
    def children(self) -> list["ExpressionNode[V, F]"]:
        pass
    
    @abstractmethod
    def all_variables(self) -> list[V]:
        pass

class NullExpressionNode(ExpressionNode, Generic[V, F]):
    kind: ClassVar[ExpressionKind] = ExpressionKind.NULL

    def children(self) -> list["ExpressionNode[V, F]"]:
        return []

    def all_variables(self) -> list[V]:
        return []

    def __eq__(self, other) -> bool:
        if not isinstance(other, self.__class__):
            return False

        return other.kind == self.kind

    def __str__(self) -> str:
        return "null"

class ValueExpressionNode(ExpressionNode, Generic[V, F]):
    kind: ClassVar[ExpressionKind] = ExpressionKind.VALUE

    value: ValueProtocol

    def children(self) -> list["ExpressionNode[V, F]"]:
        return []
    def all_variables(self) -> list[V]:
        return []

    def __init__(self, value: ValueProtocol):
        self.value = value

    def __eq__(self, other) -> bool:
        if not isinstance(other, self.__class__):
            return False

        t_other = cast(ValueExpressionNode[V, F], other)
        return other.kind == self.kind \
                and self.value == t_other.value

    def __str__(self) -> str:
        return f"{self.value}"



class UnaryExpressionNode(ExpressionNode, Generic[V, F]):
    kind: ExpressionKind = ExpressionKind.UNARY

    operator: F
    operand: ExpressionNode[V, F]

    def children(self) -> list["ExpressionNode[V, F]"]:
        return [self.operand]
    def all_variables(self) -> list[V]:
        return self.operand.all_variables()

    def __init__(self, operator: F, operand: ExpressionNode[V, F]):
        self.operator = operator
        self.operand = operand

    def __eq__(self, other) -> bool:
        if not isinstance(other, self.__class__):
            return False

        t_other = cast(UnaryExpressionNode[V, F], other)
        return other.kind == self.kind \
                and self.operator == t_other.operator \
                and self.operand == t_other.operand

    def __str__(self) -> str:
        return f"{self.operator}{self.operand}"

class BinaryExpressionNode(ExpressionNode, Generic[V, F]):
    kind: ExpressionKind = ExpressionKind.BINARY
    operator: F

    left: ExpressionNode
    right: ExpressionNode

    def children(self) -> list["ExpressionNode[V, F]"]:
        return [self.left, self.right]
    def all_variables(self) -> list[V]:
        return self.left.all_variables() + self.right.all_variables()

    def __init__(self, operator: F,
                 left: ExpressionNode[V, F],
                 right: ExpressionNode[V, F]):
        self.operator = operator
        self.left = left
        self.right = right

    def __eq__(self, other) -> bool:
        if not isinstance(other, self.__class__):
            return False

        t_other = cast(BinaryExpressionNode[V, F], other)
        return other.kind == self.kind \
                and self.operator == t_other.operator \
                and self.left == t_other.left \
                and self.right == t_other.right

    def __str__(self) -> str:
        return f"{self.left} {self.operator} {self.right}"


class FunctionExpressionNode(ExpressionNode, Generic[V, F]):
    kind: ExpressionKind = ExpressionKind.FUNCTION

    function: F
    args: list[ExpressionNode]

    def children(self) -> list["ExpressionNode[V, F]"]:
        return self.args

    def all_variables(self) -> list[V]:
        vars: list[V] = []
        for arg in self.args:
            vars += arg.all_variables()
        return vars

    def __init__(self, function: F, args: list[ExpressionNode[V, F]]):
        self.function = function
        self.args = args

    
    def __eq__(self, other) -> bool:
        if not isinstance(other, self.__class__):
            return False

        t_other = cast(FunctionExpressionNode[V, F], other)
        return other.kind == self.kind \
                and self.function == t_other.function \
                and self.args == t_other.args 

    def __str__(self) -> str:
        args = ", ".join(str(arg) for arg in self.args)
        return f"{self.function}({args})"



class VariableExpressionNode(ExpressionNode, Generic[V, F]):
    kind: ExpressionKind = ExpressionKind.VARIABLE

    variable: V

    def children(self) -> list["ExpressionNode[V, F]"]:
        return []
    def all_variables(self) -> list[V]:
        return [self.variable]

    def __init__(self, variable: V):
        self.variable = variable

    def __eq__(self, other) -> bool:
        if not isinstance(other, self.__class__):
            return False

        t_other = cast(VariableExpressionNode[V, F], other)
        return other.kind == self.kind \
                and self.variable == t_other.variable

    def __str__(self) -> str:
        return f"{self.variable}"


UnboundExpression = ExpressionNode[str, str]
"""Expression where the variable and function references are strings.

This form of expression is returned by the parser and it is let up to the user
to either perform lookups on each node or to transform it into a bound
expression.
"""

