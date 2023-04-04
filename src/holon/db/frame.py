# frame.py
#
# Created by: Stefan Urbanek
# Date: 2023-03-30
#

from typing import Optional, Iterator, TYPE_CHECKING
from .version import VersionID, VersionState
from .object import ObjectID, ObjectSnapshot

if TYPE_CHECKING:
    from ..graph import UnboundGraph

__all__ = [
    "VersionFrame",
    "SnapshotStorage",
]

class VersionFrame:
    """
    Version frame represents a version snapshot of the design – snapshot of
    objects and their properties.
    """

    state: VersionState
    """Mutability state of the plane."""
    
    version: VersionID
    """
    Version associated with this plane. All objects created or modified
    in this plane share the same version. Version is unique within the
    object memory.
    """
    
    # check for mutability
    objects: dict[ObjectID, ObjectSnapshot]
    """
    Versions of objects in the plane.
    
    Objects not in the map do not exist in the version plane, but might
    exist in the object memory.

    """
   
    
    def __init__(self, version: VersionID,
                 objects: Optional[dict[ObjectID, ObjectSnapshot]] = None):
        """Create a new version frame for a version `version`.

        :param VersionID version: Version ID of the new frame. It must be unique within the database.
        :param dict[ObjectID, ObjectSnapshot] objetcs: optional dictionary of objects that will be associated with this frame.
        """
        self.version = version
        self.state = VersionState.UNSTABLE
        if objects is not None:
            self.objects = dict(objects)
        else:
            self.objects = dict()
    
    def contains(self, id: ObjectID) -> bool:
        """:return: `True` if the frame constains objects with object identity `id`."""
        return id in self.objects


    def structural_dependants(self, id: ObjectID) -> Iterator[ObjectID]:
        """
        Find all objects that depend on the object with `id`. For example,
        edges depend on their endpoints.

        For example, when removing a node, find all edges that point to/from
        the node and remove them as well, when cascading removal is desired.

        :return: Objects that structurally depend on the object with `id`.
        """
        for object in self.objects.values():
            if id in object.structural_dependencies():
                yield object.id

    def has_referential_integrity(self) -> bool:
        """Returns `true` if the frame maintains referential integrity of
        structural objects."""

        return next(self.referential_integrity_violators()) == None


    def referential_integrity_violators(self) -> Iterator[ObjectID]:
        """Iterates through objects that structurally vioalte referential
        integrity of the frame.

        For example, if the frame is representing a graph and endpoints of the
        edges of the graph refer to objects that do not exist in the frame."""

        for (oid, object) in self.objects.items():
            if any(id not in self.objects
                   for id in object.structural_dependencies()):
                yield oid
                    

    def derive_object(self, id: ObjectID) -> ObjectSnapshot:
        """Derive an object with identity `id` so it can be mutated within this
        frame.

        :return: Derived object snapshot.

        Preconditions:

        * frame must be mutable
        * frame must contain the object
        * object must not be already derived

        """
        assert self.state.is_mutable
        assert id in self.objects

        original = self.objects[id]
        assert original.version != self.version, \
                     "Trying to derive already derived object"

        derived = original.derive(version=self.version)
        self.objects[id] = derived
        return derived
    
    def remove_cascading(self, id: ObjectID) -> list[ObjectID]:
        """Remove object from the frame including all it dependants."""
        assert self.state.is_mutable
        assert id in self.objects, \
                     f"Trying to remove an object ({id}) that is not in the frame {self.version}"

        # Preliminary implementation, works for edge-like objects. Good for
        # now.
        removed: list[ObjectID] = list()

        for (dep_id, dep) in self.objects.items():
            if id not in dep.structural_dependencies():
                continue
            del self.objects[dep_id]
            removed.append(dep_id)

        del self.objects[id]

        return removed

    def remove(self, id: ObjectID):
        """Remove an object with given identity from the frame."""
        # TODO: Rename to remove_unsafe and recommend remove_cascading()
        assert self.state.is_mutable
        assert id in self.objects, \
                     f"Trying to remove an object ({id}) that is not in the frame {self.version}"
        del self.objects[id]
    
    def insert(self, snapshot: ObjectSnapshot):
        """Insert a snapshot to the frame.

        Preconditions:

        * Frame must be mutable.
        * Frame must not contain an object with the same identity as the
          snapshot.
        * Snapshot version must be the same as the frame version.

        """
        assert (self.state.is_mutable)
        assert (self.version == snapshot.version)
        assert (snapshot.id not in self.objects)
        
        self.objects[snapshot.id] = snapshot
    
    def object(self, id: ObjectID) -> Optional[ObjectSnapshot]:
        """Returns an object with given identity if the frame contains it.
        Otherwise returns `None`."""

        # TODO: Make mutable/immutable version of this method.
        return self.objects.get(id)
    
    def __str__(self) -> str:
        return f"VersionFrame({self.version}, state: {self.state}"
    
    def derive(self, version: VersionID) -> "VersionFrame":
        """Derive new version of the frame."""
        assert (self.state.can_derive)
        return VersionFrame(version=version, objects=self.objects)
    
    def make_transient(self):
        """Make the frame transient.

        All objects in the frame that are unstable will be made transient.
        """
        for obj in self.objects.values():
            if obj.version == self.version and obj.state == VersionState.UNSTABLE:
                obj.make_transient()

        self.state = VersionState.TRANSIENT
    
    def freeze(self):
        """Make the frame frozen.

        All objects in the frame that are transient will be frozen.
        """
        for obj in self.objects.values():
            if obj.version == self.version and obj.state != VersionState.FROZEN:
                obj.freeze()
        self.state = VersionState.FROZEN


    # Graph
    # -------------------------------------------------------------------
    @property
    def unbound_graph(self) -> "UnboundGraph":
        """Get unbound graph view of the frame."""
        return UnboundGraph(self)


class SnapshotStorage:
    """Storage of version frames."""

    frames: dict[VersionID, VersionFrame]
    
    def __init__(self):
        """Create a new frame storage."""
        self.frames = dict()
    
    def frame(self, version: VersionID) -> Optional[VersionFrame]:
        """Get a frame by version.

        :param VersionID version: Version of the frame to be fetched.
        :return: A frame if it exists in the storage.
        """
        return self.frames[version]

    def versions(self, id: ObjectID) -> list[VersionID]:
        """ Get list of all versions of a given object.

        :param ObjectID id: Identity of the object to be queired.
        :return: a list of version IDs.

        """
        versions: list[VersionID] = []

        for frame in self.frames.values():
            if frame.contains(id):
                versions.append(frame.version)

        return versions

    
    def create_frame(self, version: VersionID) -> VersionFrame:
        """Create a new empty frame in the storage and assign it a new version
        ID.

        Precondition: storage must not contain a frame with given version.

        :param VersionID version: Version identity of the new frame.
        :return: Newly created version frame.


        .. note::
            Usually you do not want to call this method, as creating an empty
            frame is a very unique operation. This method is used by the
            database to create the very first frame.

        """
        assert version not in self.frames

        frame = VersionFrame(version=version)
        self.frames[version] = frame

        return frame

    
    def derive_frame(self,
                     version: VersionID,
                     originalVersion: VersionID) -> VersionFrame:
        """Derive a frame from an existing frame.

        :param VersionID version: Version of the new frame.
        :param VersionID originalVersion: Version of the frame to be used as an original.

        Precondition: Storage must not contain `version`.

        """
        assert version not in self.frames

        original = self.frames[originalVersion]

        assert original is not None, \
                f"Unknown original frame {originalVersion}"

        derived = original.derive(version=version)
        self.frames[version] = derived
        
        return derived
    
    def remove_frame(self, version: VersionID):
        """Remove a frame `version` from the storage."""

        assert version in self.frames
        del self.frames[version]
