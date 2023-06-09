# issues.py
#
# Node issues.
#
# Created by: Stefan Urbanek
# Date: 2023-04-03


from typing import Self, Optional
from enum import Enum, auto

from ..db import ObjectID

__all__ = [
    "NodeIssueType",
    "NodeIssue",
    "CompilerError",
]

class NodeIssueType(Enum):
    EXPRESSION_SYNTAX_ERROR = auto()
    UNUSED_INPUT = auto()
    UNKNOWN_PARAMETER = auto()
    DUPLICATE_NAME = auto()

    def __str__(self) -> str:
        match self:
            case self.EXPRESSION_SYNTAX_ERROR:
                return "Expression syntax error"
            case self.UNUSED_INPUT:
                return "Unused input"
            case self.UNKNOWN_PARAMETER:
                return "Unused parameter"
            case self.DUPLICATE_NAME:
                return "Duplicate name"


class NodeIssue:
    type: NodeIssueType
    message: str

    def __init__(self, type: NodeIssueType, message: str):
        self.type = type
        self.message = message

    # Conveinence initializers so we do not have noise in the source
    @classmethod
    def expression_syntax_error(cls, message: str) -> Self:
        return cls(type=NodeIssueType.EXPRESSION_SYNTAX_ERROR, message=message)

    @classmethod
    def unused_input(cls, message: str) -> Self:
        return cls(type=NodeIssueType.UNUSED_INPUT, message=message)

    @classmethod
    def unknown_parameter(cls, message: str) -> Self:
        return cls(type=NodeIssueType.UNKNOWN_PARAMETER, message=message)

    @classmethod
    def duplicate_name(cls, message: str) -> Self:
        return cls(type=NodeIssueType.DUPLICATE_NAME, message=message)


class CompilerError(Exception):
    node_issues: dict[ObjectID, list[NodeIssue]]
    def __init__(self, issues: Optional[dict[ObjectID, list[NodeIssue]]] = None,
                 message: Optional[str] = None):
        super().__init__(message)
        self.node_issues = issues or dict()

