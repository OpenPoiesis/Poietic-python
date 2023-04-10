# object_type.py
#
# Meta-model entity: Representation of design object types.
#
# Created by: Stefan Urbanek
# Date: 2023-04-01
#

from typing import Type, Optional, TYPE_CHECKING

from .component import Component

if TYPE_CHECKING:
    from .object import ObjectSnapshot


__all__ = [
    "ObjectType",
]


class ObjectType:
    """Represents and describes a type the object.

    Typically a meta-model would describe a list of object types of the model
    domain. 

    Since the object types are unique for a meta-model, they can be compared
    using identity comparison.

    .. note:
        Analogous concepts are _class_ from OOP or _archetype_ from ECS.
    """

    name: str
    """Name of the object type.

    The name will be used in the interchange format.
    """

    component_types: list[Type[Component]]
    """
    List of component types that the object of this type is expected to
    contain.
    """

    structural_type = Optional[Type["ObjectSnapshot"]]
    """Structural type that objects of this type must be, for example an Edge
    or a Node. If not provided, then the object might be of any structural type
    """

    def __init__(self,
                 name: str,
                 structural_type: Optional[Type["ObjectSnapshot"]] = None,
                 component_types: Optional[list[Type[Component]]] = None):
                 
        self.name = name
        self.component_types = component_types or list()
        self.structural_type = structural_type

