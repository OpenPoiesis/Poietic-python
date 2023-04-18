# database.py
#
# Created by: Stefan Urbanek
# Date: 2023-03-30
#


from .transaction import Transaction
from .frame import VersionFrame
from .frame import SnapshotStorage
from .version import VersionID
from .identity import SequentialIDGenerator
from .object import ObjectID
from typing import Optional

from .constraints import Constraint, ConstraintViolation

__all__ = [
    "Database"
]

class Database:
    # TODO: This needs to be wrapped in a lock
    object_id_generator: SequentialIDGenerator
    """
    Sequential generator for object identifiers - unique for each object
    during the lifetime of the database.
    """
    
    # TODO: This needs to be wrapped in a lock
    version_id_generator: SequentialIDGenerator
    """
    Sequential generator for version identifiers - unique for each
    transaction during the lifetime of the database.

    """ 
    
    storage: SnapshotStorage
    """
    List of versions that are represented by version planes in the database.
    
    Returned value has at least one element.
    
    - Note: The returned order is unspecified. Do not treat it as a
      sequential historical order.
    """
    
    @property
    def all_versions(self) -> list[VersionID]:
        """
        List of all frame versions present in the database.

        The order is arbitrary and nothings should be inferred from it.
        """
        return list(self.storage.frames.keys())
    
    # TODO :Make it this public read-only
    version_history: list[VersionID]
    """List of versions in chronological order."""
    
    # TODO: [IMPORTANT] Garbage collection of unused versions of graph objects (nodes/edges)
    
    # Undo/redo buffers
    
    # TODO: Make thos public read-only
    redo_history: list[VersionID]
    """
    List of versions of a graph for performing redo operation after an
    undo operation. The last item is the most recently undoed item.
    
    When re-doing the whole history, last item in the list is taken and
    restored as a current graph.
    
    - Note: All dependent objects of the histories referenced in the redo
    history must be retained and should not be garbage collected.
    """
    
    @property
    def current_version(self) -> VersionID:
        """
        Version identifier of the latest state in the history of versions.
        """
        if not self.version_history:
            raise RuntimeError("Version history is empty (should not be)")
        return self.version_history[-1]
    
    
    def __init__(self):
        """
        Create a new empty database.
        """
        self.version_id_generator = SequentialIDGenerator()
        self.object_id_generator = SequentialIDGenerator()

        self.storage = SnapshotStorage()
        
        initial_version = self.version_id_generator.next()
        frame = self.storage.create_frame(initial_version)
        
        frame.freeze()
        
        self.version_history = [initial_version]
        self.redo_history = []
    
    @property
    def current_frame(self) -> VersionFrame:
        """Current version frame."""
        frame = self.storage.frame(self.current_version)
        return frame
    
    
    def frame(self, version: VersionID) -> VersionFrame:
        """Get a frame with given version identifier.

        A `RuntimeError` is raised when the frame does not exist.
        """
        return self.storage.frame(version)


    def contains_version(self, version: VersionID) -> bool:
        """Returns `true` if the storage contains given version."""
        return self.storage.contains(version)
        
   
    
    def create_transaction(self) -> Transaction:
        """Create a new transaction."""
        version = self.version_id_generator.next()
        
        frame = self.storage.derive_frame(version, originalVersion=self.current_version)
        transaction = Transaction(database=self, frame=frame)
        
        return transaction
    
    
    def commit(self, transaction: Transaction):
        """Commit an open transaction and push the frame version into the
        history.

        If transaction has no changes, nothing happens.

        Guarantees:

        * commited frame has referential integrity within the structural
          objects
        * all objects in the commited frame are either transient or frozen.
        """
        assert(transaction.is_open)
        assert(transaction.version not in self.version_history)
        
        if not transaction.has_changes:
            self.storage.remove_frame(transaction.version)
            transaction.close()
            return
       
        # Validate integrity

        missing_objects: list[ObjectID] = list()
        for obj in transaction.derived_objects.values():
            missing_objects += (dep for dep in obj.structural_dependencies()
                                if not transaction.frame.contains(dep))

        if missing_objects:
            raise RuntimeError("Unhandled integrity violation: missing structural dependencies")

        # Finalize
        transaction.frame.make_transient()

        if not transaction.frame.has_referential_integrity:
            raise RuntimeError(f"Referential integrity violated (transaction: {transaction.version})")

        self.version_history.append(transaction.version)
        self.redo_history.clear()
        transaction.close()
    

    def rollback(self, transaction: Transaction):
        """Rolls-back the transaction.

        Cleans-up all objects related to the transaction and closes the
        transaction.
        """
        assert(transaction.is_open)
        self.storage.remove_frame(transaction.version)
        transaction.close()
    

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

        next_index = index + 1
        
        undo_versions = self.version_history[next_index:]
        del self.version_history[next_index:]
        undo_versions.reverse()
        self.redo_history += undo_versions
    
    
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
            index = self.redo_history.index(version)
        except:
            raise RuntimeError(f"Trying to redo to version '{version}', which does not exist in the history")

        redo_versions = self.redo_history[index:]
        del self.redo_history[index:]
        redo_versions.reverse()
        self.version_history += redo_versions


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
