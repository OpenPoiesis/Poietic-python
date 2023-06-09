from poietic.db import ObjectMemory
from poietic.db import VersionID, VersionState
from poietic.db import Component

import unittest

class TestComponent(Component):
    text: str
    def __init__(self, text: str):
        self.text = text

class TestDatabase(unittest.TestCase):
    def test_empty(self):
        # test_ that empty trans does not result in a version change
        db = ObjectMemory()
        trans = db.derive_frame()
        
        db.accept(trans)
        
        self.assertFalse(trans.is_open)

        self.assertTrue(db.contains_version(trans.version))

        # Internal logic test_s - that we cleaned-up the version
        versions = db.all_versions
        self.assertEqual(len(versions), 2)

    def test_simple_accept(self):
        db = ObjectMemory()
        v1 = db.current_version

        trans = db.derive_frame()
        a = trans.create_object()
        b = trans.create_object()
        self.assertTrue(trans.contains(a))
        self.assertTrue(trans.contains(b))
        self.assertTrue(trans.has_changes)

        self.assertEqual(len(db.version_history), 1)
        db.accept(trans)

        self.assertEqual(db.version_history, [v1, trans.version])
        self.assertTrue(db.current_frame.contains(a))
        self.assertTrue(db.current_frame.contains(b))


    def test_make_object_frozen_after_accept(self):
        db = ObjectMemory()
        trans = db.derive_frame()
        a = trans.create_object()
        db.accept(trans)
        
        node = db.current_frame.object(a)

        self.assertEqual(node.state, VersionState.FROZEN)
    

    def test_discard(self):
        db = ObjectMemory()

        trans = db.derive_frame()
        trans.create_object()

        db.discard(trans)

        self.assertEqual(len(db.version_history), 1)
    

    def test_remove_object(self):
        db = ObjectMemory()
        originalTrans = db.derive_frame()

        nodeID = originalTrans.create_object(components=[TestComponent(text="hello")])
        db.accept(originalTrans)

        originalVersion = db.current_version

        removeTrans = db.derive_frame()

        self.assertTrue(db.current_frame.contains(nodeID))
        removeTrans.remove_cascading(nodeID)
        self.assertTrue(originalTrans.has_changes)
        db.accept(removeTrans)

        self.assertFalse(db.current_frame.contains(nodeID))

        original2 = db.frame(originalVersion)
        
        self.assertTrue(original2.contains(nodeID))

    def test_modify_attribute(self):
        db = ObjectMemory()
        trans = db.derive_frame()
        id = trans.create_object(components=[TestComponent(text="hello")])
        db.accept(trans)
        
        originalVersion = db.current_version

        node = db.current_frame.object(id)
        
        self.assertEqual("hello", node[TestComponent].text)

        trans2 = db.derive_frame()
        trans2.set_component(id, component=TestComponent(text="good bye"))

        self.assertTrue(trans2.has_changes)
        db.accept(trans2)

        # We need to get a fresh node snapshot from the graph
        node2 = db.current_frame.object(id)

        self.assertEqual("good bye", node2[TestComponent].text)
        self.assertEqual(len(db.versions(node2.id)), 2)

        frame = db.frame(originalVersion)
        originalNodeAgain = frame.object(id)
        
        self.assertEqual("hello", originalNodeAgain[TestComponent].text)

    
    def test_undo(self):
        db = ObjectMemory()
        v0 = db.current_version

        trans1 = db.derive_frame()
        v1 = trans1.version
        a = trans1.create_object()
        db.accept(trans1)

        trans2 = db.derive_frame()
        v2 = trans2.version
        b = trans2.create_object()
        db.accept(trans2)

        self.assertTrue(db.current_frame.contains(a))
        self.assertTrue(db.current_frame.contains(b))

        self.assertEqual(db.version_history, [v0, v1, v2])

        db.undo(v1)
        self.assertEqual(db.current_version, v1)
        self.assertEqual(db.undoable_versions, [v0, v1])
        self.assertEqual(db.redoable_versions, [v2])

        self.assertTrue(db.current_frame.contains(a))
        self.assertFalse(db.current_frame.contains(b))


        db.undo(v0)
        self.assertEqual(db.current_version, v0)
        self.assertEqual(db.undoable_versions, [v0])
        self.assertEqual(db.redoable_versions, [v1, v2])

        self.assertFalse(db.current_frame.contains(a))
        self.assertFalse(db.current_frame.contains(b))

    
    def test_undo_property(self):
        db = ObjectMemory()

        trans1 = db.derive_frame()
        v1 = trans1.version
        nodeID = trans1.create_object(components=[TestComponent(text="old")])

        db.accept(trans1)

        trans2 = db.derive_frame()
        trans2.set_component(id=nodeID,
                             component=TestComponent(text="new"))
        db.accept(trans2)

        db.undo(v1)
        node = db.current_frame.object(nodeID)
        self.assertEqual("old", node[TestComponent].text)


    def test_redo(self):
        db = ObjectMemory()
        v0 = db.current_version

        trans1 = db.derive_frame()
        v1 = trans1.version
        a = trans1.create_object()
        db.accept(trans1)

        trans2 = db.derive_frame()
        v2 = trans2.version
        b = trans2.create_object()
        db.accept(trans2)

        db.undo(v1)
        db.redo(v2)

        # Nothing must have had changed here.
        self.assertEqual(db.current_version, v2)
        self.assertEqual(db.undoable_versions, [v0, v1, v2])
        self.assertEqual(db.redoable_versions, [])

        self.assertTrue(db.current_frame.contains(a))
        self.assertTrue(db.current_frame.contains(b))

        db.undo(v0)
        db.redo(v2)

        # Nothing must have had changed here again.
        self.assertEqual(db.current_version, v2)
        self.assertEqual(db.undoable_versions, [v0, v1, v2])
        self.assertEqual(db.redoable_versions, [])

        self.assertTrue(db.current_frame.contains(a))
        self.assertTrue(db.current_frame.contains(b))

        db.undo(v0)
        db.redo(v1)

        # We are back at v1
        self.assertEqual(db.current_version, v1)
        self.assertEqual(db.undoable_versions, [v0, v1])
        self.assertEqual(db.redoable_versions, [v2])

        self.assertTrue(db.current_frame.contains(a))
        self.assertFalse(db.current_frame.contains(b))


    def test_redo_reset(self):
        db = ObjectMemory()
        v0 = db.current_version

        trans1 = db.derive_frame()
        # v1 = trans1.version
        a = trans1.create_object()
        db.accept(trans1)

        db.undo(v0)

        trans2 = db.derive_frame()
        v2 = trans2.version
        b = trans2.create_object()
        db.accept(trans2)

        self.assertEqual(db.current_version, v2)
        self.assertEqual(db.version_history, [v0, v2])
        self.assertEqual(db.undoable_versions, [v0, v2])
        self.assertEqual(db.redoable_versions, [])

        self.assertFalse(db.current_frame.contains(a))
        self.assertTrue(db.current_frame.contains(b))
