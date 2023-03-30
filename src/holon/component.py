from typing import Type, Optional, TypeVar, cast

class Component:
    pass


C = TypeVar("C", bound=Component)

class ComponentSet:
    components: dict[Type[Component], Component]

    def __init__(self, components: Optional[list[Component]] = None):
        self.components = dict()

        if components:
            for component in components:
                self.set(component)

    def set(self, component: Component):
        self.components[component.__class__] = component

    def remove(self, component_type: Type[Component]):
        del self.components[component_type]

    def remove_all(self):
        self.components.clear()

    def get(self, component_type: Type[C]) -> C:
        """Get a component of type `component_type`. Raises `KeyError` when the
        component is not present."""
        return cast(C, self.components[component_type])

    def as_list(self) -> list[Component]:
        return list(self.components.values())

        
