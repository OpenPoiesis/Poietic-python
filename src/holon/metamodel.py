# metamodel.py
#
# Created by: Stefan Urbanek
# Date: 2023-03-30


from functools import cache

from .value import ValueType
from .db.object_type import ObjectType
from .db.component import Component, PersistableComponent

from typing import Type, ClassVar


class ArchetypeDescription:
    name: str
    """Archetype identifier."""

    components: list[str]
    """List of component names of the archetype."""

    description: str
    """Short description of the archetype."""

class ComponentDescription:
    name: str
    """Component identifier."""

    attributes: list["AttributeDescription"]
    """List of attributes of the component."""

    description: str
    """Short description of the component."""


class AttributeDescription:
    name: str
    """Attribute identifier."""

    value_type: ValueType

    title: str
    """Human-readable name of the attribute."""

    description: str
    """Short description of the attribute. Might be used as a tool-tip in GUI
    applications."""


class MetamodelBase:
    """
    Base class for all metamodels.

    .. note::

        We are using object reflection and metadata available at runtime for
        convenience of the metamodel developers.

    """
    components: ClassVar[list[Type[Component]]]

    @classmethod
    @cache
    def type_by_name(cls, name: str) -> ObjectType:
        """Get object type by name"""
        types: dict[str, ObjectType] = dict()

        for value in cls.__dict__.values():
            if isinstance(value, ObjectType):
                types[value.name] = value
        
        return types[name]


    @classmethod
    @property
    @cache
    def all_type_names(cls) -> list[str]:
        names: list[str] = list()
        for value in cls.__dict__.values():
            if isinstance(value, ObjectType):
                names.append(value.name)
        return names

    @classmethod
    @cache
    def persistable_component(cls, name: str) -> Type[PersistableComponent]:
        """Get persistable component by name"""

        for component in cls.components:
            if issubclass(component, PersistableComponent):
                if component.component_name == name:
                    return component

        raise KeyError(name)


