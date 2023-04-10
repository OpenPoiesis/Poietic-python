# value.py
#
# Value protocol - representing basic value types
#
# created by: stefan urbanek
# date: 2023-04-01

from enum import Enum, auto
from collections import namedtuple

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


class ValueType(Enum):
    INT = auto()
    FLOAT = auto()
    BOOL = auto()
    STRING = auto()
    POINT = auto()

# NOTE: Python does not allow extending existing types. We do not want to do
# any dark magic here, so we just add a set of functions.

def value_type(value: ValueProtocol) -> ValueType:
    if isinstance(value, bool):
        return ValueType.BOOL
    elif isinstance(value, float):
        return ValueType.FLOAT
    elif isinstance(value, str):
        return ValueType.STRING
    elif isinstance(value, Point):
        return ValueType.POINT
    else:
        raise RuntimeError


def value_to_int(value: ValueProtocol) -> int:
    return int(value)


def value_to_float(value: ValueProtocol) -> float:
    return float(value)


def value_to_bool(value: ValueProtocol) -> bool:
    if isinstance(value, str):
        return value.lower() in ["true", "yes"]
    else:
        return bool(value)

def value_to_string(value: ValueProtocol) -> str:
    return str(value)

