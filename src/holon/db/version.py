# version.py
#
# Created by: Stefan Urbanek
# Date: 2023-03-30
#

from enum import Enum, auto

__all__ = [
    "VersionState",
]


class VersionState(Enum):
    """
    State of a versioned object snapshot.

    The VersionState denotes how the version snapshot can be used for a mutation
    of the object itself or for a mutation of its owner.

    Objects can be `frozen`, `stable` and `transient`. The following table
    describes what can be done with the objects in given state:

    .. list-table:: Capabilities based on state
        :header-rows: 1

        * - 
          - `unstable`
          - `transient`
          - `stable`
        * - Change invariant attributes
          - No
          - No
          - No
        * - Change versioned attributes
          - Yes
          - No
          - No
        * - Change unversioned attributes
          - Yes
          - Yes
          - No
        * - Derive new version
          - No
          - Yes
          - Yes
    """

    UNSTABLE = auto()
    """
    Denotes that the version of an object is mutable however it is still
    eing initialised. No derivative versions can be created from an object
    n this state,
    """
    
    TRANSIENT = auto()
    """
    Denotes that the version an object is mutable and one can derive other
    versions from it.
    """
    
    FROZEN = auto()
    """
    Denotes that the version of an object is immutable and can not become
    mutable any more.
    
    - no modification is allowed
    - all members should be either frozen or unversioned
    - new versions can be derived
    
    """


    @property
    def is_mutable(self) -> bool:
        """
        Returns ``True`` if the object can be mutated, based on its version
        state.
        """
        return self == VersionState.UNSTABLE or self == VersionState.TRANSIENT

    @property
    def can_derive(self) -> bool:
        """
        Returns ``True`` if the object can be derived based on its version state.
        """
        return self == VersionState.TRANSIENT or self == VersionState.FROZEN

