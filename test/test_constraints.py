import unittest

from holon.db import ObjectSnapshot
from holon.db.constraints import \
        Constraint, \
        UniqueAttribute, \
        EdgeEndpointType

from holon.db import ObjectMemory

from .common import NodeTypeA, NodeTypeB, EdgeTypeA

class ConstraintsTestCase(unittest.TestCase):
    def setUp(self):
        self.db = ObjectMemory()
        self.transaction = self.db.derive_frame()
        self.graph = self.transaction.mutable_graph

    def test_endpoint_type_requirement(self):
        a = self.graph.create_node(NodeTypeA)
        b = self.graph.create_node(NodeTypeB)

        edge_aa = self.graph.create_edge(EdgeTypeA, a, a)
        edge_ab = self.graph.create_edge(EdgeTypeA, a, b)
        edge_ba = self.graph.create_edge(EdgeTypeA, b, a)
        edge_bb = self.graph.create_edge(EdgeTypeA, b, b)

        edges: list[ObjectSnapshot] = list(self.graph.edges())

        req1 = EdgeEndpointType(origin_type=NodeTypeA)
        self.assertEqual(list(o.id for o in req1.check(self.graph, edges)),
                         [edge_ba, edge_bb])

        req2 = EdgeEndpointType(target_type=NodeTypeA)
        self.assertEqual(list(o.id for o in req2.check(self.graph, edges)),
                         [edge_ab, edge_bb])

        req3 = EdgeEndpointType(origin_type=NodeTypeA,
                                target_type=NodeTypeB)
        self.assertEqual(list(o.id for o in req3.check(self.graph, edges)),
                         [edge_aa, edge_ba, edge_bb])
        
