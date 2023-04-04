# predicate.py
#
# Entities for predicates matching raw or structural objects (such as nodes or
# edges).
#
# Created by: Stefan Urbanek
# Date: 2023-04-01
#


from typing import Protocol, Type, Iterable

from .graph import Graph, Node, Edge, EdgeDirection

from ..db.object import ObjectSnapshot, ObjectType, ObjectID
from ..db.component import Component


__all__ = [
    "NodePredicate",
    "EdgePredicate",
    "ObjectPredicate",
    "AnyPredicate",
    "HasComponentPredicate",
]

class NodePredicate(Protocol):
    def match_node(self, graph: Graph, node: Node) -> bool:
        ...

class EdgePredicate(Protocol):
    def match_edge(self, graph: Graph, edge: Edge) -> bool:
        ...

class ObjectPredicate(NodePredicate, EdgePredicate, Protocol):
    def match_node(self, graph: Graph, node: Node) -> bool:
        return self.match(graph=graph, object=node)

    def match_edge(self, graph: Graph, edge: Edge) -> bool:
        return self.match(graph=graph, object=edge)

    def match(self, graph: Graph, object: ObjectSnapshot) -> bool:
        ...

class AnyPredicate(ObjectPredicate):
    def match(self, graph: Graph, object: ObjectSnapshot) -> bool:
        return True


class HasComponentPredicate(ObjectPredicate):
    component_type: Type[Component] 

    def __init__(self, component_type: Type[Component]):
        self.component_type = component_type

    def match(self, graph: Graph, object: ObjectSnapshot) -> bool:
        return object.components.has(self.component_type)
    
class IsTypePredicate(ObjectPredicate):
    object_type: ObjectType

    def __init__(self, object_type: ObjectType):
        self.object_type = object_type

    def match(self, graph: Graph, object: ObjectSnapshot) -> bool:
        return object.type is self.object_type

class NeighborhoodSelector:
    direction: EdgeDirection
    predicate: EdgePredicate

    def __init__(self,
                 predicate: EdgePredicate,
                 direction: EdgeDirection):
        self.direction = direction
        self.predicate = predicate

class Neighborhood:
    graph: Graph
    node_id: ObjectID
    selector: NeighborhoodSelector
    edges: Iterable[Edge]

    def __init__(self,
                 graph: Graph,
                 node_id: ObjectID,
                 selector: NeighborhoodSelector,
                 edges: Iterable[Edge]):
        """Create a neighbourhood query.

        :param Graph graph: Graph containing the neighbourhood.
        :param ObjectID node_id: The node that the neighbourhood is connected to.
        :param NeighborhoodSelector selector: Selector used to create the query.
        :param edges: Iterator over the edges from the graph that are part of the neighbourhood.

        .. note:
            Currently you should not create objects of this type. They are a
            result from ``Graph.select_neighbors``.

        """
        self.graph = graph
        self.selector = selector
        self.node_id = node_id
        self.edges = edges

    @property
    def nodes(self) -> Iterable[Node]:
        """Get an iterator of nodes that are at the endpoing of the
        neighbourhood edges specified by the ``direction``."""
        for edge in self.edges:
            node_id: ObjectID
            match self.selector.direction:
                case EdgeDirection.INCOMING: node_id = edge.origin
                case EdgeDirection.OUTGOING: node_id = edge.target

            if not (node := self.graph.node(node_id)):
                # This should not happen
                raise RuntimeError(f"Unknown node {node_id}")
            yield node

