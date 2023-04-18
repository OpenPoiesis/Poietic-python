# transaction.py
#
# Created by: Stefan Urbanek
# Date: 2023-03-30
#

from contextlib import contextmanager
from .version import VersionID, VersionState

from .frame import VersionFrame
from .object import ObjectID, ObjectSnapshot
from .object_type import ObjectType
from .component import Component

from typing import Optional, TypeVar
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .database import Database

from ..graph import UnboundGraph, MutableGraph, Node, Edge

C = TypeVar("C", bound=Component)

__all__ = [
    "Transaction",
    "MutableUnboundGraph",
]

class MutableUnboundGraph(UnboundGraph, MutableGraph):
    """Mutable unbound graph is a view on top of a version frame where changes
    to the graph are applied within associated transaction.

    Any structural changes of the graph (adding node/edge, removing node/edge)
    result in a transaction operation in a way that the structural integrity
    of the frame is maintained.
    """

    transaction: "Transaction"

    def __init__(self, transaction: "Transaction"):
        """Create a new unbound-graph view on top of a version frame `frame`
        within a transaction `transaction.
        """
        super().__init__(transaction.frame)
        self.transaction = transaction

    def insert_node(self, node: Node):
        self.transaction.insert_derived(node)

    def insert_edge(self, edge: Edge):
        assert self.frame.contains(edge.origin), \
                f"The graph does not contain origin node {edge.origin}"
        assert self.frame.contains(edge.target), \
                f"The graph does not contain target node {edge.target}"
        self.transaction.insert_derived(edge)

    # FIXME:[DEBT] This needs redesign.
    # FIXME: Add tests
    def create_node(self,
               object_type: ObjectType,
               components: Optional[list[Component]] = None) -> ObjectID:
        # TODO: Prefer this convenience method
        assert object_type.structural_type is Node
        object = Node(id=0,
                      version=self.transaction.version,
                      type=object_type,
                      components=components)
        object.state = VersionState.TRANSIENT
        # Insert missing but required components with default initialization
        #
        for comp_type in object_type.component_types:
            if not object.components.has(comp_type):
                object.components.set(comp_type())

        # FIXME: We are unnecessarily creating two copies of the object here
        return self.transaction.insert_derived(object)


    # FIXME:[DEBT] This needs redesign.
    # FIXME: This is not properly designed, as well as other create_* methods
    # FIXME: Add tests
    def create_edge(self,
                object_type: ObjectType,
                origin: ObjectID,
                target: ObjectID,
                components: Optional[list[Component]] = None) -> ObjectID:
        # TODO: Prefer this convenience method
        assert object_type.structural_type is Edge
        assert self.transaction.frame.contains(origin)
        assert self.transaction.frame.contains(target)

        object = Edge(id=0,
                      version=self.transaction.version,
                      origin=origin,
                      target=target,
                      type=object_type,
                      components=components)
        object.state = VersionState.TRANSIENT
        # Insert missing but required components with default initialization
        #
        for comp_type in object_type.component_types:
            if not object.components.has(comp_type):
                object.components.set(comp_type())

        # FIXME: We are unnecessarily creating two copies of the object here
        return self.transaction.insert_derived(object)


    def remove_node(self, node_id: ObjectID) -> list[ObjectID]:
        return self.transaction.remove_object_cascading(node_id)

    def remove_edge(self, edge_id: ObjectID):
        self.transaction.remove_object(edge_id)


class Transaction:
    # TODO: Make private
    is_open: bool
    version: VersionID
    frame: VersionFrame
    database: "Database"

    removed_objects: list[ObjectID]
    derived_objects: dict[ObjectID, ObjectSnapshot]

    def __init__(self, database: "Database", frame: VersionFrame):
        self.version = frame.version
        self.frame = frame
        self.database = database
        self.removed_objects = list()
        self.derived_objects = dict()
        self.is_open = True

    @property
    def graph(self) -> MutableUnboundGraph:
        """Get a mutable graph associated with this transaction.

        Any changes with the graph will be registered with the transaction.
        """
        return MutableUnboundGraph(self)

    @property
    def has_changes(self) -> bool:
        return (len(self.removed_objects) > 0 or len(self.derived_objects) > 0)

    def insert_derived(self,
                       original: ObjectSnapshot,
                       id: Optional[ObjectID] = None) -> ObjectID:
        """Inserts a derived instance of the snapshot.

        The derived instance will have the provided `id` or a new ID generated
        from the database identity sequence.

        - Precondition: if the object ID is provided, it must not exist in the
          frame.

        The identity of the original snapshot is ignored.
        """

        assert self.is_open, "Trying to modify a closed transaction"

        actual_id = id or self.database.object_id_generator.next()

        derived = original.derive(version=self.version, id=actual_id)

        self.derived_objects[actual_id] = derived
        self.frame.insert(derived)
    
        return actual_id


    def create_object(self, id: Optional[ObjectID] = None,
                      components: Optional[list[Component]] = None) -> ObjectID:
        # TODO: Deprecated method in favour of insert_object(snapshot:id:)
        assert self.is_open, "Trying to modify a closed transaction"

        actual_id = id or self.database.object_id_generator.next()
        object = ObjectSnapshot(id=actual_id,
                                version=self.version,
                                components=components)
        self.derived_objects[actual_id] = object
        self.frame.insert(object)

        return actual_id

    def remove_object(self, id: ObjectID):
        assert self.is_open, "Trying to modify a closed transaction"
        self.frame.remove(id)
        self.removed_objects.append(id)

    def remove_object_cascading(self, id: ObjectID) -> list[ObjectID]:
        """Remove an object from the transaction and all objects that depend on
        the removed objects. Returns a list of removed objects."""
        assert self.is_open, "Trying to modify a closed transaction"
        removed = self.frame.remove_cascading(id)
        self.removed_objects.append(id)
        self.removed_objects += removed
        return removed

    def _derived_object(self, id: ObjectID) -> ObjectSnapshot:
        assert self.is_open, "Trying to close already closed transaction"

        object: ObjectSnapshot

        try:
            object = self.derived_objects[id]
        except KeyError:
            derived = self.frame.derive_object(id)
            self.derived_objects[id] = derived
            object = derived

        return object

    def set_component(self, id: ObjectID, component: Component):
        assert self.is_open, "Trying to close already closed transaction"

        object = self._derived_object(id)
        object.components.set(component)


    def update_object(self, id: ObjectID) -> ObjectSnapshot:
        """
        Get an object snapshot reference for updating.

        Returns a derived object for the transaction frame. Derive the object
        if the requested object is not yet derived.
        """
        return self._derived_object(id)

    @contextmanager
    def update2(self, id: ObjectID):
        obj = self._derived_object(id)
        try:
            yield obj
        finally:
            # Check referential integrity after update
            missing = list(oid for oid in obj.structural_dependencies()
                           if not self.frame.contains(oid))
            if missing:
                raise RuntimeError(f"Unhandled broken structural integrity. ID: {id}, missing: {missing}")



    def close(self):
        """Close the transaction.

        """
        assert self.is_open, "Trying to close already closed transaction"
        self.is_open = False
