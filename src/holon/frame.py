from typing import Optional
from .version import VersionID, VersionState
from .object import ObjectID, ObjectSnapshot

class VersionFrame:
    """
    Configuration Plane combines different versions of objects.

    - Note: In the original paper analogous concept is called `configuration plane`
      however the more common usage of the term _"configuration"_ nowadays has a
      different connotation. Despite _configuration_ being more correct for this
      concept, we go with _arrangement_.
    """

    """Mutability state of the plane."""
    state: VersionState
    
    """
    Version associated with this plane. All objects created or modified
    in this plane share the same version. Version is unique within the
    object memory.
    """
    version: VersionID
    
    """
    Versions of objects in the plane.
    
    Objects not in the map do not exist in the version plane, but might
    exist in the object memory.

    """
    # check for mutability
    objects: dict[ObjectID, ObjectSnapshot]
   
    
    def __init__(self, version: VersionID,
                 objects: Optional[dict[ObjectID, ObjectSnapshot]] = None):
        self.version = version
        self.state = VersionState.UNSTABLE
        if objects is not None:
            self.objects = dict(objects)
        else:
            self.objects = dict()
    
    def contains(self, id: ObjectID) -> bool:
        return id in self.objects

    def derive_object(self, id: ObjectID) -> ObjectSnapshot:
        assert self.state.is_mutable
        assert id in self.objects

        original = self.objects[id]
        assert original.version != self.version, \
                     "Trying to derive already derived object"

        derived = original.derive(version=self.version)
        self.objects[id] = derived
        return derived
    
    # Remove the object from the frame
    def remove(self, id: ObjectID):
        assert self.state.is_mutable
        assert id in self.objects, \
                     f"Trying to remove an object ({id}) that is not in the frame {self.version}"
        del self.objects[id]
    
    def insert(self, snapshot: ObjectSnapshot):
        assert (self.state.is_mutable)
        assert (self.version == snapshot.version)
        assert (snapshot.id not in self.objects)
        
        self.objects[snapshot.id] = snapshot
    
    def object(self, id: ObjectID) -> Optional[ObjectSnapshot]:
        # TODO: Make mutable/immutable version of this method.
        return self.objects.get(id)
    
    def __str__(self) -> str:
        return f"VersionFrame({self.version}, state: {self.state}"
    
    def derive(self, version: VersionID) -> "VersionFrame":
        assert (self.state.can_derive)
        return VersionFrame(version=version, objects=self.objects)
    
    def make_transient(self):
        for obj in self.objects.values():
            if obj.version == self.version and obj.state == VersionState.UNSTABLE:
                obj.make_transient()

        self.state = VersionState.TRANSIENT
    
    def freeze(self):
        for obj in self.objects.values():
            if obj.version == self.version and obj.state != VersionState.FROZEN:
                obj.freeze()
        self.state = VersionState.FROZEN


class SnapshotStorage:
    frames: dict[VersionID, VersionFrame]
    
    def __init__(self):
        self.frames = dict()
    
    def frame(self, version: VersionID) -> Optional[VersionFrame]:
        return self.frames[version]

    def versions(self, id: ObjectID) -> list[VersionID]:
        versions: list[VersionID] = []

        for frame in self.frames.values():
            if frame.contains(id):
                versions.append(frame.version)

        return versions

    
    def create_frame(self, version: VersionID) -> VersionFrame:
        assert version not in self.frames

        frame = VersionFrame(version=version)
        self.frames[version] = frame

        return frame

    
    def derive_frame(self,
                     version: VersionID,
                     originalVersion: VersionID) -> VersionFrame:
        assert version not in self.frames

        original = self.frames[originalVersion]

        assert original is not None, \
                f"Unknown original frame {originalVersion}"

        derived = original.derive(version=version)
        self.frames[version] = derived
        
        return derived
    
    def remove_frame(self, version: VersionID):
        assert version in self.frames
        del self.frames[version]
