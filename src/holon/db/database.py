# database.py
#
# Created by: Stefan Urbanek
# Date: 2023-03-30
#

# FIXME: Rename the file/module to `memory`

from typing import Optional, Iterable, Type, cast

from ..persistence.store import \
        PersistentStore, \
        PersistentRecord, \
        ExtendedPersistentRecord

from ..metamodel import MetamodelBase
from ..graph import Node, Edge

from .frame import StableFrame
from .component import PersistableComponent

from .mutable_frame import MutableFrame
from .identity import SequentialIDGenerator, VersionID, ObjectID, SnapshotID
from .object import ObjectSnapshot
from .constraints import Constraint, ConstraintViolation


__all__ = [
    "ObjectMemory"
]


# TODO: Validate whether objects have required components according to
# the metamodel
class ObjectMemory:
    """Database represents a versioned object memory.
    """
    # TODO: Rename to "Design" or "DesignProject"
    # TODO: This is NOT thread-safe, however it should be.
    # TODO: All access to *_id_generator should be atomic
    # TODO: [IMPORTANT] Separate all history related functionality.

    identity_generator: SequentialIDGenerator
    """
    Generator for identifiers of persistent objects: objects, frames,
    snapshots.
    """
    
    """
    List of versions that are represented by version planes in the database.
    
    Returned value has at least one element.
    
    - Note: The returned order is unspecified. Do not treat it as a
      sequential historical order.
    """

    _stable_frames: dict[VersionID,StableFrame]
    _mutable_frames: dict[VersionID,MutableFrame]

    # History management
    # TODO: Separate this functionality
    version_history: list[VersionID]
    """List of versions in chronological order."""

    current_version_index: Optional[int]


    metamodel: Optional[Type[MetamodelBase]]

    
    @property
    def all_versions(self) -> list[VersionID]:
        """
        List of all frame versions present in the database.

        The order is arbitrary and nothings should be inferred from it.
        """
        return list(self._stable_frames.keys())
    
    def __init__(self,
                 metamodel: Optional[Type[MetamodelBase]]=None,
                 store: Optional[PersistentStore]=None):
        """
        Create a new database.

        `store` is a persistent store from which the design will be loaded. If
        not provided an empty design will be created.
        """
        self._stable_frames = dict()
        self._mutable_frames = dict()
        self.version_history = list()
        self.current_version_index = None
        self.identity_generator = SequentialIDGenerator()
        self.metamodel = metamodel


        if store is not None:
            if metamodel is not None:
                self._initialize_from_store(metamodel=metamodel,
                                            store=store)
            else:
                raise RuntimeError("Store provided without metamodel")
        else:
            # Create a first frame.
            # TODO: This is a history-related functionality that needs to be
            # separated.
            frame = self.create_frame()
            self.accept(frame)

    def _initialize_from_store(self,
                               metamodel: Type[MetamodelBase],
                               store: PersistentStore):
        # NOTE: Keep this method in-sync with save()
        # TODO: Consider passing richer context thhan just metamodel, something
        # that might include the version as well so the functions down-stream
        # would be able to adapt, if possible.

        info: PersistentRecord = store.read_info_record()

        version = info["version"]

        # TODO: This is hardcoded for now
        if version != "0.0.1":
            raise Exception(f"Unknown dump format version: {version}")

        snapshots: dict[ObjectID, ObjectSnapshot] = dict()

        # 1. Load all the snapshots and create records.
        for record in store.read_extended_records("snapshots"):
            type_name = cast(str, record["type"])
            object_type = metamodel.type_by_name(type_name)
            structural_type = object_type.structural_type_name

            match structural_type:
                case "node": 
                    snapshot = Node.from_record(metamodel=metamodel,
                                                record=record)
                case "edge":
                    snapshot = Edge.from_record(metamodel=metamodel,
                                                record=record)
                case _: raise Exception(f"Unknown structural type: {structural_type}")

            snapshots[snapshot.snapshot_id] = snapshot

        for record in store.read_extended_records("frames"):
            frame_id: VersionID = cast(int, record["frame_id"]) 
            ids: list[VersionID] = cast(list[int], record["snapshots"]) 

            frame = self.create_frame(version=frame_id)
        
            for id in ids:
                snapshot = snapshots[id]
                # We insert a snapshot to the frame and make it non-owned. The
                # frame will be closed immediately and made stable (not-mutable)
                frame.insert(snapshot, owned=False)

            self.accept(frame)
        pass


    def save(self, store: PersistentStore):
        """
        Dump the design into the persistent store, replacing the existing
        design in the store.

        .. note::
            This is a preliminary and straightforward implementaiton of
            persistence. It will likely change in the future.

        .. note::

            This is actually a data structure and data model transformation
            method: it transforms from in-memory transactional model into an
            external relational model.
        """
        # NOTE: Keep this method in-sync with _initialize_from_store()

        info: PersistentRecord = PersistentRecord()

        info["version"] = "0.0.1"

        store.write_info_record(info)

        # What we are going to store:

        snapshots: list[ExtendedPersistentRecord] = list()
        frames: list[ExtendedPersistentRecord] = list()

        # 1. Write snapshots
        # ----------------

        for obj in self.snapshots:
            record = obj.persistent_record()
            snapshots.append(record)

        # 1. Write snapshots
        # ----------------

        for frame in self.frames:
            ids: list[SnapshotID] = list(obj.id for obj in frame.snapshots)
            frame_record = ExtendedPersistentRecord()
            frame_record["frame_id"] = frame.version
            frame_record["snapshots"] = ids
            frames.append(frame_record)

        store.write_extended_records("snapshots", snapshots)
        store.write_extended_records("frames", frames)

        # Here the store is expected to have:
        #
        # - info
        # - snapshots
        # - frames

        store.close()


    def clear(self):
        """Clearsthe whole memory, removing all objects.

        .. note::

            Intent of this method is to satisfy loading of the memory from a
            store. 
            
        """
        pass
    
    @property
    def frames(self) -> Iterable[StableFrame]:
        """Get a list of all stable (accepted) frames in the database."""
        return self._stable_frames.values()

    
    def frame(self, version: VersionID) -> StableFrame:
        """Get a frame with given version identifier.

        A `RuntimeError` is raised when the frame does not exist.
        """
        return self._stable_frames[version]

    @property
    def snapshots(self) -> Iterable[ObjectSnapshot]:
        """All snapshots contained in stable frames of the memory."""
        seen: set[SnapshotID] = set()
        for frame in self._stable_frames.values():
            for snapshot in frame.snapshots:
                if snapshot.id in seen:
                    continue
                seen.add(snapshot.id)
                yield snapshot

    @property
    def current_version(self) -> VersionID:
        """
        Version identifier of the latest state in the history of versions.
        """
        if (index := self.current_version_index) is None:
            raise RuntimeError("Memory has no history (no current version index)")
        if not self.version_history:
            raise RuntimeError("Version history is empty (should not be)")
        try:
            return self.version_history[index]
        except IndexError:
            raise RuntimeError("Invalid current version index")
    
    
    @property
    def current_frame(self) -> StableFrame:
        """Get current version frame from the version history."""
        return self.frame(self.current_version)
    

    def contains_version(self, version: VersionID) -> bool:
        """Returns `true` if the memory contains a frame (stable or mutable) with given
        version."""
        return version in self._stable_frames \
                or version in self._mutable_frames
       
    def versions(self, id: ObjectID) -> list[VersionID]:
        """Return list of stable versions of an object with given ID."""
        versions: list[VersionID] = list()

        for frame in self._stable_frames.values():
            if frame.contains(id):
                versions.append(frame.version)

        return versions

    
    def create_frame(self, version: Optional[VersionID] = None) -> MutableFrame:
        """
        Create a new empty mutable frame in the storage and assign it a new version
        ID.

        Precondition: storage must not contain a frame with given version.

        :param VersionID version: Version identity of the new frame. If not
            provided, a new version ID will be generated.
        :return: Newly created version frame.


        .. note::
            Usually you do not want to call this method, as creating an empty
            frame is a very unique operation. This method is used by the
            database to create the very first frame.
        """

        actual_version: VersionID

        if version is not None:
            assert not self.contains_version(version)
            self.identity_generator.mark_used(version)
            actual_version = version
        else:
            actual_version = self.identity_generator.next()

        frame = MutableFrame(memory=self,
                             version=actual_version)
        self._mutable_frames[actual_version] = frame

        return frame

    
    def derive_frame(self,
                     original_version: Optional[VersionID] = None,
                     version: Optional[VersionID] = None) -> MutableFrame:
        """Derive a frame from an existing frame.

        :param VersionID originalVersion: Version of the frame to be used as an original.
            If it is not provided (default `None`) then current version is used as
            the original.
        :param VersionID version: Version of the new frame. If not
            provided, a new version ID will be generated.

        - Precondition: Memory must not contain `version`.
        - Precondition: Only stable frame can be derived.

        """
        # TODO: [IMPORTANT] Remove history related functionality - using
        # "current version" for original; make original required.

        actual_version: VersionID
        actual_original_version: VersionID

        if original_version is not None:
            assert self.contains_version(original_version)
            actual_original_version = original_version
        else:
            actual_original_version = self.current_version


        if version is not None:
            assert not self.contains_version(version)
            self.identity_generator.mark_used(version)
            actual_version = version
        else:
            actual_version = self.identity_generator.next()

        original = self._stable_frames[actual_original_version]

        derived = MutableFrame(memory=self,
                               version=actual_version,
                               objects=original.snapshots)
        self._mutable_frames[actual_version] = derived
        
        return derived

    
    def remove_frame(self, version: VersionID):
        """Remove a frame `version` from the storage."""

        # TODO: Garbage collect objects

        if version in self._stable_frames:
            del self._stable_frames[version]
        elif version in self._mutable_frames:
            del self._mutable_frames[version]
        else:
            raise RuntimeError(f"Unknown frame: {version}")


    def accept(self, frame: MutableFrame, append_history: bool = True):
        """Commit an open transaction and push the frame version into the
        history.

        If transaction has no changes, nothing happens.

        Guarantees:

        * commited frame has referential integrity within the structural
          objects
        * all objects in the commited frame are either transient or frozen.
        """
        assert frame.memory is self, \
                "Trying to accept a frame from a different memory"
        
        # Validate integrity

        missing_objects: list[ObjectID] = list()
        for obj in frame.derived_objects:
            missing_objects += (dep for dep in obj.structural_dependencies()
                                if not frame.contains(dep))

        if missing_objects:
            raise RuntimeError("Unhandled integrity violation: missing structural dependencies")

        # We need to freeze the mutable frame before we can derive a stable
        # frame.
        frame.freeze()

        stable_frame = StableFrame(version=frame.version,
                                   objects=frame.snapshots)


        if not frame.has_referential_integrity:
            raise RuntimeError(f"Referential integrity violated (frame: {frame.version})")

        self._stable_frames[frame.version] = stable_frame
        del self._mutable_frames[frame.version]

        # History management
        if append_history:
            if self.current_version_index is not None:
                if self.version_history:
                    # Delete "redo" history
                    del self.version_history[self.current_version_index + 1:]
                self.current_version_index += 1
            else:
                self.current_version_index = 0
            self.version_history.append(frame.version)


    def discard(self, frame: MutableFrame):
        """Discards a mutable frame.

        Cleans-up all objects related to the mutable frame.
        """
        assert frame.memory is self, \
                "Trying to discard a frame from a different memory"
        assert frame.state.is_mutable, \
                "Trying to discard already accepted frame"

        frame.freeze()
        del self._mutable_frames[frame.version]
        # TODO: Garbage collect objetcs


    # History undo/redo
    # --------------------------------------------------------

    @property
    def undoable_versions(self) -> list[VersionID]:
        """List of versions that can be undone."""
        if self.current_version_index is not None:
            return self.version_history[0:self.current_version_index+1]
        else:
            return []

    @property
    def redoable_versions(self) -> list[VersionID]:
        """List of versions that can be redone."""
        if self.current_version_index is not None:
            return self.version_history[self.current_version_index+1:]
        else:
            return []

    def undo(self, version: VersionID):
        """
        Undo the changes in the history timeline of the database up to the given
        version.
        
        The function removes all history from the version forward, leaving
        the database in the state in the version `version`.
        
        - Precondition: The version must exist in the version history, otherwise
          it is considered a programming error.

        """
    
        # Get the index of the version we would like to undo to. We search
        # from the end of the version list.
        #
        try:
            index = self.version_history.index(version)
        except:
            raise RuntimeError(f"Trying to reset to version '{version}', which does not exist in the history")

        self.current_version_index = index
    
    
    def redo(self, version: VersionID):
        """
        Redo the undone changes up to the given version.
        
        The function places all undoned vesiojns from the redo history back
        to the version history up to the `version`.
        
        - Precondition: The redo stack must not be empty here.
        - Precondition: The requested version must exist in the redo stack,
          otherwise it is considered a programming error.
        """
        try:
            index = self.version_history.index(version)
        except:
            raise RuntimeError(f"Trying to redo to version '{version}', which does not exist in the history")

        self.current_version_index = index


    # Constraints
    # --------------------------------------------------------

    def check_constraints(self, constraints: list[Constraint]) -> list[ConstraintViolation]:
        violations: list[ConstraintViolation] = list()

        for constraint in constraints:
            if (violation := self.check_constraint(constraint)):
                violations.append(violation)

        return violations

    def check_constraint(self, constraint: Constraint) -> Optional[ConstraintViolation]:
        raise NotImplementedError


# TODO: [IMPORTANT] Garbage collection of unused versions of graph objects (nodes/edges)

# FIXME: change to HistoryManager and associate the memory with it.
# class HistoryManager:
#     # TODO :Make it this public read-only
#     version_history: list[VersionID]
#     """List of versions in chronological order."""
#
#     current_version_index: int
#
#     def append_version(self, version: VersionID):
#         ...
#     def undo_to_version(self, version: VersionID):
#         ...
#     def redo_to_version(self, version: VersionID):
#         ...
#     
#     """
#     List of versions of a graph for performing redo operation after an
#     undo operation. The last item is the most recently undoed item.
#     
#     When re-doing the whole history, last item in the list is taken and
#     restored as a current graph.
#     
#     - Note: All dependent objects of the histories referenced in the redo
#     history must be retained and should not be garbage collected.
#     """
#
#     def __init__(self, memory: ObjectMemory):
#         super().__init__()
#
#         self.memory = memory
#
#         frame = self.memory.create_frame()
#         
#         self.commit(frame)
#         
#         self.version_history = [initial_version]
#         self.redo_history = []
#     
#     @property
#     def current_version(self) -> VersionID:
#         """
#         Version identifier of the latest state in the history of versions.
#         """
#         if not self.version_history:
#             raise RuntimeError("Version history is empty (should not be)")
#         try:
#             return self.version_history[self.current_version_index]
#         except IndexError:
#             raise RuntimeError("Invalid current version index")
#     
#     
#     @property
#     def current_frame(self) -> StableFrame:
#         """Get current version frame from the version history."""
#         return self.frame(self.current_version)
#     
#     def create_frame(self) -> MutableFrame:
#         ...
#
#     def undo(self, version: VersionID):
#         """
#         Undo the changes in the history timeline of the database up to the given
#         version.
#         
#         The function removes all history from the version forward, leaving
#         the database in the state in the version `version`.
#         
#         - Precondition: The version must exist in the version history, otherwise
#           it is considered a programming error.
#
#         """
#     
#         # Get the index of the version we would like to undo to. We search
#         # from the end of the version list.
#         #
#         try:
#             index = self.version_history.index(version)
#         except:
#             raise RuntimeError(f"Trying to reset to version '{version}', which does not exist in the history")
#
#         next_index = index + 1
#         
#         undo_versions = self.version_history[next_index:]
#         del self.version_history[next_index:]
#         undo_versions.reverse()
#         self.redo_history += undo_versions
#     
#     
#     def redo(self, version: VersionID):
#         """
#         Redo the undone changes up to the given version.
#         
#         The function places all undoned vesiojns from the redo history back
#         to the version history up to the `version`.
#         
#         - Precondition: The redo stack must not be empty here.
#         - Precondition: The requested version must exist in the redo stack,
#           otherwise it is considered a programming error.
#         """
#         try:
#             index = self.redo_history.index(version)
#         except:
#             raise RuntimeError(f"Trying to redo to version '{version}', which does not exist in the history")
#
#         redo_versions = self.redo_history[index:]
#         del self.redo_history[index:]
#         redo_versions.reverse()
#         self.version_history += redo_versions
#
#
