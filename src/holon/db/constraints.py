# constraint.py
#
# Database and graph constraints.
#
# Created by: Stefan Urbanek
# Date: 2023-04-17
#

from ..graph import Graph, Edge, Node, EdgeDirection
from ..graph import NodePredicate, EdgePredicate
from .object import ObjectID, ObjectSnapshot
from ..value import ValueProtocol
from .object_type import ObjectType 
from ..attributes import AttributeReference

from typing import Optional, cast, Iterable, Protocol

from abc import abstractmethod

"""

Predicate

NodeConstraint(NodePredicate, NodeRequirement)

EdgeConstraint(EdgePredicate, EdgeRequirement)

NodePredicate.match(node)
EdgePredicate.match(edge)

ObjectPredicate

"""

class ConstraintViolation:
    """
    Structure that contains information about a violated constraint. The
    structure is returned by ``ConstraintChecker/check(graph:)``

    The structure contains a list of nodes and edges that violated the
    constraint.
    """

    """Constraint that was violated and produced this violation."""
    constraint: "Constraint"
    
    """List of nodes that the constraint evaluated as being offensive."""
    nodes: list[ObjectID]
    
    """List of edges that the constraint evaluated as being offensive."""
    
    edges: list[ObjectID]

    """Human-readable description of the violation."""
    def __str__(self) -> str:
        nodes = ", ".join(str(node) for node in self.nodes)
        edges = ", ".join(str(edge) for edge in self.edges)
        return f"ConstraintViolation({self.constraint.name}, {nodes}, {edges})"

class Constraint:
    """Definition of a database constraint.

    Constraints have two components: match predicate and a requirement. The
    match predicate selectes the objects that are going to be validated. The
    requirement is a condition that the matched objects must satisfy. Objects
    selected by the predicate that do not satisfy the requirement are
    constraint violators.
    """

    name: str
    """An identifier of the constraint. Should be unique within set of
    constraints in a database."""
    description: str
    """Human-readable description of the constraint."""
    @abstractmethod
    def check(self, graph: Graph) -> list[ObjectID]:
        ...


class NodeConstraint(Constraint):
    match: NodePredicate
    """Predicate that matches the objects to be verified by the constraint."""

    requirement: "NodeConstraintRequirement"
    """Requirement that the matched objects must satisfy."""

    def __init__(self,
                 name: str,
                 description: str,
                 predicate: NodePredicate,
                 requirement: "NodeConstraintRequirement"):
        self.name = name
        self.description = description
        self.predicate = predicate
        self.requirement = requirement

    @abstractmethod
    def check(self, graph: Graph) -> list[ObjectID]:
        matching = graph.select_nodes(self.predicate)
        violating = self.requirement.check_nodes(graph, matching)
        return violating


class NodeConstraintRequirement(Protocol):
    """Abstract class for cosntraint requirements.

    Constraint requirement is checked on all objets selected by the constraint
    predicate.
    """
    def check_nodes(self, graph: Graph, nodes: Iterable[Node]) -> list[Node]:
        """
        Check the given objects within the given graph and return a list of
        objects that violate the requirement. Returned empty list means that
        all objects satisfy the requirement - there are no violators.
        """
        ...

class ObjectConstraintRequirement(NodeConstraintRequirement, Protocol):
    """Abstract class for cosntraint requirements.

    Constraint requirement is checked on all objets selected by the constraint
    predicate.
    """
    def check(self, graph: Graph, objects: Iterable[ObjectSnapshot]) -> list[ObjectSnapshot]:
        """
        Check the given objects within the given graph and return a list of
        objects that violate the requirement. Returned empty list means that
        all objects satisfy the requirement - there are no violators.
        """
        ...

    def check_nodes(self, graph: Graph, nodes: Iterable[Node]) -> list[Node]:
        return cast(list[Node], self.check(graph=graph, objects=nodes))

    def check_edges(self, graph: Graph, edges: Iterable[Edge]) -> list[Edge]:
        return cast(list[Edge], self.check(graph=graph, objects=edges))

class UniqueNeighborRequirement(NodeConstraintRequirement):
    predicate: EdgePredicate
    direction: EdgeDirection

    def __init__(self,
                 predicate: EdgePredicate,
                 direction: EdgeDirection=EdgeDirection.OUTGOING):
        self.predicate = predicate
        self.direction = direction

    def check_nodes(self, graph: Graph, objects: Iterable[Node]) -> list[Node]:
        raise NotImplementedError


class EdgeConstraintRequirement:
    """Abstract class for cosntraint requirements.

    Constraint requirement is checked on all objets selected by the constraint
    predicate.
    """
    @abstractmethod
    def check(self, graph: Graph, objects: list[Edge]) -> list[Edge]:
        """
        Check the given objects within the given graph and return a list of
        objects that violate the requirement. Returned empty list means that
        all objects satisfy the requirement - there are no violators.
        """
        pass


class AcceptAll(EdgeConstraintRequirement):
    """Requirement that satisfies all objects - used as a placeholder or for
    testing purposes. This requirement does not have much practical use."""
    def check(self, graph: Graph, objects: list[Edge]) -> list[Edge]:
        return list()


class UniqueAttribute(ObjectConstraintRequirement):
    attribute: AttributeReference

    def __init__(self, attribute: AttributeReference):
        self.attribute = attribute

    def check(self, graph: Graph, objects: list[Edge]) -> list[Edge]:
        seen: dict[ValueProtocol, list[Edge]] = dict()

        for object in objects:
            component = object[self.attribute.component]
            value = getattr(component, self.attribute.name)

            if value not in seen:
                seen[value] = [object]
            else:
                seen[value].append(object)

        dupes: list[Edge] = list()
        for ids in seen.values():
            if len(ids) > 1:
                dupes += ids

        return dupes


class EdgeEndpointType(EdgeConstraintRequirement):
    """Constraint requirement for edge and its endpoints."""

    # TODO: Change to Union[None, ObjectType, list[ObjectType]]
    edge_type: Optional[ObjectType]
    """Type that the edge is required to be."""
    origin_type: Optional[ObjectType]
    """Type that the origin is required to be."""
    target_type: Optional[ObjectType]
    """Type that the target is required to be."""

    def __init__(self,
                  edge_type: Optional[ObjectType]=None,
                  origin_type: Optional[ObjectType]=None,
                  target_type: Optional[ObjectType]=None):
        """Create a new edge endpoint type requirement."""
        if edge_type is not None:
            assert edge_type.structural_type is Edge
        if origin_type is not None:
            assert origin_type.structural_type is Node
        if target_type is not None:
            assert target_type.structural_type is Node

        self.edge_type = edge_type
        self.origin_type = origin_type
        self.target_type = target_type

    def check(self,
              graph: Graph,
              objects: list[Edge]) -> list[Edge]:
        violators: list[Edge] = list()

        for edge in objects:
            assert isinstance(edge, Edge), \
                    f"Expected edge, got: {edge}"

            edge = cast(Edge, edge)

            origin: Node = graph.node(edge.origin)
            target: Node = graph.node(edge.target)
            if (origin_type := self.origin_type):
                if origin.type is not origin_type:
                    violators.append(edge)
                    continue

            if (target_type := self.target_type):
                if target.type is not target_type:
                    violators.append(edge)
                    continue

        return violators
