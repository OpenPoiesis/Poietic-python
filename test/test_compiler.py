import unittest

from poietic.db import ObjectMemory, MutableFrame, ObjectID
from poietic.db import MutableUnboundGraph

from poietic.flows import Compiler, CompilerError, NodeIssueType
from poietic.flows import DomainView
from poietic.flows import Metamodel
from poietic.flows import ExpressionComponent

class TestDomainView(unittest.TestCase):
    db: ObjectMemory
    trans: MutableFrame
    graph: MutableUnboundGraph

    def setUp(self):
        self.db = ObjectMemory()
        self.trans = self.db.derive_frame()
        self.graph = MutableUnboundGraph(self.trans)

    def test_Empty(self):
        pass


    def test_CompileSome(self):
        # a -> b -> c
        
        trans = self.db.derive_frame()
        graph = MutableUnboundGraph(trans)

        c = graph.create_node(Metamodel.Auxiliary,
                         [ExpressionComponent(name="c",expression="b")])
        b = graph.create_node(Metamodel.Auxiliary,
                         [ExpressionComponent(name="b",expression="a")])
        a = graph.create_node(Metamodel.Auxiliary,
                         [ExpressionComponent(name="a",expression="0")])


        graph.create_edge(Metamodel.Parameter, a, b)
        graph.create_edge(Metamodel.Parameter, b, c)
        
        # FIXME: Make this a test for DomainView instead
        compiler = Compiler(trans)

        compiled = compiler.compile()
        self.assertEqual(len(compiled.sorted_expression_nodes), 3)
        self.assertEqual(compiled.sorted_expression_nodes[0].id, a)
        self.assertEqual(compiled.sorted_expression_nodes[1].id, b)
        self.assertEqual(compiled.sorted_expression_nodes[2].id, c)

        self.assertIn(a, compiled.expressions)
        self.assertIn(b, compiled.expressions)
        self.assertIn(c, compiled.expressions)


    def test_collectNames(self):
        _ = self.graph.create_node(Metamodel.Stock,
                               [ExpressionComponent(name="a",expression="0")])
        _ = self.graph.create_node(Metamodel.Stock,
                               [ExpressionComponent(name="b",expression="0")])
        _ = self.graph.create_node(Metamodel.Stock,
                               [ExpressionComponent(name="c",expression="0")])
        # TODO: Check using violation checker
        
        compiler = DomainView(self.graph)

        names = compiler.collect_names()

        self.assertTrue("a" in names)
        self.assertTrue("b" in names)
        self.assertTrue("c" in names)
        self.assertEqual(len(names), 3)

    def test_ValidateDuplicateName(self):
        c1 = self.graph.create_node(Metamodel.Stock,
                               [ExpressionComponent(name="things",expression="0")])
        c2 = self.graph.create_node(Metamodel.Stock,
                               [ExpressionComponent(name="things",expression="0")])
        _ = self.graph.create_node(Metamodel.Stock,
                               [ExpressionComponent(name="a",expression="0")])
        _ = self.graph.create_node(Metamodel.Stock,
                               [ExpressionComponent(name="b",expression="0")])
        
        # TODO: Check using violation checker
        
        compiler = DomainView(self.graph)

        try:
            compiler.collect_names()
        except CompilerError as error:
            self.assertTrue(c1 in error.node_issues)
            self.assertTrue(c2 in error.node_issues)
            self.assertEqual(len(error.node_issues), 2)
            return

        self.fail("collect_names should raise an exception")

    def test_compileExpressions(self):
        names: dict[str, ObjectID] = {
                "a": 1,
                "b": 2,
                }

        l = self.graph.create_node(Metamodel.Stock,
                               [ExpressionComponent(name="l",
                                                    expression="sqrt(a*a + b*b)")])
        compiler = DomainView(self.graph)

        exprs = compiler.compile_expressions(names)

        bound = exprs[l]
        var_refs = bound.all_variables()

        self.assertTrue(1 in var_refs)
        self.assertTrue(2 in var_refs)
        self.assertEqual(len(var_refs), 2)


    def test_UnusedInputs(self):
        used = self.graph.create_node(Metamodel.Auxiliary,
                               [ExpressionComponent(name="used",expression="0")])
        unused = self.graph.create_node(Metamodel.Auxiliary,
                               [ExpressionComponent(name="unused",expression="0")])
        tested = self.graph.create_node(Metamodel.Auxiliary,
                               [ExpressionComponent(name="tested",expression="used")])
        
        self.graph.create_edge(Metamodel.Parameter, used, tested)
        self.graph.create_edge(Metamodel.Parameter, unused, tested)
        
        compiler = DomainView(self.graph)
        
        # TODO: Get the required list from the compiler
        issues = compiler.validate_inputs(node=tested, required=["used"])

        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].type, NodeIssueType.UNUSED_INPUT)
        # FIXME: check for unused name "unused"


    def test_UnknownParameters(self):
        known = self.graph.create_node(Metamodel.Auxiliary,
                               [ExpressionComponent(name="known",expression="0")])
        tested = self.graph.create_node(Metamodel.Auxiliary,
                               [ExpressionComponent(name="tested",expression="known + unknown")])
        
        self.graph.create_edge(Metamodel.Parameter, known, tested)
        
        compiler = DomainView(self.graph)

        issues = compiler.validate_inputs(node=tested, required=["known",
                                                                 "unknown"])
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].type, NodeIssueType.UNKNOWN_PARAMETER)

    def test_FlowFillsAndDrains(self):
        flow = self.graph.create_node(Metamodel.Flow,
                               [ExpressionComponent(name="f",expression="1")])
        source = self.graph.create_node(Metamodel.Stock,
                               [ExpressionComponent(name="source",expression="0")])
        sink = self.graph.create_node(Metamodel.Stock,
                               [ExpressionComponent(name="sink",expression="0")])
        
        self.graph.create_edge(Metamodel.Drains, source, flow)
        self.graph.create_edge(Metamodel.Fills, flow, sink)
        
        compiler = DomainView(self.graph)

        self.assertEqual(compiler.flow_fills(flow), sink)
        self.assertEqual(compiler.flow_drains(flow), source)

    def test_UpdateImplicitFlows(self):
        flow = self.graph.create_node(Metamodel.Flow,
                               [ExpressionComponent(name="f",expression="1")])
        source = self.graph.create_node(Metamodel.Stock,
                               [ExpressionComponent(name="source",expression="0")])
        sink = self.graph.create_node(Metamodel.Stock,
                               [ExpressionComponent(name="sink",expression="0")])

        self.graph.create_edge(Metamodel.Drains, source, flow)
        self.graph.create_edge(Metamodel.Fills, flow, sink)

        compiler = Compiler(self.trans)
        view = DomainView(self.graph)

        self.assertEqual(len(view.implicit_drains(source)), 0)
        self.assertEqual(len(view.implicit_fills(sink)), 0)
        self.assertEqual(len(view.implicit_drains(source)), 0)
        self.assertEqual(len(view.implicit_fills(sink)), 0)
        
        compiler.update_implicit_flows()

        src_drains = view.implicit_drains(source)
        sink_drains = view.implicit_drains(sink)
        src_fills = view.implicit_fills(source)
        sink_fills = view.implicit_fills(sink)
       
        self.assertEqual(len(src_drains), 0)
        self.assertEqual(sink_drains[0], source)
        self.assertEqual(src_fills[0], sink)
        self.assertEqual(len(sink_fills), 0)

