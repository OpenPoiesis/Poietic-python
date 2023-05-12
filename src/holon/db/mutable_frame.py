# transaction.py
#
# Created by: Stefan Urbanek
# Date: 2023-03-30
#

from typing import Optional, TypeVar, Iterator, Iterable, Tuple
from typing import TYPE_CHECKING
from collections import namedtuple

from .version import VersionID, VersionState
from .object import ObjectID, ObjectSnapshot, SnapshotID
from .object_type import ObjectType
from .frame import FrameBase
from .component import Component
from ..graph import MutableGraph, Node, Edge
from ..errors import IDError

if TYPE_CHECKING:
    from .database import ObjectMemory
    from ..graph import Graph, Node, Edge


C = TypeVar("C", bound=Component)

__all__ = [
    "MutableFrame",
    "MutableUnboundGraph",
]


# TODO: Rename to SnapshotOwnershipReference
FrameSnapshotReference = namedtuple('FrameSnapshotReference', ['snapshot', 'owned'])
"""Annotated reference to a snapshot object from a frame. The `owned` property
is a flag that denotes whether the version frame owns the snapshot, that is,
whether changes can be made to the snapshot without need to derive it.

Changes to an unowned snapshot require that the snapshot is derived first.
"""


class MutableFrame(FrameBase):
    """
    A version frame that can be mutated. Mutable frame is bound to its owning
    memory.

    Frame that allows objects to be inserted, removed and modified. When
    objects are created or modified a new version snapshot is created. Version
    snapshot identity is provided by the owning memory.
    """

    memory: "ObjectMemory"
    """Owning object memory. The reference is used to provide identities for
    new object version snapshot on object insertion or mutation."""

    
    version: VersionID
    """Unique identifier of the frame within a memory."""

    state: VersionState
    """Mutability state of the frame. Once the frame has been accepted to the 
    memory, it can no longer be mutated."""

    _snapshot_ids: set[SnapshotID]
    _snapshots: dict[ObjectID, FrameSnapshotReference]

    # TODO: Change this to be an observable instead of storing it here.
    _removed_objects: list[ObjectID]
    # TODO: This is redundant, we have the information in the
    # FrameSnapshotReference. Remove this.
    _derived_objects: dict[ObjectID, ObjectSnapshot]
    
    def __init__(self,
                 memory: "ObjectMemory",
                 version: VersionID,
                 objects: Optional[Iterator[ObjectSnapshot]] = None):
        """Create a new version frame for a version `version`.

        :param VersionID version: Version ID of the new frame. It must be unique within the database.
        :param dict[ObjectID, ObjectSnapshot] objetcs: optional dictionary of objects that will be associated with this frame.
        """
        self.version = version
        self.state = VersionState.UNSTABLE
        self.memory = memory
        self._snapshots = dict()
        self._snapshot_ids = set()
        self._removed_objects = list()
        self._derived_objects = dict()

        if objects is not None:
            for obj in objects:
                ref = FrameSnapshotReference(snapshot=obj, owned=False)
                self._snapshots[obj.id] = ref
                self._snapshot_ids.add(obj.snapshot_id)

    @property
    def has_changes(self) -> bool:
        return (len(self._removed_objects) > 0 or len(self._derived_objects) > 0)

    @property
    def is_open(self) -> bool:
        """True if the frame was accepted by the memory and is no longer
        mutable."""
        return self.state.is_mutable

    @property
    def derived_objects(self) -> Iterator[ObjectSnapshot]:
        return iter(self._derived_objects.values())


    @property
    def snapshots(self) -> Iterator[ObjectSnapshot]:
        """Get a sequence of all snapshots within the frame."""
        for (snapshot, _) in self._snapshots.values():
            yield snapshot

    def contains(self, id: ObjectID) -> bool:
        """:return: `True` if the frame constains objects with object identity `id`."""
        return id in self._snapshots

    def object(self, id: ObjectID) -> ObjectSnapshot:
        """
        Returns an object with given identity if the frame contains it.
        
        :raises IDError: If there is no object with given ID.
        """

        # TODO: Make mutable/immutable version of this method.
        try:
            ref = self._snapshots[id]
            return ref.snapshot
        except KeyError:
            raise IDError(id)

    def insert(self, snapshot: ObjectSnapshot, owned: bool = False):
        """Insert a snapshot to the frame.

        Inserted snapshot will not be owned by the frame unless derived.

        Preconditions:

        * Frame must be mutable.
        * Frame must not contain an object with the same identity as the
          snapshot.
        * Frame must not contain an object with the same snapshot version.

        """
        assert (self.state.is_mutable), \
                f"Trying to modify accepted frame (id: {self.version})"
        assert (snapshot.id not in self._snapshots)
        assert (snapshot.snapshot_id not in self._snapshot_ids)
        # TODO: Check that we do not own a snapshot with given snapshot ID
        
        ref = FrameSnapshotReference(snapshot=snapshot, owned=owned)

        self._snapshots[snapshot.id] = ref
        self._snapshot_ids.add(snapshot.snapshot_id)


    # TODO: Reconsider existence of this method
    def create_object(self, object_type: Optional[ObjectType]=None,
                      components: Optional[list[Component]]=None) -> ObjectID:
        """Create an unspecific object.


        .. note::
            This method is a leftover from previous design. It is not
            advised to use it at the moment. Create an object externally and insert
            it using the `insert(method)`.
        """
        actual_id = self.memory.object_id_generator.next()
        snapshot_id = self.memory.snapshot_id_generator.next()

        new_object = ObjectSnapshot(id=actual_id,
                                snapshot_id=snapshot_id)
        new_object = Node(id=actual_id,
                      snapshot_id=snapshot_id,
                      type=object_type,
                      components=components)
        self.insert(new_object, owned=True)
        self._derived_objects[actual_id] = new_object

        return actual_id


    def insert_derived(self,
                       original: ObjectSnapshot,
                       id: Optional[ObjectID] = None) -> ObjectID:
        """Inserts a derived instance of the snapshot.

        The derived instance will have the provided `id` or a new ID generated
        from the database identity sequence.

        New snapshot ID will be generated to the inserted derived object.

        - Precondition: if the object ID is provided, it must not exist in the
          frame.

        The identity of the original snapshot is ignored.
        """

        assert (self.state.is_mutable), \
                f"Trying to modify accepted frame (id: {self.version})"

        actual_id = id or self.memory.object_id_generator.next()
        snapshot_id = self.memory.snapshot_id_generator.next()

        derived = original.derive(snapshot_id=snapshot_id, id=actual_id)

        self.insert(derived)
        self._derived_objects[actual_id] = derived
    
        return actual_id


    def _derive_object(self, id: ObjectID) -> ObjectSnapshot:
        """Derive an object with identity `id` so it can be mutated within this
        frame.

        :return: Derived object snapshot.

        Preconditions:

        * frame must be mutable
        * frame must contain the object
        * object must not be already derived

        """
        # Note: This is called only from mutable_object(...), separated to other
        # method for transparency.

        assert (self.state.is_mutable), \
                f"Trying to modify accepted frame (id: {self.version})"
        assert id in self._snapshots

        # Note: I did it this way because the type inference for tuple was not
        # working and I wanted it to be have correctly.
        tup: Tuple[ObjectSnapshot, bool] = self._snapshots[id]
        original: ObjectSnapshot = tup[0]
        owned: bool = tup[1]

        assert not owned, \
                 "Trying to derive already derived object"

        snapshot_id = self.memory.snapshot_id_generator.next()

        derived = original.derive(snapshot_id=snapshot_id)
        self._snapshots[id] = FrameSnapshotReference(snapshot=derived,
                                                  owned=True)
        self._snapshot_ids.add(id)
        return derived
    

    # TODO: Rename to _mutable_object(...) or public mutate_object()
    def mutable_object(self, id: ObjectID) -> ObjectSnapshot:
        """
        Get an object snapshot reference for updating.

        Returns a derived object for the transaction frame. Derive the object
        if the requested object is not yet derived.
        """
        assert (self.state.is_mutable), \
                f"Trying to modify accepted frame (id: {self.version})"
        # TODO: Now we have this information in the Frame as "owned" flag

        object: ObjectSnapshot

        try:
            object = self._derived_objects[id]
        except KeyError:
            derived = self._derive_object(id)
            self._derived_objects[id] = derived
            object = derived

        return object


    def set_component(self, id: ObjectID, component: Component):
        assert (self.state.is_mutable), \
                f"Trying to modify accepted frame (id: {self.version})"

        object = self.mutable_object(id)
        object.components.set(component)

    
    def remove_cascading(self, id: ObjectID) -> list[ObjectID]:
        """Remove object from the frame including all it dependants."""
        assert (self.state.is_mutable), \
                f"Trying to modify accepted frame (id: {self.version})"
        assert id in self._snapshots, \
                     f"Trying to remove an object ({id}) that is not in the frame {self.version}"

        # Preliminary implementation, works for edge-like objects. Good for
        # now.
        removed: list[ObjectID] = list()

        for (dep_id, ref) in self._snapshots.items():
            dep = ref.snapshot
            if id not in dep.structural_dependencies():
                continue
            self._remove(dep_id)
            removed.append(dep_id)

        self._remove(id)

        return removed


    def _remove(self, id: ObjectID):
        """Remove an object with given identity from the frame."""
        # TODO: Rename to remove_unsafe and recommend remove_cascading()
        assert (self.state.is_mutable), \
                f"Trying to modify accepted frame (id: {self.version})"
        assert id in self._snapshots, \
                     f"Trying to remove an object ({id}) that is not in the frame {self.version}"
        snapshot = self._snapshots[id].snapshot
        del self._snapshots[id]

        self._snapshot_ids.remove(snapshot.snapshot_id)
        self._removed_objects.append(id)
    

    # TODO: This is not used any more.

    # def make_transient(self):
    #     """Make the frame transient.
    #
    #     All objects in the frame that are unstable will be made transient.
    #     """
    #     for ref in self._snapshots.values():
    #         obj = ref.snapshot
    #         if obj.version == self.version and obj.state == VersionState.UNSTABLE:
    #             obj.make_transient()
    #
    #     self.state = VersionState.TRANSIENT
    

    def freeze(self):
        """Make the frame frozen.

        All objects in the frame that are transient will be frozen. The frame
        will no longer be mutable - no more changes can be made with the frame.

        This is used by the memory when accepting the frame and changing it
        into a stable, immutable frame.
        """
        assert (self.state.is_mutable), \
                f"Trying to modify accepted frame (id: {self.version})"

        # Freeze derived objects
        for ref in self._snapshots.values():
            (obj, owned) = ref
            if owned and obj.state != VersionState.FROZEN:
                obj.freeze()

        self.state = VersionState.FROZEN

    
    @property
    def graph(self) -> "Graph":
        """Get a mutable graph associated with this transaction.

        Any changes with the graph will be registered with the transaction.
        """
        return self.mutable_graph

    @property
    def mutable_graph(self) -> "MutableGraph":
        """Get a mutable graph associated with this transaction.

        Any changes with the graph will be registered with the transaction.
        """
        return MutableUnboundGraph(self)


class MutableUnboundGraph(MutableGraph):
    """Mutable unbound graph is a view on top of a version frame where changes
    to the graph are applied within associated transaction.

    Any structural changes of the graph (adding node/edge, removing node/edge)
    result in a transaction operation in a way that the structural integrity
    of the frame is maintained.
    """

    frame: "MutableFrame"

    def __init__(self, frame: "MutableFrame"):
        """Create a new unbound-graph view on top of a version frame `frame`
        within a transaction `transaction.
        """
        self.frame = frame

    def nodes(self) -> Iterable[Node]:
        return (obj for obj in self.frame.snapshots
                if isinstance(obj, Node))

    def edges(self) -> Iterable[Edge]:
        return (obj for obj in self.frame.snapshots
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
    def insert_node(self, node: Node):
        self.frame.insert_derived(node)

    def insert_edge(self, edge: Edge):
        assert self.frame.contains(edge.origin), \
                f"The graph does not contain origin node {edge.origin}"
        assert self.frame.contains(edge.target), \
                f"The graph does not contain target node {edge.target}"
        self.frame.insert_derived(edge)

    # TODO: Add tests
    def create_node(self,
               object_type: ObjectType,
               components: Optional[list[Component]] = None) -> ObjectID:
        # TODO: Prefer this convenience method
        assert object_type.structural_type is Node

        object = Node(id=0,          # Will be assigned in insert_derived()
                      snapshot_id=0, # Will be assigned in insert_derived()
                      type=object_type,
                      components=components)
        object.state = VersionState.TRANSIENT
        # Insert missing but required components with default initialization
        #
        for comp_type in object_type.component_types:
            if not object.components.has(comp_type):
                object.components.set(comp_type())

        # TODO: We are unnecessarily creating two copies of the object here
        return self.frame.insert_derived(object)


    # TODO: Add tests
    def create_edge(self,
                object_type: ObjectType,
                origin: ObjectID,
                target: ObjectID,
                components: Optional[list[Component]] = None) -> ObjectID:
        # TODO: Prefer this convenience method
        assert object_type.structural_type is Edge
        assert self.frame.contains(origin)
        assert self.frame.contains(target)

        object = Edge(id=0,           # Will be assigned in insert_derived()
                      snapshot_id=0,  # Will be assigned in insert_derived()
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

        # TODO: We are unnecessarily creating two copies of the object here
        return self.frame.insert_derived(object)


    def remove_node(self, node_id: ObjectID) -> list[ObjectID]:
        return self.frame.remove_cascading(node_id)

    def remove_edge(self, edge_id: ObjectID):
        self.frame.remove_cascading(edge_id)

