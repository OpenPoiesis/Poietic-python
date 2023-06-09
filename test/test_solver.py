import unittest

from poietic.db import ObjectMemory, MutableFrame
from poietic.db import MutableUnboundGraph
from poietic.flows import Compiler
from poietic.flows.solver import Solver
from poietic.flows import Metamodel
from poietic.flows import ExpressionComponent

class SolverTestCase(unittest.TestCase):
    db: ObjectMemory
    trans: MutableFrame
    graph: MutableUnboundGraph
    compiler: Compiler

    def setUp(self):
        self.db = ObjectMemory()
        self.trans = self.db.derive_frame()
        self.graph = self.trans.mutable_graph
        self.compiler = Compiler(self.trans)

    def testInitializeStocks(self):

        a = self.graph.create_node(Metamodel.Auxiliary,
                               [ExpressionComponent(name="a",
                                                   expression="1")])
        b = self.graph.create_node(Metamodel.Auxiliary,
                               [ExpressionComponent(name="b",
                                                   expression="a + 1")])
        c =  self.graph.create_node(Metamodel.Stock,
                               [ExpressionComponent(name="const",
                                                   expression="100")])
        s_a = self.graph.create_node(Metamodel.Stock,
                               [ExpressionComponent(name="use_a",
                                                   expression="a")])
        s_b = self.graph.create_node(Metamodel.Stock,
                               [ExpressionComponent(name="use_b",
                                                   expression="b")])

        self.graph.create_edge(Metamodel.Parameter, a, b)
        self.graph.create_edge(Metamodel.Parameter, a, s_a)
        self.graph.create_edge(Metamodel.Parameter, b, s_b)

        compiled = self.compiler.compile()
        solver = Solver(compiled)
        
        vector = solver.initialize()
        
        self.assertEqual(vector[a], 1)
        self.assertEqual(vector[b], 2)
        self.assertEqual(vector[c], 100)
        self.assertEqual(vector[s_a], 1)
        self.assertEqual(vector[s_b], 2)

    def testOrphanedInitialize(self):

        a = self.graph.create_node(Metamodel.Auxiliary,
                               [ExpressionComponent(name="a",
                                                   expression="1")])
        compiled = self.compiler.compile()
        solver = Solver(compiled)
        
        vector = solver.initialize()
        
        self.assertIn(a, vector)

    def testEverythingInitialized(self):
        aux = self.graph.create_node(Metamodel.Auxiliary,
                               [ExpressionComponent(name="a",
                                                   expression="10")])
        stock = self.graph.create_node(Metamodel.Stock,
                               [ExpressionComponent(name="b",
                                                   expression="20")])
        flow = self.graph.create_node(Metamodel.Flow,
                               [ExpressionComponent(name="c",
                                                   expression="30")])

        compiled = self.compiler.compile()
        solver = Solver(compiled)
        
        vector = solver.initialize()
        
        self.assertEqual(vector[aux], 10)
        self.assertEqual(vector[stock], 20)
        self.assertEqual(vector[flow], 30)
