# object.py
#
# Created by: Stefan Urbanek
# Date: 2023-03-30
#

from typing import Optional, TypeVar, Type, Self, cast, TYPE_CHECKING

from ..persistence.store import ExtendedPersistentRecord, PersistentRecord
from ..metamodel import MetamodelBase

from .identity import ObjectID, SnapshotID
from .version import VersionState
from .component import Component, ComponentSet
from .object_type import ObjectType

if TYPE_CHECKING:
    from ..metamodel import MetamodelBase

__all__ = [
    "ObjectSnapshot",
]


C = TypeVar("C", bound=Component)

class ObjectSnapshot:
    """
    Structure that uniquely identifies concrete object snapshot through
    its ID and version. There can be only one snapshot with such identity
    within the database.

    Object has an identity that is unique within a database.
    """
    structural_type_name: str = "object"
    # TODO: Rename id to _persistent_id
    # TODO: Rename version to _persistent_version
    # TODO: Make all ids read-only, allow write only in unstable state
    # TODO: Mention that we are doing the above to prevent us having two classes.

    # TODO: Make this private and expose public read-only property
    id: ObjectID
    """Persistent object identity that is guaranteed to be unique within an
    object frame."""

    snapshot_id: SnapshotID
    """Unique identifier of the object snapshot within the database."""

    state: VersionState
    """Object state. See ``VersionState`` for more information."""

    # TODO: For the time being the type is optional
    # Note: we want to allow change of type.
    type: Optional[ObjectType]

    components: ComponentSet


    def __init__(self,
                 id: ObjectID,
                 snapshot_id: SnapshotID,
                 type: Optional[ObjectType]=None,
                 components: Optional[list[Component]] = None):
        """
        Create a new object with given identity and version.
        The combination of object identity and version must be unique within the database.
        """
        self.id = id
        self.snapshot_id = snapshot_id
        self.state = VersionState.UNSTABLE
        self.components = ComponentSet(components)
        self.type = type


    @classmethod
    def from_record(cls,
                    metamodel: Type["MetamodelBase"],
                    record: ExtendedPersistentRecord) -> "ObjectSnapshot":
        """
        Create an object from an extended persistent record.

        The persistent record is expected to contain the following keys:

        - `object_id` – will become ID of the snapshot
        - `snapshot_id`
        - `type` – object type name that must exist in the metamodel

       
        Subclasses overriding this method must call `add_record_components()`
        after they are done finalizing the initialization.
        """

        # TODO: Handle errors
        id = cast(int, record["object_id"])
        snapshot_id = cast(int, record["snapshot_id"])
        type_name = cast(str, record["type"])
        
        object_type = metamodel.type_by_name(type_name)

        snapshot = cls(id=id,
                       snapshot_id=snapshot_id,
                       type=object_type,
                       )

        snapshot.add_record_components(metamodel, record.components)

        return snapshot


    def add_record_components(self,
                              metamodel: Type["MetamodelBase"],
                              records: dict[str, PersistentRecord]):
        """
        Add components from persistent records.


        The keys of the dictionary are component names that must exist in the
        metamodel.

        If sublcasses override `from_record()` then they must call this method.

        """
        
        for name, record in records.items():
            cls = metamodel.persistable_component(name)
            component = cls.from_record(record)
            self.components.set(component)


    def persistent_record(self) -> ExtendedPersistentRecord:
        """Create a persistent record that represents the snapshot.

        The keys of the records:

        - `object_id`
        - `snapshot_id`
        - `type` – object type name
        - `structural_type` – structural type of the object, either ``node`` or
          ``edge`` at the moment.

        """
        record = ExtendedPersistentRecord()

        record["object_id"] = self.id
        record["snapshot_id"] = self.snapshot_id
        if self.type is not None:
            record["type"] = self.type.name
        else:
            record["type"] = "object"

        # Note: Writing structural type is redundant here, because we can
        # derive it from the metamodel. It is written here only for the
        # convenience of the model readers if they do not have the
        # metamodel available to them.

        record["structural_type"] = self.structural_type_name

        for name, component in self.components.persistable_components.items():
            comp_record = component.persistent_record()
            record.set_component(name, comp_record)

        return record


    def derive(self,
               snapshot_id: SnapshotID,
               id: Optional[ObjectID] = None) -> Self:
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
                             snapshot_id = snapshot_id,
                             components = self.components.as_list() )
        obj.state = VersionState.UNSTABLE
        obj.type = self.type
        return obj


    def make_transient(self):
        assert self.state == VersionState.UNSTABLE
        self.state = VersionState.TRANSIENT


    def freeze(self):
        # We can freeze an object in any state. Freezing already frozen object
        # does nothing.
        self.state = VersionState.FROZEN


    def __getitem__(self, key: Type[C]) -> C:
        return self.components.get(key)

    def __setitem__(self, key: Type[C], value: C):
        # TODO: This is weird, we do not need key here
        self.components.set(value)

    def structural_dependencies(self) -> list[ObjectID]:
        """Return objects that structurally depend on the receiver.

        For example an edge depends on a node that is an endpoint of the edge.
        """
        return []

