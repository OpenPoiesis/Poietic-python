# value.py
#
# Value protocol - representing basic value types
#
# created by: stefan urbanek
# date: 2023-04-01

from enum import Enum, auto
from collections import namedtuple
from typing import Any

__all__ = [
    "Point",
    "ValueProtocol",
    "ValueType",
    "value_to_int",
    "value_to_bool",
    "value_to_float",
    "value_to_string",
]


class Point(namedtuple('Point', ['x', 'y'])):
    """Two-dimensional vector representing a point. The elements are float
    values.

    .. note:
        Systems that do not support vector types can represent the value as two
        floating-point types and use the base attribute name through a dot
        notation with the respective vector element, for example: `location.x`
        and `location.y`.

    """
    __slots__ = ()
    @property
    def __str__(self):
        return f"Point(x={self.x}, y={self.y})"

    def __bool__(self) -> bool:
        raise ValueError

    def __float__(self) -> float:
        raise ValueError

    def __int__(self) -> int:
        raise ValueError


ValueProtocol = int | float | bool | str | Point
"""
Type of basic values. Only values of the types conforming to this protocol
can be used in the design attributes that are to be acessed by an external
(sub)system. The following functionality relies on the value protocol:

- Design inter-change - import/export of the design to external form that is
  going to be consumed by other tools.
- User-interface inspection - accessing values through user-interface elements,
  such as inspector panels.
"""


class ValueType(Enum):
    """Enumeration of core value types."""
    INT = auto()
    """An integer type."""
    FLOAT = auto()
    """A floating point type."""
    BOOL = auto()
    """A boolean type."""
    STRING = auto()
    """A text type."""
    POINT = auto()
    """A two-dimensional point type - a vecator of two elements `x` and `y`.
    See a note in `Point` for more information.
    """


# NOTE: Python does not allow extending existing types in a straightforward
# way. We do not want to do any meta-class meddling for clarity, so we just
# add a set of functions here.

def value_type(value: ValueProtocol) -> ValueType:
    """Get a basic value type of the value provided."""

    if isinstance(value, bool):
        return ValueType.BOOL
    elif isinstance(value, int):
        return ValueType.INT
    elif isinstance(value, float):
        return ValueType.FLOAT
    elif isinstance(value, str):
        return ValueType.STRING
    elif isinstance(value, Point):
        return ValueType.POINT
    else:
        raise RuntimeError


def value_to_int(value: ValueProtocol) -> int:
    """Get an integer representation of the provided value."""
    return int(value)


def value_to_float(value: ValueProtocol) -> float:
    return float(value)


def value_to_bool(value: ValueProtocol) -> bool:
    """Get a boolan representation of the provided value. The value is `True` if
    the value is non-zero of if the string contains words `"true"` or `"yes"`.
    """
    if isinstance(value, str):
        return value.lower() in ["true", "yes"]
    else:
        return bool(value)


def value_to_string(value: ValueProtocol) -> str:
    """Get a string representation of the value. All values can be converted to
    a string."""
    return str(value)

