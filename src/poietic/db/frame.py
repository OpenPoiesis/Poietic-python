# frame.py
#
# Created by: Stefan Urbanek
# Date: 2023-03-30
#

# TODO: IMPORTANT: .object(id) should raise IdentityError

from typing import Optional, Iterator, TYPE_CHECKING, Protocol

from ..errors import IDError

from .version import VersionState
from .object import ObjectSnapshot
from .identity import ObjectID, VersionID


__all__ = [
    "FrameBase",
    "StableFrame",
]


class FrameBase(Protocol):
    @property
    def snapshots(self) -> Iterator[ObjectSnapshot]:
        ...

    def contains(self, id: ObjectID) -> bool:
        ...

    def object(self, id: ObjectID) -> ObjectSnapshot:
        ...

    def structural_dependants(self, id: ObjectID) -> Iterator[ObjectID]:
        """
        Find all objects that depend on the object with `id`. For example,
        edges depend on their endpoints.

        For example, when removing a node, find all edges that point to/from
        the node and remove them as well, when cascading removal is desired.

        :return: Objects that structurally depend on the object with `id`.
        """
        for snapshot in self.snapshots:
            if id in snapshot.structural_dependencies():
                yield snapshot.id

    def has_referential_integrity(self) -> bool:
        """Returns `true` if the frame maintains referential integrity of
        structural objects."""

        return next(self.referential_integrity_violators()) == None


    def referential_integrity_violators(self) -> Iterator[ObjectID]:
        """Iterates through objects that structurally vioalte referential
        integrity of the frame.

        For example, if the frame is representing a graph and endpoints of the
        edges of the graph refer to objects that do not exist in the frame."""

        for snapshot in self.snapshots:
            for id in snapshot.structural_dependencies():
                if not self.contains(id):
                    yield snapshot.id
                    break
    

class StableFrame(FrameBase):
    """
    Version frame represents a version snapshot of the design – snapshot of
    objects and their properties.
    """

    version: VersionID
    """
    Version associated with this plane. All objects created or modified
    in this plane share the same version. Version is unique within the
    object memory.
    """
    
    # check for mutability
    _snapshots: dict[ObjectID, ObjectSnapshot]
    
    def __init__(self, version: VersionID,
                 objects: Optional[Iterator[ObjectSnapshot]] = None):
        """Create a new version frame for a version `version`.

        :param VersionID version: Version ID of the new frame. It must be unique within the database.
        :param dict[ObjectID, ObjectSnapshot] objetcs: optional dictionary of objects that will be associated with this frame.
        """
        self.version = version
        self.state = VersionState.UNSTABLE
        self._snapshots = dict()
        self._snapshot_ids = set()

        if objects is not None:
            for obj in objects:
                if obj.state.is_mutable:
                    raise RuntimeError("Trying to create a stable frame with a mutable object snapshot.")
                self._snapshots[obj.id] = obj
    
    @property
    def snapshots(self) -> Iterator[ObjectSnapshot]:
        """Get a sequence of all snapshots within the frame."""
        return iter(self._snapshots.values())

    
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
            return self._snapshots[id]
        except KeyError:
            raise IDError(id)
    
    def __str__(self) -> str:
        return f"VersionFrame({self.version}, state: {self.state}"

