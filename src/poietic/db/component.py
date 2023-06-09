# component.py
#
# Created by: Stefan Urbanek
# Date: 2023-03-30
#
from typing import Type, Optional, TypeVar, cast, Protocol, Self, ClassVar, \
        Iterator
from abc import abstractmethod

from ..persistence.store import PersistentRecord

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

class PersistableComponent(Component):
    """Component that is stored in the persistent store."""

    component_name: ClassVar[str]
    
    @classmethod
    @abstractmethod
    def from_record(cls, record: PersistentRecord) -> Self:
        """
        Create a new instance of the component from the persistent record.
        If a component property is not present in the record it will be
        supplied by a default value of a concrete component subclass.

        Default implementation raises an exception.
        """
        raise NotImplementedError("Subclasses of PersistableComponent are required to implement from_record()")

    @abstractmethod
    def persistent_record(self) -> PersistentRecord:
        """
        Returns a persistent record representing the persistable component.
        Subclasses of `PersistableComponent` are expected to provide all
        persistable attributes in the persistent record.

        Default implementation returns an empty record.
        """
        return PersistentRecord({})


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

    @property
    def persistable_components(self) -> dict[str, PersistableComponent]:
        """Get a mapping of persistable components. The key is the component
        name and the value is the component itself."""
        components: dict[str, PersistableComponent] = dict()
        for component in self._components.values():
            if not isinstance(component, PersistableComponent):
                continue
            name = component.component_name
            components[name] = component

        return components
            

    def has(self, component_type: Type[Component]) -> bool:
        """Returns `true` when the component `component_type` is present."""
        return component_type in self._components

    def __str__(self) -> str:
        comp_list = ", ".join(str(key.__name__) for key in self._components.keys())
        return f"[{comp_list}]"

    def __len__(self) -> int:
        return len(self._components)

    def __iter__(self) -> Iterator[Component]:
        return iter(self._components.values())

    def __eq__(self, other: Self) -> bool:
        if type(other) != type(self):
            return False

        return self._components == other._components
