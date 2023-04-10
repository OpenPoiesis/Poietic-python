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

from ..db.object import ObjectSnapshot, ObjectType
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
    def match(self, graph: Graph, object: ObjectSnapshot) -> bool: # pyright: ignore
        return True


class HasComponentPredicate(ObjectPredicate):
    component_type: Type[Component] 

    def __init__(self, component_type: Type[Component]):
        self.component_type = component_type

    def match(self, graph: Graph, object: ObjectSnapshot) -> bool: # pyright: ignore
        return object.components.has(self.component_type)
    
class IsTypePredicate(ObjectPredicate):
    object_type: ObjectType

    def __init__(self, object_type: ObjectType):
        self.object_type = object_type

    def match(self, graph: Graph, object: ObjectSnapshot) -> bool: # pyright: ignore
        return object.type is self.object_type

