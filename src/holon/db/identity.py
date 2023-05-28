# identity.py
#
# Created by: Stefan Urbanek
# Date: 2023-03-30

from typing import TypeAlias, Any, Optional

__all__ = [
    "ID",
    "ObjectID",
    "SnapshotID",
    "VersionID",
    "SequentialIDGenerator",
]

ID: TypeAlias = int
"""Identity type. Object, version and snapshot identites are of this type."""

ObjectID: TypeAlias = ID
"""Object identity type.

Each design object has an unique ID within the database and might have
multiple snapshots.
"""

SnapshotID: TypeAlias = ID
"""Object snapshot identity type.

`SnapshotID` is unique within the database.
"""

VersionID: TypeAlias = ID


# TODO: Rename to IdentitySequence
class SequentialIDGenerator:
    """Generator of sequential identity.

    This class is used to assign an identity to objects, snapshots and
    versions.
    """

    _current: ID

    def __init__(self, state: Optional[str] = None):
        """Create a new sequential ID generator.

        `state` is a string value representing a state of the genertor that has ben
        retrieved using the `state` property. It is used for persistence of the
        ID sequence.
        """

        start: int

        if state is not None:
            try:
                start = int(state)
            except ValueError:
                raise Exception(f"Invalid sequence state provided: {state}")
        else:
            start = 1

        self._current = start


    @property
    def state(self) -> str:
        """String representation of the ID generator state.

        .. important::

            The state is opaque, nothing should be assumed about the string
            contents. The state should be stored as-is.
        """
        return str(self._current)

    def next(self) -> int:
        """Get a next ID.

        If the ID has been already marked as used, then it returns the next
        unused one.
        """
        id = self._current
        self._current += 1
        return id

    def mark_used(self, id: ID):
        """Marks an ID as used, so it will not be generated in the future."""
        self._current = id + 1



