
# test_predicate.py
#
# Created by: Stefan Urbanek
# Date: 2023-05-24
#


import unittest
from dataclasses import dataclass
from typing import cast, ClassVar

from holon.metamodel import MetamodelBase
from holon.db.object_type import ObjectType
from holon.db.object import ObjectSnapshot
from holon.db.component import PersistableComponent
from holon.graph import Node, Edge

from holon.persistence.store import PersistentRecord, ExtendedPersistentRecord
from holon.persistence.store import JSONStore

from holon.db import ObjectMemory, MutableFrame
from holon.db import MutableUnboundGraph

from pathlib import Path
from tempfile import TemporaryDirectory


@dataclass
class TestComponent(PersistableComponent):
    value: int = 0

    component_name: ClassVar[str] = "Test"

    @classmethod
    def from_record(cls, record: PersistentRecord) -> "TestComponent":
        value: int = cast(int, record.get("value", 0))

        return cls(value)

    def persistent_record(self) -> PersistentRecord:
        record = PersistentRecord()

        record["value"] = self.value

        return record


class Metamodel(MetamodelBase):
    components = [
            TestComponent,
    ]

    Stock = ObjectType(
            name="Stock",
            structural_type = Node,
            component_types=[
            ])

    Flow = ObjectType(
            name="Flow",
            structural_type = Node,
            component_types=[
            ])
    
    Parameter = ObjectType(
            name="Parameter",
            structural_type = Edge,
            component_types=[
            ])

    Arrow = ObjectType(
            name="Arrow",
            structural_type = Edge,
            component_types=[
            ])


class TestMetamodel(unittest.TestCase):
    def test_get_type(self):
        self.assertIs(Metamodel.type_by_name("Stock"), Metamodel.Stock)
        self.assertIs(Metamodel.type_by_name("Flow"), Metamodel.Flow)
        self.assertIs(Metamodel.type_by_name("Parameter"), Metamodel.Parameter)

    def test_get_all_types(self):
        names = Metamodel.all_type_names

        self.assertEqual(set(names), set(["Stock", "Flow", "Parameter", "Arrow"]))


class TestPersistentRecord(unittest.TestCase):
    def test_from_record_node(self):
        record = ExtendedPersistentRecord({
                "object_id": 10,
                "snapshot_id": 20,
                "structural_type": "node",
                "type": "Stock",
        })

        obj: ObjectSnapshot = ObjectSnapshot.from_record(metamodel=Metamodel,
                                                         record=record)

        self.assertEqual(obj.id, 10)
        self.assertEqual(obj.snapshot_id, 20)
        # self.assertIsInstance(obj, Node)
        self.assertIs(obj.type, Metamodel.Stock)

    def test_component_to_record(self):
        component = TestComponent(10)
        result = component.persistent_record()

        record = PersistentRecord({ "value": 10 })

        self.assertEqual(result, record)

    def test_component_from_record(self):
        record = PersistentRecord({ "value": 10 })

        component: TestComponent = TestComponent.from_record(record)

        self.assertEqual(component.value, 10)

    def test_snapshot_with_component(self):
        record = ExtendedPersistentRecord({
                "object_id": 10,
                "snapshot_id": 20,
                "structural_type": "node",
                "type": "Stock",
        })

        record.set_component("Test",
                             PersistentRecord({"value": 10}))

        obj: ObjectSnapshot = ObjectSnapshot.from_record(metamodel=Metamodel,
                                                         record=record)

        self.assertEqual(TestComponent(10), obj[TestComponent])


class TestPersistentStore(unittest.TestCase):
    db: ObjectMemory
    frame: MutableFrame

    def setUp(self):
        self.db = ObjectMemory()
        self.frame = self.db.derive_frame()
        self.graph = MutableUnboundGraph(self.frame)

        flow = self.graph.create_node(Metamodel.Flow,
                               [TestComponent(value=10)])
        source = self.graph.create_node(Metamodel.Stock,
                               [TestComponent(value=20)])
        sink = self.graph.create_node(Metamodel.Stock,
                               [TestComponent(value=30)])

        self.graph.create_edge(Metamodel.Arrow, source, flow)
        self.graph.create_edge(Metamodel.Arrow, flow, sink)
        self.db.accept(self.frame)

    def test_restore(self):
        tmpdir = TemporaryDirectory()
       
        path = Path(tmpdir.name) / "db.json"

        save_store = JSONStore(str(path), writting=True)
        self.db.save(save_store)

        load_store = JSONStore(str(path), writting=False)
        restored = ObjectMemory(metamodel=Metamodel,
                                store=load_store)
        self.assertEqual(len(list(self.db.snapshots)),
                         len(list(restored.snapshots)))

        other_frame = restored.frame(self.frame.version)

        for snapshot in self.frame.snapshots:
            other = other_frame.object(snapshot.id)
            if snapshot != other:
                # import pdb; pdb.set_trace()
                pass

            self.assertEqual(snapshot, other)

        tmpdir.cleanup()

    def test_restore_history(self):
        frame = self.db.derive_frame()
        graph = MutableUnboundGraph(frame)
        node = graph.create_node(Metamodel.Stock,
                                [TestComponent(value=100)])
        self.db.accept(frame)
        frame = self.db.derive_frame()
        frame.remove_cascading(node)
        self.db.accept(frame)

        # Create a frame that will not be part of the history
        frame = self.db.derive_frame()
        self.db.accept(frame, append_history=False)

        # Sanity check
        all_versions = self.db.all_versions
        self.assertEqual(len(all_versions), 5)

        tmpdir = TemporaryDirectory()
        path = Path(tmpdir.name) / "db.json"

        save_store = JSONStore(str(path), writting=True)
        self.db.save(save_store)

        load_store = JSONStore(str(path), writting=False)
        restored = ObjectMemory(metamodel=Metamodel,
                                store=load_store)

        self.assertEqual(self.db.all_versions,
                         restored.all_versions)

        self.assertEqual(self.db.version_history,
                         restored.version_history)

        tmpdir.cleanup()

        
