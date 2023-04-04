# test_predicate.py
#
# Created by: Stefan Urbanek
# Date: 2023-04-01
#


import unittest

from holon.flows import Metamodel, ExpressionComponent

from holon.db import Database, Transaction
from holon.graph import MutableUnboundGraph

from holon.db import Component
from holon.db import ObjectSnapshot
from holon.db import VersionFrame
from holon.graph import HasComponentPredicate
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

class TestGraphQuery(unittest.TestCase):
    db: Database
    trans: Transaction
    graph: MutableUnboundGraph

    def setUp(self):
        self.db = Database()
        self.trans = self.db.create_transaction()
        self.graph = MutableUnboundGraph(self.trans)

    def test_selectNodes(self):
        node_id = self.graph.create_node(Metamodel.Auxiliary,
                              [ExpressionComponent(name="c",expression="0")])

        nodes = list(self.graph.select_nodes(Metamodel.expression_nodes))

        self.assertEqual(len(nodes), 1)
        self.assertEqual(nodes[0].id, node_id)
        self.assertIs(nodes[0], self.graph.node(node_id))

