# graph.py
#
# Created by: Stefan Urbanek
# Date: 2023-03-30

from typing import Protocol, Iterable, Optional, Self, cast
from abc import abstractmethod

from .object import ObjectID, ObjectSnapshot
from .version import VersionID
from .frame import VersionFrame
from .transaction import Transaction

__all__ = [
    "Graph",
    "Node",
    "Edge",
    "BoundGraph",
    "UnboundGraph",
]

# Structural Object Types
# --------------------------------------------------------------------------

class Node(ObjectSnapshot):
    """Structural object type representing nodes in a graph."""
    pass


class Edge(ObjectSnapshot):
    """Structural object type representing a directed edge in a graph."""

    origin: ObjectID
    """Origin endpoint (arrow tail) of the directed edge."""
    target: ObjectID
    """Target endpoint (arrow head) of the directed edge."""

    def derive(self, version: VersionID, id: Optional[ObjectID] = None) -> Self:
        """Derive a new edge, keeping the same origin and target."""
        derived = super().derive(version=version, id=id)
        derived.origin = self.origin
        derived.target = self.target

        return derived

    def structural_dependencies(self) -> list[ObjectID]:
        """Return objects that structurally depend on the receiver.

        For example an edge depends on a node that is an endpoint of the edge.
        """
        return [self.origin, self.target]

# Graph Protocol
# --------------------------------------------------------------------------


class Graph(Protocol):
    """Protocol describing graphs.

    Types conforming to this protocol must implement at least the `nodes()` and
    `edges()` functions. The rest of the functions have a default
    implementation that iterates through all nodes or edges.

    It is recommended to provide optimal implementaiton for respective methods,
    if possible.
    """
    @abstractmethod
    def nodes(self) -> Iterable[Node]:
        ...

    @abstractmethod
    def edges(self) -> Iterable[Edge]:
        ...

    @property
    def node_ids(self) -> Iterable[ObjectID]:
        return (node.id for node in self.nodes())

    @property
    def edgde_ids(self) -> Iterable[ObjectID]:
        return (edge.id for edge in self.edges())

    def node(self, id: ObjectID) -> Optional[Node]:
        return next((obj for obj in self.nodes() if obj.id == id), None)

    def edge(self, id: ObjectID) -> Optional[Edge]:
        return next((obj for obj in self.edges() if obj.id == id), None)

    def contains_node(self, id: ObjectID) -> bool:
        return any(node.id == id for node in self.nodes())

    def contains_edge(self, id: ObjectID) -> bool:
        return any(edge.id == id for edge in self.edges())

    def outgoing(self, id: ObjectID) -> Iterable[Edge]:
        return (edge for edge in self.edges() if edge.origin == id)

    def incoming(self, id: ObjectID) -> Iterable[Edge]:
        return (edge for edge in self.edges() if edge.target == id)

    def neighbors(self, id: ObjectID) -> Iterable[Edge]:
        return (edge for edge in self.edges() if edge.origin == id or edge.target == id)



class MutableGraph(Graph, Protocol):
    @abstractmethod
    def insert_node(self, node: Node):
        ...

    @abstractmethod
    def insert_edge(self, edge: Edge):
        ...

    @abstractmethod
    def remove_node(self, node: Node) -> list[ObjectID]:
        ...

    @abstractmethod
    def remove_edge(self, edge: Edge):
        ...



class UnboundGraph(Graph):
    """Slow graph on top of a mutable frame."""
    frame: VersionFrame

    def __init__(self, frame: VersionFrame):
        self.frame = frame

    def nodes(self) -> Iterable[Node]:
        return (obj for obj in self.frame.objects.values()
                if isinstance(obj, Node))
    def edges(self) -> Iterable[Edge]:
        return (obj for obj in self.frame.objects.values()
                if isinstance(obj, Edge))


class MutableUnboundGraph(UnboundGraph, MutableGraph):
    """Mutable unbound graph is a view on top of a version frame where changes
    to the graph are applied within associated transaction.

    Any structural changes of the graph (adding node/edge, removing node/edge)
    result in a transaction operation in a way that the structural integrity
    of the frame is maintained.
    """

    transaction: Transaction

    def __init__(self, frame: VersionFrame, transaction: Transaction):
        """Create a new unbound-graph view on top of a version frame `frame`
        within a transaction `transaction.
        """
        super().__init__(frame)
        self.transaction = transaction

    def insert_node(self, node: Node):
        self.transaction.insert_derived(node)

    def insert_edge(self, edge: Edge):
        assert self.frame.contains(edge.origin), \
                f"The graph does not contain origin node {edge.origin}"
        assert self.frame.contains(edge.target), \
                f"The graph does not contain target node {edge.target}"
        self.transaction.insert_derived(edge)

    def remove_node(self, node_id: ObjectID) -> list[ObjectID]:
        return self.transaction.remove_object_cascading(node_id)

    def remove_edge(self, edge_id: ObjectID):
        self.transaction.remove_object(edge_id)


class BoundGraph(Graph):
    """Fast, immutable graph derived from an immutable frame."""
    _nodes: dict[ObjectID, Node]
    _edges: dict[ObjectID, Edge]

    def __init__(self, frame: VersionFrame):
        assert not frame.state.is_mutable

        for obj in frame.objects.values():
            if isinstance(obj, Node):
                node = cast(Node, obj)
                self._nodes[node.id] = node
            elif isinstance(obj, Edge):
                edge = cast(Edge, obj)
                self._edges[edge.id] = edge
            else:
                assert True, f"Invalid object type: {obj.__class__}"

    def nodes(self) -> Iterable[Node]:
        return self._nodes.values()

    def edges(self) -> Iterable[Edge]:
        return self._edges.values()

    def node(self, id: ObjectID) -> Optional[Node]:
        return self._nodes.get(id)

    def edge(self, id: ObjectID) -> Optional[Edge]:
        return self._edges.get(id)

    def contains_node(self, id: ObjectID) -> bool:
        return id in self._nodes

    def contains_edge(self, id: ObjectID) -> bool:
        return id in self._edges

