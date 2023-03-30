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

        
