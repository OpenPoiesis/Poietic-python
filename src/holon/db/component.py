# component.py
#
# Created by: Stefan Urbanek
# Date: 2023-03-30
#
from typing import Type, Optional, TypeVar, cast, Protocol

class Component(Protocol):
    """Protocol for object components.

    Components must conform to this protocol to be properly recognized by
    the system.

    Currently there is no other requirement.

    .. note:
        The ``Component``concept in this project is rather a logical one than a
        phyisical one. How the components are stored should be opaque to the
        user of the framework. One can think of component as of grouping of
        attributes. The primary use-cases of the groups are:

        - extensibility of the model through composition
        - separation of concerns by providing different aspects on objects to
          systems using the objects as they need it
    """
    pass


C = TypeVar("C", bound=Component)

class ComponentSet:
    """Primitive implementation for a per-object component storage.

    The component set stores one instance of a component per component type.
    """
    _components: dict[Type[Component], Component]

    def __init__(self, components: Optional[list[Component]] = None):
        """Create a new component set."""
        self._components = dict()

        if components:
            for component in components:
                self.set(component)

    def set(self, component: Component):
        self._components[component.__class__] = component

    def remove(self, component_type: Type[Component]):
        del self._components[component_type]

    def remove_all(self):
        self._components.clear()

    def get(self, component_type: Type[C]) -> C:
        """Get a component of type `component_type`. Raises `KeyError` when the
        component is not present."""
        return cast(C, self._components[component_type])

    def as_list(self) -> list[Component]:
        return list(self._components.values())

    def has(self, component_type: Type[Component]) -> bool:
        """Returns `true` when the component `component_type` is present."""
        return component_type in self._components

    def __str__(self) -> str:
        comp_list = ", ".join(str(key.__name__) for key in self._components.keys())
        return f"[{comp_list}]"

