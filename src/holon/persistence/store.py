# writer.py
#
# Writer
#
# Created by: Stefan Urbanek
# Date: 2023-04-26


import json
from typing import Protocol, Iterable, Any, Optional, Iterator
from dataclasses import dataclass, field
from collections.abc import MutableMapping

from ..db.identity import ObjectID
from ..value import Point

__all__ = [
    "PersistentValue",
    "PersistentRecord",
    "ExtendedPersistentRecord",
    "PersistentStore",

    "JSONStore",
]


PersistentValue = bool | int | float | str | Point | ObjectID | list[ObjectID]
"""
Type for values that can be stored in the persistent store.

It consistes of types that conform to the `ValueProtocol` and of an object ID
or a list of object IDs.

.. note::

    Stores that do not have the ability to have a vector, list or array values
    can store the list of IDs as a comma separated values. String
    representation of ObjectID is guaranteed to be alpha-numeric.

"""


@dataclass
class PersistentRecord(MutableMapping):
    """Object for storing key-value pairs that describe an object. 


    .. seealso::

        `ExtendedPersistentRecord`

    .. note::

        We are wrapping a dictionary so we can have more customization and
        control.
    """
    _data: dict[str, PersistentValue] = field(default_factory=dict)

    def __getitem__(self, key: str) -> PersistentValue:
        return self._data[key]

    def __setitem__(self, key: str, value: PersistentValue):
        self._data[key] = value

    def __delitem__(self, key: str):
        del self._data[key]

    def __iter__(self) -> Iterator:
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)

    def as_dict(self) -> dict[str, Any]:
        """Get a JSON-compatible dictionary representation of the record.

        .. note::

            At this moment, no value conversion is performed. Just the
            underlying dictionary is returned as-is.
        """
        return dict(self._data)


"""Type representing external records for interchange."""


@dataclass
class ExtendedPersistentRecord(PersistentRecord):
    """
    Record for persistent object snapshot.

    The record contains keys and values of the object snapshot as well as
    associated components.
    """

    components: dict[str, PersistentRecord] = field(default_factory=dict)
    """A dictionary of persistent records representing components."""

    def __init__(self, primary: Optional[dict[str, PersistentValue]] = None,
                 components: Optional[dict[str, PersistentRecord]] = None):

        if primary is not None:
            super().__init__(primary)
        else:
            super().__init__()

        if components is not None:
            self.components = components
        else:
            self.components = dict()

    def component_names(self) -> list[str]:
        """List of component names associated with the extended record."""
        return list(self.components.keys())


    def component(self, name: str) -> PersistentRecord:
        """Get a persistent record for a component with given name."""
        return self.components[name]

    def set_component(self, name: str, record: PersistentRecord):
        """Set a persistent record for a component with given name."""
        self.components[name] = record


class PersistentStore(Protocol):
    # TODO: Rename to relational persistent store
    """
    What needs to be stored:

    - bundle information
        - version of the format
    - objects: list
        - snapshot ID: string, optional for single-frame
        - object ID: string, required
        - object type: string, required
        - attributes: dictionary of string:scalar, optional
        - structural, required
    - frames: list
        - version ID

    
    - Rules:
        - if "frames" is not present, then all objects are from a single frame
            - snapshot ID does not have to be present, will be assigned
    - Validation:
        - snapshot ID is unique
        - object ID is unique in a frame
    """
    def write_info_record(self, info: PersistentRecord):
        """Write a record that contains information about the stored design.

        The info record is expected to contain the following keys:

        - `version` – version of the stored format, a system value
        """
        ...

    def read_info_record(self) -> PersistentRecord:
        ...

    def write_extended_records(self, type_name: str, records: Iterable[ExtendedPersistentRecord]):
        ...

    def read_extended_records(self, type_name: str) -> Iterable[ExtendedPersistentRecord]:
        ...

    def record_types(self) -> list[str]:
        """Return list of record type names.

        Naming convenience:

        - ``frames`` – frame object records
        - ``snapshots`` - object snapshot records
        - ``*_component`` - components

        """
        ...

    def close(self):
        pass


class JSONStore(PersistentStore):
    """
    Persistent store that stores the object memory as a single JSON file.


    .. note::

        There is no significiant reason why the reading and writing is coupled
        under the hood of the single class at this moment. It is just to keep
        the code together and maintain it together.
    """
    path: str
    """Path to a file where the memory will be stored."""

    is_writing: bool

    _result: dict[str, Any]
    """Aggregate result to be written. This simple store holds it all in memory
    before writing it out."""

    def __init__(self, path: str, writing: bool):
        """Create a new store at given path."""
        self.path = path
        self._result = dict()
        self.is_writing = writing

        if not writing:
            with open(path) as f:
                self._result = json.load(f)


    def write_info_record(self, info: PersistentRecord):
        assert self.is_writing
        self._result["info"] = info.as_dict()


    def _named_collection(self, name: str) -> list[dict[str, Any]]:
        cont_name: str
        # NOTE: The match below is a remnant from when `name` was `type_name`
        # TODO: Good for now. This emulates existence of a DB schema.
        match name:
            case "snapshots": cont_name = "snapshots"
            case "frames": cont_name = "frames"
            case _: raise Exception(f"Unknown container type: {name}")

        cont: list[dict[str, Any]]

        try:
            cont = self._result[cont_name]
        except KeyError:
            cont = list()
            self._result[cont_name] = cont

        return cont

    def write_extended_records(self, type_name: str,
                              records: list[ExtendedPersistentRecord]):
        assert self.is_writing
        """Replace all the records in the container for given type."""
        collection = self._named_collection(type_name)

        for record in records:
            json_record = dict(record.as_dict())
            components: dict[str, Any] = dict()

            for key in record.component_names():
                components[key] = record.component(key).as_dict()

            if components:
                json_record["components"] = components

            collection.append(json_record)


    def read_info_record(self) -> PersistentRecord:
        assert not self.is_writing

        return PersistentRecord(self._result["info"])


    def read_extended_records(self, type_name: str) -> Iterable[ExtendedPersistentRecord]:
        assert not self.is_writing

        collection = self._named_collection(type_name)

        json_components: dict[str, Any] = dict()
        components: dict[str, PersistentRecord] = dict()

        for json_record in collection:
            if "components" in json_record:
                json_components = json_record["components"]
                del json_record["components"]
            else:
                json_components = dict()

            for (key, value) in json_components.items():
                record = PersistentRecord(value)
                components[key] = record

            record = ExtendedPersistentRecord(json_record, components)

            yield record


    def record_types(self) -> list[str]:
        return list(self._result.keys())


    def close(self):
        if self.is_writing:
            with open(self.path, "w") as f:
                json.dump(self._result, f)
        else:
            pass
