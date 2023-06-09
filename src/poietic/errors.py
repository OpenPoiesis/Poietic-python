
from typing import Any

__all__ = [
    "IDError",
]

class IDError(Exception):
    """Error raised when an invalid ID is used."""
    id: Any

    def __init__(self, id: Any):
        self.id = id

