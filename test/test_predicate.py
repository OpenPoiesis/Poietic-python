# test_predicate.py
#
# Created by: Stefan Urbanek
# Date: 2023-04-01
#


import unittest

from holon.component import Component
from holon.object import ObjectSnapshot, ObjectID
from holon.predicate import HasComponentPredicate
from holon.frame import VersionFrame
from holon.graph import UnboundGraph

class TestComponent(Component):
    text: str
    def __init__(self, text: str):
        self.text = text

class TestPredicate(unittest.TestCase):
    def test_has_component(self):
        frame = VersionFrame(0)
        graph = UnboundGraph(frame)
        
        obj_yes = ObjectSnapshot(id=1, version=0,
                                 components=[TestComponent(text="test")])
        obj_no = ObjectSnapshot(id=2, version=0)

        frame.insert(obj_yes)
        frame.insert(obj_no)

        pred = HasComponentPredicate(TestComponent)

        self.assertTrue(pred.match(graph, obj_yes))
        self.assertFalse(pred.match(graph, obj_no))


