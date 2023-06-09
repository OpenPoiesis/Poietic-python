# attributes.py
#
# Attribute metadata, reflection, getting and setting
#
# Created by: Stefan Urbanek
# Date: 2023-04-17
#

from .db import Component

from typing import Type

__all__ = [
        "AttributeReference"
    ]

class AttributeReference:
    component: Type[Component]
    name: str

    def __init__(self, component: Type[Component], name: str):
        self.component = component
        self.name = name


