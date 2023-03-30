from typing import TypeAlias, Optional, TypeVar, Type
from .identity import ID
from .version import VersionID, VersionState

from .component import Component, ComponentSet

"""Object identity type."""
ObjectID: TypeAlias = ID
SnapshotID: TypeAlias = ID

class Dimension:
    name: str

    """Graph dimension type."""
    def __init__(self, name: str):
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

    """Object identity that is guaranteed to be unique within the object
    memory."""
    id: ObjectID

    """Object version identifier – unique within object identity."""
    version: VersionID

    """Object state. See ``VersionState`` for more information."""
    state: VersionState

    """Dimension of the object in a graph."""
    dimension: Dimension
    components: ComponentSet


    def __init__(self, id: ObjectID, version: VersionID, components: Optional[list[Component]] = None):
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


    def derive(self, version: VersionID) -> "ObjectSnapshot":
        """
        Derive a new object from existing object and assign it a new version
        identifier.
        
        Precondition: The object must be in a derive-able state. See [`VersionState`] for more
        information.
        """
        assert self.state.can_derive, f"Can not derive an object that is in the state {self.state}"

        obj = ObjectSnapshot(id = self.id,
                             version = version,
                             components = self.components.as_list() )
        obj.dimension = self.dimension
        obj.state = VersionState.UNSTABLE
        return obj

    def make_transient(self):
        assert self.state == VersionState.UNSTABLE
        self.state = VersionState.TRANSIENT

    def freeze(self):
        assert self.state == VersionState.TRANSIENT
        self.state = VersionState.FROZEN

    def __getitem__(self, key: Type[C]) -> C:
        return self.components.get(key)

