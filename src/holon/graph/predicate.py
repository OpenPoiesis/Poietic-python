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
    object_types: list[ObjectType]

    def __init__(self, object_type: ObjectType | list[ObjectType]):
        if isinstance(object_type, ObjectType):
            self.object_types = [object_type]
        else:
            self.object_type = object_type

    def match(self, graph: Graph, object: ObjectSnapshot) -> bool: # pyright: ignore
        return all(object.type is t for t in self.object_types)


# class EdgeEndpointPredicate(EdgePredicate):
#     """Constraint requirement for edge and its endpoints."""
#
#     # TODO: Change to Union[None, ObjectType, list[ObjectType]]
#     edge_type: Optional[ObjectType]
#     """Type that the edge is required to be."""
#     origin_type: Optional[ObjectType]
#     """Type that the origin is required to be."""
#     target_type: Optional[ObjectType]
#     """Type that the target is required to be."""
#
#     def __init__(self,
#                   edge_type: Optional[ObjectType]=None,
#                   origin_type: Optional[ObjectType]=None,
#                   target_type: Optional[ObjectType]=None):
#         """Create a new edge endpoint type requirement."""
#         if edge_type is not None:
#             assert edge_type.structural_type is Edge
#         if origin_type is not None:
#             assert origin_type.structural_type is Node
#         if target_type is not None:
#             assert target_type.structural_type is Node
#
#         self.edge_type = edge_type
#         self.origin_type = origin_type
#         self.target_type = target_type
#
#     def match_edge(self, graph: Graph, edge: Edge) -> bool:
#         assert isinstance(edge, Edge), \
#                 f"Expected edge, got: {edge}"
#
#         edge = cast(Edge, edge)
#
#         origin: Node = graph.node(edge.origin)
#         target: Node = graph.node(edge.target)
#         if (origin_type := self.origin_type):
#             if origin.type is not origin_type:
#                 return False
#
#         if (target_type := self.target_type):
#             if target.type is not target_type:
#                 violators.append(edge)
#                 return False
#
#         if (edge_type := self.edge_type):
