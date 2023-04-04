# transaction.py
#
# Created by: Stefan Urbanek
# Date: 2023-03-30
#

from .version import VersionID

from .frame import VersionFrame
from .object import ObjectID, ObjectSnapshot
from .component import Component

from typing import Optional, TypeVar
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .database import Database

C = TypeVar("C", bound=Component)

__all__ = [
    "Transaction",
]

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
        assert self.is_open, "Trying to modify a closed transaction"
        removed = self.frame.remove_cascading(id)
        self.removed_objects.append(id)
        self.removed_objects += removed
        return removed

    def set_component(self, id: ObjectID, component: Component):
        assert self.is_open, "Trying to close already closed transaction"

        object: ObjectSnapshot

        try:
            object = self.derived_objects[id]
        except KeyError:
            derived = self.frame.derive_object(id)
            self.derived_objects[id] = derived
            object = derived

        object.components.set(component)

    def close(self):
        """Close the transaction.

        """
        assert self.is_open, "Trying to close already closed transaction"
        self.is_open = False
