# graph.py
#
# Created by: Stefan Urbanek
# Date: 2023-03-30

# TODO: IMPORTANT: Graph .node(id) and .edge(id) should raise IdentityError

from typing import Protocol, Iterable, Optional, Self, cast, TYPE_CHECKING
from abc import abstractmethod
from enum import Enum, auto

from ..db.object import ObjectID, ObjectSnapshot
from ..db.object_type import ObjectType
from ..db.component import Component
from ..db.version import VersionID
from ..db.frame import VersionFrame
from ..common import first
from ..errors import IDError

if TYPE_CHECKING:
    from .predicate import NodePredicate, EdgePredicate

__all__ = [
    "Graph",
    "MutableGraph",
    "Node",
    "Edge",

    "EdgeDirection",
    "NeighborhoodSelector",
    "Neighborhood",

    "BoundGraph",
    "UnboundGraph",

    # Draft
    # "MutableUnboundGraph",
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

    def __init__(self,
                 id: ObjectID,
                 version: VersionID,
                 origin: ObjectID,
                 target: ObjectID,
                 type: Optional[ObjectType]=None,
                 components: Optional[list[Component]] = None):
        """
        Create a new object with given identity and version.
        The combination of object identity and version must be unique within the database.
        """
        super().__init__(id=id,
                         version=version,
                         type=type,
                         components=components)
        self.origin = origin
        self.target = target


    def derive(self, version: VersionID, id: Optional[ObjectID] = None) -> Self:
        """Derive a new edge, keeping the same origin and target."""
        # FIXME: This is a workaround before I figure out how to have better structual components
        derived = self.__class__(id=id or self.id,
                                 version=version,
                                 origin=self.origin,
                                 target=self.target,
                                 type=self.type,
                                 components = self.components.as_list())

        return derived

    def structural_dependencies(self) -> list[ObjectID]:
        """Return objects that structurally depend on the receiver.

        For example an edge depends on a node that is an endpoint of the edge.
        """
        return [self.origin, self.target]

class EdgeDirection(Enum):
    OUTGOING = auto()
    INCOMING = auto()


class EdgeEndpoint(Enum):
    ORIGIN = auto()
    TARGET = auto()


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

    def node(self, id: ObjectID) -> Node:
        node = next((obj for obj in self.nodes() if obj.id == id), None)
        
        if (unwrapped := node):
            return unwrapped
        else:
            raise IDError(id)


    def edge(self, id: ObjectID) -> Edge:
        edge = next((obj for obj in self.edges() if obj.id == id), None)

        if (unwrapped := edge):
            return unwrapped
        else:
            raise IDError(id)


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

    def select_neighbors(self,
                  id: ObjectID,
                  selector: "NeighborhoodSelector") -> "Neighborhood":
        
        edges: Iterable[Edge]

        match selector.direction:
            case EdgeDirection.INCOMING: edges = self.incoming(id)
            case EdgeDirection.OUTGOING: edges = self.outgoing(id)

        filtered_edges = (edge for edge in edges
                          if selector.predicate.match_edge(self, edge))
        
        return Neighborhood(self,
                            selector=selector,
                            node_id=id,
                            edges=filtered_edges)

    def select_nodes(self, predicate: "NodePredicate") -> Iterable[Node]:
        return (node for node in self.nodes()
                if predicate.match_node(self, node))

    def select_edges(self, predicate: "EdgePredicate") -> Iterable[Edge]:
        return (edge for edge in self.edges()
                if predicate.match_edge(self, edge))


    # FIXME: We need to liberate the graph, but that is too complex in Python
    # if we want to retain type annotations.

    def topological_sort(self,
                         to_sort: list[ObjectID],
                         edges: list[Edge]) -> list[ObjectID]:
        sorted: list[ObjectID] = list()
        nodes: list[ObjectID] = list(to_sort)

        # Create a copy
        edges = list(edges)

        targets = set(edge.target for edge in edges)
        sources: list[ObjectID] = list(node for node in nodes
                                       if node not in targets) 

        while sources:
            node = sources.pop()
            sorted.append(node)
            outgoings = list(edge for edge in edges if edge.origin == node)
            for edge in outgoings:
                m = edge.target
                edges.remove(edge)
                incomings = any(edge for edge in edges if edge.target == m)
                # If there are no incoming edges ... 
                if not incomings:
                    sources.append(m)

        if edges:
            raise Exception("[UNHANDLED] Cycle")
        else:
            return sorted


    def debug_print(self):
        print("NODES:")
        for node in self.nodes():
            if node.type:
                typename = node.type.name
            else:
                typename = "(none)"
            print(f"    {node.id}: {typename}")
        print("EDGES:")
        for edge in self.edges():
            if edge.type:
                typename = edge.type.name
            else:
                typename = "(none)"
            print(f"    {edge.id}: {typename} {edge.origin} -> {edge.target}")


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

    def node(self, id: ObjectID) -> Node:
        node = self.frame.object(id)

        if isinstance(node, Node):
            return node
        else:
            raise TypeError

    def edge(self, id: ObjectID) -> Edge:
        edge = self.frame.object(id)

        if isinstance(edge, Edge):
            return edge
        else:
            raise TypeError


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

    def node(self, id: ObjectID) -> Node:
        return self._nodes[id]

    def edge(self, id: ObjectID) -> Edge:
        return self._edges[id]

    def contains_node(self, id: ObjectID) -> bool:
        return id in self._nodes

    def contains_edge(self, id: ObjectID) -> bool:
        return id in self._edges


class NeighborhoodSelector:
    direction: "EdgeDirection"
    predicate: "EdgePredicate"

    def __init__(self,
                 predicate: "EdgePredicate",
                 direction: "EdgeDirection"):
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

            node = self.graph.node(node_id)
            yield node

    @property
    def first_edge(self) -> Optional[Edge]:
        return first(iter(self.edges))

    @property
    def first_node(self) -> Optional[Node]:
        return first(iter(self.nodes))
