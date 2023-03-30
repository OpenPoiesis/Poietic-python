# identity.py
#
# Created by: Stefan Urbanek
# Date: 2023-03-30

from typing import TypeAlias

__all__ = [
    "ID",
    "SequentialIDGenerator",
]

ID: TypeAlias = int
"""Identity type. Object, version and snapshot identites are of this type."""

class SequentialIDGenerator:
    """Generator of sequential identity.

    This class is used to assign an identity to objects, snapshots and
    versions.
    """

    _current: ID
    _used: set[ID]

    def __init__(self):
        """Create a new sequential ID generator."""
        self._current = 0
        self._used = set()

    def next(self) -> int:
        """Get a next ID.

        If the ID has been already marked as used, then it returns the next
        unused one.
        """
        while self._current in self._used:
            self._used.remove(self._current)
            self._current += 1
        id = self._current
        self._current += 1
        return id

    def mark_used(self, id: ID):
        """Marks an ID as used, so it will not be generated in the future."""
        self._used.add(id)



