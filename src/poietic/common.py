# common.py
#
# Common utility functions
#
# Date: 2023-04-07

from typing import Optional, TypeVar, Callable
from collections.abc import Iterator

__all__ = [
    "first",
    "first_index",
]

T = TypeVar("T")

def first(iterator: Iterator[T],
          predicate: Optional[Callable[[T], bool]] = None) -> Optional[T]:
    """Return first item of an iterator or None if no such item exists.

    Optionally a predicate can be applied.
    """
    if (pred := predicate):
        try:
            item: T = next(item for item in iterator if pred(item))
            return item
        except StopIteration:
            return None
    else:
        try:
            item: T = next(iterator)
            return item
        except StopIteration:
            return None

def first_index(iterator: Iterator[T],
                predicate: Callable[[T], bool]) -> Optional[int]:
    """Return first item of an iterator or None if no such item exists.

    Optionally a predicate can be applied.
    """
    for (i, item) in enumerate(iterator):
        if predicate(item):
            return i
    return None
