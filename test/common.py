# common.py
#
# Common structures for tests.
#
# Created by: Stefan Urbanek
# Date: 2023-04-01
#

from holon.db.component import Component
from holon.db.object_type import ObjectType
from holon.graph import Node, Edge

class TestComponent(Component):
    text: str
    def __init__(self, text: str):
        self.text = text

EdgeTypeA = ObjectType(
        name="EdgeTypeA",
        structural_type = Edge,
        component_types=[
        ])
EdgeTypeB = ObjectType(
        name="EdgeTypeB",
        structural_type = Edge,
        component_types=[
        ])

NodeTypeA = ObjectType(
        name="NodeTypeA",
        structural_type = Node,
        component_types=[
        ])

NodeTypeB = ObjectType(
        name="NodeTypeB",
        structural_type = Node,
        component_types=[
        ])
