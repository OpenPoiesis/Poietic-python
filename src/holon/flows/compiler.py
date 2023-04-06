# compiler.py
#
# Created by: Stefan Urbanek
# Date: 2023-04-01

from typing import cast
from ..db import ObjectID
from ..graph import Graph, Node, Edge
from collections import defaultdict

from .model import StockComponent, FlowComponent, ExpressionComponent
from .model import Metamodel
from .expression import *
from .expression.parser import ExpressionParser

from .issues import CompilerError, NodeIssueType, NodeIssue
from .functions import BuiltinFunctions


__all__ = [
    "Compiler",
    "bind_expression",
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


class CompiledModel:
    # expressions: dict[ObjectID, BoundExpression]
    sorted_expression_nodes: list[Node]
    # stock_components: dict[ObjectID, StockComponent]
    # flow_components: dict[ObjectID, FlowComponent]

    # stock -> [flow]
    # outflows: dict[Node, list[Node]]
    # stock -> [flow]
    # inflows: dict[Node, list[Node]]


    def __init__(self):
        # self.expressions = dict()
        self.sorted_expression_nodes = list()
        # self.stock_components = dict()
        # self.flow_components = dict()
        # self.outflows = dict()
        # self.inflows = dict()

class Compiler:
    graph: Graph

    def __init__(self, graph: Graph):
        self.graph = graph

    def compile(self) -> CompiledModel:
        compiled = CompiledModel()


        # node_issues: dict[ObjectID, list[Exception]] = dict()

        # TODO: Validate constraints
        # TODO: Validate inputs
        # TODO: Handle node issues
        # TODO: Derive implicit edges

        # 1. Collect names
        names: dict[str, ObjectID]
        names = self.collect_names()

        # 2. Compile expressions
        expressions: dict[ObjectID, BoundExpression]
        expressions = self.compile_expressions(names)

        # 3. Sort nodes in order of computation


        sorted_nodes = self.sort_nodes(list(expressions.keys()))
        compiled.sorted_expression_nodes = sorted_nodes

        # Finalize and collect issues

        return compiled
    #
    # def compile_expression(self, node: ObjectID, names: dict[str, ObjectID]):
    #     component: ExpressionComponent
    #
    #     parser = ExpressionParser(component.expression)
    #
    #     # TODO: try:
    #     unbound_expression = parser.parse()
    #
    #     # TODO: except -> throw NodeError
    #
    #     validate_inputs(node)

    def collect_names(self) -> dict[str, ObjectID]:
        """
        Collect names of objects.

        Raises an exception when there are duplicate names.

        :raises Exception: when duplicate names are found.
        """
        # import pdb; pdb.set_trace();
        names: defaultdict[str, list[ObjectID]] = defaultdict(list)
        issues: defaultdict[ObjectID, list[NodeIssue]] = defaultdict(list)

        for node in self.graph.select_nodes(Metamodel.expression_nodes):
            name = node[ExpressionComponent].name
            names[name].append(node.id)

        dupes: list[str] = list()
        result: dict[str, ObjectID] = dict()

        for name, ids in names.items():
            if len(ids) > 1:
                issue = NodeIssue.duplicate_name(name)
                dupes.append(name)
                for id in ids:
                    issues[id].append(issue)
            else:
                result[name] = ids[0]

        if issues:
            raise CompilerError(issues, f"Duplicate names: {dupes}")
        else:
            return result


    def compile_expressions(self, names: dict[str,ObjectID]) -> dict[ObjectID, BoundExpression]:
        """
        Compile node expressions into bound expressions.

        :param dict[str,ObjectID] names: Mapping of object names to node IDs.

        :return: Mapping of node IDs to compiled bound expressions.
        """
        issues: defaultdict[ObjectID, list[NodeIssue]] = defaultdict(list)

        # TODO: Validate inputs
        expressions: dict[ObjectID, BoundExpression] = dict()

        for node in self.graph.select_nodes(Metamodel.expression_nodes):
            component = node[ExpressionComponent]
                
            try:
                parser = ExpressionParser(component.expression)
                unbound_expr = parser.parse()
                bound_expr = bind_expression(unbound_expr,
                                             variables=names,
                                             functions=BuiltinFunctions)
                expressions[node.id] = bound_expr

            except SyntaxError as error:
                issue = NodeIssue.expression_syntax_error(str(error))
                issues[node.id].append(issue)

        if issues:
            raise CompilerError(issues, f"Syntax errors detected")
        else:
            return expressions


    def validate_inputs(self, node: ObjectID, required: list[str]) -> list[NodeIssue]:
        """
        Validate parameters of a node.

        A node using parameters, such as an
        expression node, must have inputs for the used parameters connected.
        In additional to that, all connected parameters must be used.
        
        An error is returned when a node is using a parameter that is not
        connected or when a connected parameter is not used.
        
        This function is guarding logical consistency of the model.

        :param ObjectID node: ID of a node to validate.
        :param list[str] names: List of variable names used in the node
        expression.
        """
        vars: set[str] = set(required)
        incoming_params = self.graph.select_neighbors(node,
                                                      Metamodel.incoming_parameters)

        incoming_names: set[str] = set()

        for param_node in incoming_params.nodes:
            expr = param_node[ExpressionComponent]
            name = expr.name
            incoming_names.add(name)

        unknown = vars - incoming_names
        unused = incoming_names - vars

        unknown_issues = (
                NodeIssue.unknown_parameter(f"{param}")
                for param in unknown
                )
        unused_issues = (
                NodeIssue.unused_input(f"{param}")
                for param in unused
                )

        return list(unknown_issues) + list(unused_issues)

    def sort_nodes(self, nodes: list[ObjectID]) -> list[Node]:
        # FIXME: Quickly hacked together.
        edges: list[Edge] = list()
        
        sorted = self.graph.topological_sort(nodes, edges)

        self.sorted_expression_nodes = list(self.graph.node(id)
                                            for id in sorted)
        result: list[Node] = list()

        for node_id in sorted:
            if not (node := self.graph.node(node_id)):
                raise RuntimeError("Something went wrong")
            result.append(node)

        return result


    

