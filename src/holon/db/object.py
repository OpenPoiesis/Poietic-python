# object.py
#
# Created by: Stefan Urbanek
# Date: 2023-03-30
#

from typing import TypeAlias, Optional, TypeVar, Type, Self

from .identity import ID
from .version import VersionID, VersionState

from .component import Component, ComponentSet
from .object_type import ObjectType

__all__ = [
    "ObjectID",
    "SnapshotID",
    "ObjectSnapshot",
    "Dimension",
]

"""Object identity type.

Each design object has an unique ID within the database and might have
multiple snapshots.
"""
ObjectID: TypeAlias = ID

"""Object snapshot identity type.

`SnapshotID` is unique within the database.
"""
SnapshotID: TypeAlias = ID


class Dimension:
    """Object dimension.

    Object dimensions are used to denote system context.

    Potential dimensions might be: user dimension - objects created by the
    user, interpreter dimension - objects created by the interpreter, used by
    the compiler, etc.

    Objects dimensions are defined in the metamodel.

    There should be only one instance of a dimension per metamodel. Dimensions
    can be compared using identity comparison `is`/`is not`.
    """

    """Dimension name. Used for debug purposes."""
    name: str

    def __init__(self, name: str):
        """Create a new dimension with name `name`."""
        self.name = name

DEFAULT_DIMENSION: Dimension = Dimension(name="%default")

C = TypeVar("C", bound=Component)

class ObjectSnapshot:
    """
    Structure that uniquely identifies concrete object snapshot through
    its ID and version. There can be only one snapshot with such identity
    within the database.

    Object has an identity that is unique within a database.
    """
    # TODO: Rename id to _persistent_id
    # TODO: Rename version to _persistent_version
    # TODO: Make all ids read-only, allow write only in unstable state
    # TODO: Mention that we are doing the above to prevent us having two classes.

    # TODO: Make this private and expose public read-only property
    id: ObjectID
    """Object identity that is guaranteed to be unique within the object
    memory."""

    version: VersionID
    """Object version identifier – unique within object identity."""

    state: VersionState
    """Object state. See ``VersionState`` for more information."""

    # TODO: For the time being the type is optional
    # Note: we want to allow change of type.
    type: Optional[ObjectType]

    # FIXME: Do we still need this? (consider removing)
    dimension: Dimension
    """Dimension of the object in a graph."""

    components: ComponentSet


    def __init__(self,
                 id: ObjectID,
                 version: VersionID,
                 type: Optional[ObjectType]=None,
                 components: Optional[list[Component]] = None):
        """
        Create a new object with given identity and version.
        The combination of object identity and version must be unique within the database.
        """
        self.id = id
        self.version = version
        self.snapshot_id = 0
        self.state = VersionState.UNSTABLE
        self.dimension = DEFAULT_DIMENSION
        self.components = ComponentSet(components)
        self.type = type


    def derive(self, version: VersionID, id: Optional[ObjectID] = None) -> Self:
        """
        Derive a new object from existing object and assign it a new version
        identifier.
        
        Precondition: The object must be in a derive-able state. See [`VersionState`] for more
        information.

        :param VersionID version: new version identifier of the derived snapshot.
        :param VersionID id: new object identity of the derived snapshot.
        :return: Derived object snapshot.

        Usually one does not need to provide a new object identity. If not
        provided, the identity of the receiver of this method will be used.

        .. note:
            We are relying on the Python's dynamic object runtime here. This
            portion needs to be re-thinked, if it is meant to be implementable
            in other languages.

            For example, in Swift this would be illegal, unless the instance
            variables of the subclasses would be forced-unwrap optionals that
            can be initialized later.

            Alternative in other languages might be to include a `structural
            component` property, that might be an enum-like.

        """
        assert self.state.can_derive, f"Can not derive an object that is in the state {self.state}"

        new_id = id or self.id

        obj = self.__class__(id = new_id,
                             version = version,
                             components = self.components.as_list() )
        obj.dimension = self.dimension
        obj.state = VersionState.UNSTABLE
        obj.type = self.type
        return obj

    def make_transient(self):
        assert self.state == VersionState.UNSTABLE
        self.state = VersionState.TRANSIENT

    def freeze(self):
        assert self.state == VersionState.TRANSIENT
        self.state = VersionState.FROZEN

    def __getitem__(self, key: Type[C]) -> C:
        return self.components.get(key)

    def structural_dependencies(self) -> list[ObjectID]:
        """Return objects that structurally depend on the receiver.

        For example an edge depends on a node that is an endpoint of the edge.
        """
        return []

