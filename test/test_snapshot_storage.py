from holon.db import SnapshotStorage
from holon.db import ObjectSnapshot, Dimension

import unittest

class TestSnapshotStorage(unittest.TestCase):
    def testNew(self):
        # Just a sanity test
        storage = SnapshotStorage()
        storage.create_frame(1)
        self.assertIsNotNone(storage.frame(1))
    
    
    def testCreateObject(self):
        storage = SnapshotStorage()
        
        frame = storage.create_frame(1)
        frame.insert(ObjectSnapshot(id=10, version=1))
        frame.insert(ObjectSnapshot(id=20, version=1))

        self.assertIsNotNone(frame.object(10))
        self.assertIsNotNone(frame.object(20))
    
 
    def testDeriveFrame(self):
        storage = SnapshotStorage()
        frame = storage.create_frame(1)

        frame.insert(ObjectSnapshot(id=10, version=1))
        frame.insert(ObjectSnapshot(id=20, version=1))
        frame.insert(ObjectSnapshot(id=30, version=1))
        
        frame.make_transient()
        
        frame2 = frame.derive(version=2)
        frame2.remove(10)
        frame2.derive_object(20)
        
        self.assertTrue(frame.contains(10))
        self.assertTrue(frame.contains(20))
        self.assertTrue(frame.contains(30))

        self.assertFalse(frame2.contains(10))
        self.assertTrue(frame2.contains(20))
        self.assertTrue(frame2.contains(30))
    
    
    def testMutation(self):
        # NOTE: This tests required API - that the frame.object() returns
        #       a mutable reference, not a copy. It will fail if the
        #       ObjectSnapshot is changed to a struct or if the
        #       frame.object() returns a copy.

        # This test is to maintain the original intent of the Storage.object()
        # signature.
        
        
        storage = SnapshotStorage()
        frame = storage.create_frame(1)

        frame.insert(ObjectSnapshot(id=10, version=1))
        
        object = frame.object(10)
        if object is None:
            self.fail("Object expected")
        
        dim = Dimension(name="test")
        object.dimension = dim

        object2 = frame.object(10)
        if object2 is None:
            self.fail("Object expected")
        
        self.assertIs(dim, object2.dimension)

    
    


