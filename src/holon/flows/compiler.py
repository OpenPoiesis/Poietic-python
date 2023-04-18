# compiler.py
#
# Created by: Stefan Urbanek
# Date: 2023-04-01

from typing import Optional
from ..db import ObjectID, Transaction
from ..graph import Graph, Node, Edge
from ..db import MutableUnboundGraph
from collections import defaultdict

from .model import StockComponent, ExpressionComponent
from .model import Metamodel
from ..expression import *
from ..expression.parser import ExpressionParser

from .issues import CompilerError, NodeIssue
from .functions import BuiltinFunctions

from .evaluate import BoundExpression, bind_expression


__all__ = [
    "DomainView",
    "Compiler",
]



class CompiledModel:
    """Compiled stocks-flows model into a representation that can be
    interpreted directly by the simulator without requiring the graph.
    """
    expressions: dict[ObjectID, BoundExpression]
    # TODO: We just need IDs here
    sorted_expression_nodes: list[Node]
    """Expression nodes sorted in their order of evaluation dependency."""

    auxiliaries: list[ObjectID]
    """List of auxiliaries, in their order of evaluation (parameter)
    dependency."""

    flows: list[ObjectID]
    """List of flows, in their order of evaluation (parameter)
    dependency."""

    stocks: list[ObjectID]
    """List of stocks, in their order of evaluation (parameter)
    dependency."""

    stock_components: dict[ObjectID, StockComponent]
    """Extracted components for stocks."""
    # flow_components: dict[ObjectID, FlowComponent]

    outflows: dict[ObjectID, list[ObjectID]]
    """Mapping of outflows from a stock. Key is the stock and value is a list
    of flows which are draining the stock."""

    inflows: dict[ObjectID, list[ObjectID]]
    """Mapping of inflows to a stock. Key is the stock and value is a list
    of flows which are filling the stock."""


    def __init__(self):
        self.expressions = dict()
        self.sorted_expression_nodes = list()
        self.auxiliaries = list()
        self.flows = list()
        self.stocks = list()

        self.stock_components = dict()
        # self.flow_components = dict()
        self.outflows = dict()
        self.inflows = dict()


class DomainView:
    """Object providing Flows domain-specific view on a graph."""
    graph: Graph

    def __init__(self, graph: Graph):
        self.graph = graph

    def collect_names(self) -> dict[str, ObjectID]:
        """
        Collect names of objects.

        Raises an exception when there are duplicate names.

        :raises Exception: when duplicate names are found.
        """
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
        """Sort the nodes based on parameter dependency."""

        edges: list[Edge] = list(self.graph.select_edges(Metamodel.parameter_edges))
        
        sorted = self.graph.topological_sort(nodes, edges)

        self.sorted_expression_nodes = list(self.graph.node(id)
                                            for id in sorted)
        result: list[Node] = list()

        for node_id in sorted:
            node = self.graph.node(node_id)
            result.append(node)

        return result


    def flow_fills(self, flow_id: ObjectID) -> Optional[ObjectID]:
        # TODO: Can this be simplified?
        flow_node = self.graph.node(flow_id)
        assert flow_node.type is Metamodel.Flow

        hood = self.graph.select_neighbors(flow_id, Metamodel.fills)

        if (node := hood.first_node):
            return node.id
        else:
            return None


    def flow_drains(self, flow_id: ObjectID) -> Optional[ObjectID]:
        # TODO: Can this be simplified?
        flow_node = self.graph.node(flow_id)
        assert flow_node.type is Metamodel.Flow

        hood = self.graph.select_neighbors(flow_id, Metamodel.drains)

        if (node := hood.first_node):
            return node.id
        else:
            return None


    def implicit_fills(self, stock_id: ObjectID) -> list[ObjectID]:
        # TODO: Can this be simplified?
        stock_node = self.graph.node(stock_id)
        assert stock_node.type is Metamodel.Stock

        hood = self.graph.select_neighbors(stock_id, Metamodel.implicit_fills)

        return list(node.id for node in hood.nodes) 


    def implicit_drains(self, stock_id: ObjectID) -> list[ObjectID]:
        # TODO: Can this be simplified?
        stock_node = self.graph.node(stock_id)
        assert stock_node.type is Metamodel.Stock

        hood = self.graph.select_neighbors(stock_id, Metamodel.implicit_drains)

        return list(node.id for node in hood.nodes) 
        


class Compiler:
    """Object that updates the graph with derived information and creates a
    compiled model."""

    graph: MutableUnboundGraph
    transaction: Transaction
    view: DomainView

    def __init__(self, transaction: Transaction):
        self.transaction = transaction
        self.graph = self.transaction.graph
        self.view = DomainView(self.graph)

    def compile(self) -> CompiledModel:
        compiled = CompiledModel()


        # node_issues: dict[ObjectID, list[Exception]] = dict()

        # TODO: Validate constraints
        # TODO: Validate inputs
        # TODO: Handle node issues
        # TODO: Derive implicit edges

        # 1. Collect names
        names: dict[str, ObjectID]
        names = self.view.collect_names()

        # 2. Compile expressions
        expressions: dict[ObjectID, BoundExpression]
        expressions = self.view.compile_expressions(names)
        compiled.expressions = expressions

        # 3. Sort nodes in order of computation


        sorted_nodes = self.view.sort_nodes(list(expressions.keys()))
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

    def update_implicit_flows(self):
        """Updates the implicit flows between stocks.

        Implicit flows are edges between two stocks where the origin of the
        edge is a stock which the flow drains and the target of the edge is a
        stock which the flow fills.

        This function removes implicit edges that have no flow and adds new
        edges when there are new flows.
        """
        existing: list[Edge] = list(self.graph.select_edges(Metamodel.implicit_flow_edge))

        for flow in list(self.graph.select_nodes(Metamodel.flow_nodes)):
            if not (fills := self.view.flow_fills(flow.id)):
                continue
            if not (drains := self.view.flow_drains(flow.id)):
                continue
            
            # Lambda would be better, but type-annotating lambdas is a bit of a
            # pain

            index: Optional[int] = None

            for (i, edge) in enumerate(existing):
                if edge.origin == drains and edge.target == fills:
                    index = i
                    break

            if index is not None:
                del existing[index]
                continue

            self.graph.create_edge(Metamodel.ImplicitFlow,
                                   origin=drains,
                                   target=fills)

        # Clean-up unused edges
        for edge in existing:
            self.graph.remove_edge(edge.id)

    

