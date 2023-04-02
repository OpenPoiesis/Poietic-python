from holon.database import Database
from holon.version import VersionID, VersionState
from holon.component import Component

import unittest

class TestComponent(Component):
    text: str
    def __init__(self, text: str):
        self.text = text

class TestDatabase(unittest.TestCase):
    def test_Empty(self):
        # test_ that empty trans does not result in a version change
        db = Database()
        version1 = db.current_version
        trans = db.create_transaction()
        
        db.commit(trans)
        
        self.assertFalse(trans.is_open)

        self.assertEqual(version1, db.current_version)
        # Internal logic test_s - that we cleaned-up the version
        versions = db.all_versions
        self.assertEqual(len(versions), 1)
        self.assertEqual(versions[0], version1)

    def test_SimpleCommit(self):
        db = Database()
        version1 = db.current_version

        trans = db.create_transaction()
        a = trans.create_object()
        b = trans.create_object()
        self.assertTrue(trans.has_changes)

        self.assertFalse(db.current_frame.contains(a))
        self.assertFalse(db.current_frame.contains(b))
        self.assertEqual(len(db.version_history), 1)
        db.commit(trans)

        self.assertEqual(db.version_history, [version1, trans.version])
        self.assertTrue(db.current_frame.contains(a))
        self.assertTrue(db.current_frame.contains(b))

        self.assertNotEqual(version1, db.current_version)
    

    def test_MakeNodeStableAfterCommit(self):
        db = Database()
        trans = db.create_transaction()
        a = trans.create_object()
        db.commit(trans)
        
        if not (node := db.current_frame.object(a)):
            self.fail("Node was not created")

        self.assertEqual(node.state, VersionState.TRANSIENT)
    

    def test_Rollback(self):
        db = Database()
        version1 = db.current_version

        trans = db.create_transaction()
        node = trans.create_object()

        db.rollback(trans)

        # Basic sanity test_s
        self.assertEqual(len(db.version_history), 1)
        self.assertFalse(db.current_frame.contains(node))
        self.assertEqual(version1, db.current_version)


        # Internal logic test_s - that we cleaned-up the version
        versions: list[VersionID] = db.all_versions
        self.assertEqual(len(versions), 1)
        self.assertEqual(versions[0], version1)
    

    def test_RemoveNode(self):
        db = Database()
        originalTrans = db.create_transaction()

        nodeID = originalTrans.create_object(components=[TestComponent(text="hello")])
        db.commit(originalTrans)

        originalVersion = db.current_version

        removeTrans = db.create_transaction()

        self.assertTrue(db.current_frame.contains(nodeID))
        removeTrans.remove_object(nodeID)
        self.assertTrue(originalTrans.has_changes)
        db.commit(removeTrans)

        self.assertFalse(db.current_frame.contains(nodeID))

        if not (original2 := db.frame(originalVersion)):
            self.fail("Original frame disappeared")
        
        self.assertTrue(original2.contains(nodeID))

    def test_ChangeAttribute(self):
        db = Database()
        trans = db.create_transaction()
        id = trans.create_object(components=[TestComponent(text="hello")])
        db.commit(trans)
        
        originalVersion = db.current_version

        if not(node := db.current_frame.object(id)):
            self.fail("Expected object")
        
        self.assertEqual("hello", node[TestComponent].text)

        trans2 = db.create_transaction()
        trans2.set_component(id, component=TestComponent(text="good bye"))

        self.assertTrue(trans2.has_changes)
        db.commit(trans2)

        # We need to get a fresh node snapshot from the graph
        if not (node2 := db.current_frame.object(id)):
            self.fail("Expected object")
        

        self.assertEqual(node2.version, trans2.version)
        self.assertEqual("good bye", node2[TestComponent].text)
        self.assertEqual(len(db.storage.versions(node2.id)), 2)

        if not (frame := db.frame(originalVersion)):
            self.fail("Fetching of original frame failed")

        if not (originalNodeAgain := frame.object(id)):
            self.fail("Fetching of original object failed")
        
        self.assertEqual("hello", originalNodeAgain[TestComponent].text)

    
    def test_Undo(self):
        db = Database()
        v0 = db.current_version

        trans1 = db.create_transaction()
        v1 = trans1.version
        a = trans1.create_object()
        db.commit(trans1)

        trans2 = db.create_transaction()
        v2 = trans2.version
        b = trans2.create_object()
        db.commit(trans2)

        self.assertTrue(db.current_frame.contains(a))
        self.assertTrue(db.current_frame.contains(b))

        self.assertEqual(db.version_history, [v0, v1, v2])
        self.assertEqual(db.redo_history, [])

        db.undo(v1)
        self.assertEqual(db.current_version, v1)
        self.assertEqual(db.version_history, [v0, v1])
        self.assertEqual(db.redo_history, [v2])

        self.assertTrue(db.current_frame.contains(a))
        self.assertFalse(db.current_frame.contains(b))


        db.undo(v0)
        self.assertEqual(db.current_version, v0)
        self.assertEqual(db.version_history, [v0])
        self.assertEqual(db.redo_history, [v2, v1])

        self.assertFalse(db.current_frame.contains(a))
        self.assertFalse(db.current_frame.contains(b))

    
    def test_UndoProperty(self):
        db = Database()

        trans1 = db.create_transaction()
        v1 = trans1.version
        nodeID = trans1.create_object(components=[TestComponent(text="old")])

        db.commit(trans1)

        trans2 = db.create_transaction()
        trans2.set_component(id=nodeID,
                            component=TestComponent(text="new"))
        db.commit(trans2)

        db.undo(v1)
        if not (node := db.current_frame.object(nodeID)):
            self.fail("Node creation failed")
        
        self.assertEqual("old", node[TestComponent].text)

    

    def test_Redo(self):
        db = Database()
        v0 = db.current_version

        trans1 = db.create_transaction()
        v1 = trans1.version
        a = trans1.create_object()
        db.commit(trans1)

        trans2 = db.create_transaction()
        v2 = trans2.version
        b = trans2.create_object()
        db.commit(trans2)

        db.undo(v1)
        db.redo(v2)

        # Nothing must have had changed here.
        self.assertEqual(db.current_version, v2)
        self.assertEqual(db.version_history, [v0, v1, v2])
        self.assertEqual(db.redo_history, [])

        self.assertTrue(db.current_frame.contains(a))
        self.assertTrue(db.current_frame.contains(b))

        db.undo(v0)
        db.redo(v2)

        # Nothing must have had changed here again.
        self.assertEqual(db.current_version, v2)
        self.assertEqual(db.version_history, [v0, v1, v2])
        self.assertEqual(db.redo_history, [])

        self.assertTrue(db.current_frame.contains(a))
        self.assertTrue(db.current_frame.contains(b))

        db.undo(v0)
        db.redo(v1)

        # We are back at v1 of the graph.
        self.assertEqual(db.current_version, v1)
        self.assertEqual(db.version_history, [v0, v1])
        self.assertEqual(db.redo_history, [v2])

        self.assertTrue(db.current_frame.contains(a))
        self.assertFalse(db.current_frame.contains(b))

    

    def test_MutationResetsRedoStack(self):
        db = Database()
        v0 = db.current_version

        trans1 = db.create_transaction()
        # v1 = trans1.version
        a = trans1.create_object()
        db.commit(trans1)

        db.undo(v0)

        trans2 = db.create_transaction()
        v2 = trans2.version
        b = trans2.create_object()
        db.commit(trans2)

        self.assertEqual(db.current_version, v2)
        self.assertEqual(db.version_history, [v0, v2])
        self.assertEqual(db.redo_history, [])

        self.assertFalse(db.current_frame.contains(a))
        self.assertTrue(db.current_frame.contains(b))
