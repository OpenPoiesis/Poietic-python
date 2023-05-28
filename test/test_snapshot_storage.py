from holon.db import ObjectMemory
from holon.db import ObjectSnapshot

import unittest

class TestObjectMemory(unittest.TestCase):
    def test_create(self):
        # Just a sanity test
        memory = ObjectMemory()
        memory.create_frame(2)
        self.assertTrue(memory.contains_version(2))
    
    
    def test_insert(self):
        memory = ObjectMemory()
        
        frame = memory.create_frame(2)
        frame.insert(ObjectSnapshot(id=10, snapshot_id=10), owned=True)
        frame.insert(ObjectSnapshot(id=20, snapshot_id=20), owned=True)

        self.assertTrue(frame.contains(10))
        self.assertTrue(frame.contains(20))
    
 
    def test_derive_frame(self):
        memory = ObjectMemory()
        frame = memory.create_frame(2)

        frame.insert(ObjectSnapshot(id=10, snapshot_id=10), owned=True)
        frame.insert(ObjectSnapshot(id=20, snapshot_id=20), owned=True)
        frame.insert(ObjectSnapshot(id=30, snapshot_id=30), owned=True)
        
        memory.accept(frame)
        # TODO: This should be enough to derive.
        # frame.freeze()
        
        frame2 = memory.derive_frame(2, version=3)
        # import pdb; pdb.set_trace()
        self.assertTrue(frame2.contains(10))
        self.assertTrue(frame2.contains(20))
        self.assertTrue(frame2.contains(30))
        
        frame2.remove_cascading(10)
        frame2.mutable_object(20)
        
        self.assertTrue(frame.contains(10))
        self.assertTrue(frame.contains(20))
        self.assertTrue(frame.contains(30))

        self.assertFalse(frame2.contains(10))
        self.assertTrue(frame2.contains(20))
        self.assertTrue(frame2.contains(30))
    
