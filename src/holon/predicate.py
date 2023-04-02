# predicate.py
#
# Entities for predicates matching raw or structural objects (such as nodes or
# edges).
#
# Created by: Stefan Urbanek
# Date: 2023-04-01
#


from typing import Protocol, Type

from .graph import Graph, Node, Edge
from .object import ObjectSnapshot
from .component import Component

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
    

