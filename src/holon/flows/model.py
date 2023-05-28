# model.py
#
# Stock and Flows Metamodel
#
# Created by: Stefan Urbanek
# Date: 2023-04-01

from dataclasses import dataclass, field
from typing import ClassVar, cast, Type

from ..graph.predicate import \
        NodePredicate, \
        EdgePredicate, \
        HasComponentPredicate, \
        IsTypePredicate

from ..db.constraints import \
        UniqueNeighborRequirement

from ..graph import EdgeDirection

from ..graph import NeighborhoodSelector

from ..metamodel import MetamodelBase
from ..db import Component, PersistableComponent, ObjectType
from ..graph import Edge, Node
from ..attributes import AttributeReference
from ..persistence.store import PersistentRecord
from ..db.constraints import UniqueAttribute, NodeConstraint
from ..value import Point


__all__ = [
    "Metamodel",
    "PositionComponent",
    "DescriptionComponent",
    "ErrorComponent",
    "FlowComponent",
    "StockComponent",
    "ExpressionComponent",
]

# Basic components
#
# Components that are share-able between various (meta-)models.
#


# TODO: Move this to holon
class NodeQuery:
    predicate: NodePredicate

    def __init__(self, predicate: NodePredicate):
        self.predicate = predicate

class EdgeQuery:
    predicate: EdgePredicate

    def __init__(self, predicate: EdgePredicate):
        self.predicate = predicate

# Components
# --------------------------------------------------------------------------

@dataclass
class PositionComponent(PersistableComponent):
    """Component containing position within the design canvas."""
    component_name: ClassVar[str] = "Position"

    position: Point
    """Location of the design object within its design canvas."""

    @classmethod
    def from_record(cls, record: PersistentRecord) -> "PositionComponent":
        x: float = cast(float, record.get("x", 0.0))
        y: float = cast(float, record.get("y", 0.0))
        return cls(Point(x, y))

    def persistent_record(self) -> PersistentRecord:
        record = PersistentRecord()

        record["x"] = self.position.x
        record["y"] = self.position.y

        return record

@dataclass
class DescriptionComponent(PersistableComponent):
    """Component containing human-targeted object description. Designer
    stores more detailed information in this component.
    """
    component_name: ClassVar[str] = "Description"

    description: str
    """Human-readable textual description of the associated design object."""

    @classmethod
    def from_record(cls, record: PersistentRecord) -> "DescriptionComponent":
        desc: str = cast(str, record.get("description", ""))
        return cls(desc)

    def persistent_record(self) -> PersistentRecord:
        record = PersistentRecord()

        record["description"] = self.description

        return record

class ErrorComponent(Component):
    """Component cotnaining list of compilation/interpretation errors related
    to the object.

    .. note::
        This component is not persistable - not available for import/export.
    """
    errors: list[Exception]
    """List of errors associated with the object."""

# Specific components
#

@dataclass
class FlowComponent(PersistableComponent):
    """Component for flow nodes."""
    component_name: ClassVar[str] = "Flow"

    priority: int = 0
    """Flow priority for evaluation of non-negative stock outflows."""

    @classmethod
    def from_record(cls, record: PersistentRecord) -> "FlowComponent":
        priority: int = cast(int, record.get("priority", 0))

        return cls(priority)

    def persistent_record(self) -> PersistentRecord:
        record = PersistentRecord()

        record["priority"] = self.priority

        return record

@dataclass
class StockComponent(PersistableComponent):
    component_name: ClassVar[str] = "Stock"

    allows_negative: bool = False
    """
    Flag whether the stock allows non-negative value. If `False` then the
    stock value is constrained to be >= 0. This affects the evaluation.
    """

    delayed_inflow: bool = False
    """
    Flag wether the inflow will be delayed during evaluation.

    Delaying inflow is required when there are flow-based cycles between
    stocks - that is when an outflow of a stock results in an inflow of the same stock
    through a chain of of other flows.
    """

    @classmethod
    def from_record(cls, record: PersistentRecord) -> "StockComponent":
        allows_negative: bool = cast(bool, record.get("allows_negative", False))
        delayed_inflow: bool = cast(bool, record.get("delayed_inflow", False))
        return cls(allows_negative, delayed_inflow)

    def persistent_record(self) -> PersistentRecord:
        record = PersistentRecord()

        record["allows_negative"] = self.allows_negative
        record["delayed_inflow"] = self.delayed_inflow

        return record



@dataclass
class ExpressionComponent(PersistableComponent):
    """Core component containing the arithemtic expression for a node."""

    component_name: ClassVar[str] = "Expression"

    name: str = "unnamed"
    """Name of the node that is used in arithmetic expressions."""
    expression: str = "0"

    """Arithmetic expression of the node."""

    @classmethod
    def from_record(cls, record: PersistentRecord) -> "ExpressionComponent":
        name: str = cast(str, record.get("name", "unnamed"))
        expression: str = cast(str, record.get("expression", "0"))
        return ExpressionComponent(name, expression)
       
    def persistent_record(self) -> PersistentRecord:
        record = PersistentRecord()

        record["name"] = self.name
        record["expression"] = self.expression

        return record


# Flows Meta Model
# --------------------------------------------------------------------------

# TODO: This should be in some inter-change format, simple DSL or something.

# TODO: Add edge endpoint type constraints
# TODO: Add dimension

class Metamodel(MetamodelBase):
    """A singleton object describing the details of the Stocks and Flows domain
    model.

    This object is used as a source of truth - list of types, queries and other
    elements that formalize the domain model.

    All queries should be described in this object and the system should refer
    to these queries by their names.

    All node types should be described in this object and the system must not
    create nodes that are not defined here.


    .. note:
        We are using a Python class and class variables for simplicity. No
        instances of this class should be created.

        Alternatively we might use python module, but I prefer a feature that
        can be easily ported to another language.

    .. note:
        In the future there is a plan for validation of the model based on this
        metamodel description.

    .. note:
        This metamodel will be used in the future for validatin imports of
        models from external sources.

    """

    components: list[Type[Component]] = [
        PositionComponent,
        DescriptionComponent,
        ErrorComponent,
        FlowComponent,
        StockComponent,
        ExpressionComponent,
    ]


    Stock = ObjectType(
            name="Stock",
            structural_type = Node,
            component_types=[
                ExpressionComponent,
                # LocationComponent,
                # DescriptionComponent,
                # ErrorComponent,
                StockComponent,
            ],


            )
    """Objec type for Stock nodes."""

    Flow = ObjectType(
            name="Flow",
            structural_type = Node,
            component_types=[
                ExpressionComponent,
                # LocationComponent,
                # DescriptionComponent,
                # ErrorComponent,
                FlowComponent,
            ])
    """Objec type for Flow nodes."""

    Auxiliary = ObjectType(
            name="Auxiliary",
            structural_type = Node,
            component_types=[
                ExpressionComponent,
                # LocationComponent,
                # DescriptionComponent,
                # ErrorComponent,
            ])
    """Objec type for Auxiliary nodes."""

    Fills = ObjectType(
            name="Fills",
            structural_type = Edge,
            component_types=[
                # None for now,
            ])
    """Object type for edges originating in a flow and ending in a stocks
    representing the flow filling the stock."""
     
    Drains = ObjectType(
            name="Drains",
            structural_type = Edge,
            component_types=[
                # None for now,
            ])
    """Object type for edges originating in a stock and ending in a flow
    representing the flow draining the stock."""
     
    Parameter = ObjectType(
            name="Parameter",
            structural_type = Edge,
            component_types=[
                # None for now,
            ])
    """Object type for edges originating in a parameter node (any expression
    node) and ending in a node using the parameter value."""

    # Internal type
    ImplicitFlow = ObjectType(
            name="ImplicitFlow",
            structural_type = Edge,
            component_types=[
                # None for now,
            ])
    """
    Object type for edges originating in a stock and ending in a stock where
    the originating stocks fills the target stock through a flow in between
    them.

    For example: let us have two stocks, one named _source_ and another named
    _sink_, and a flow in between them::

                 (drains)         (fills)
        source -----------> flow ---------> sink

    This edge represents the edge::

                 (drains)         (fills)
        source -----------> flow ---------> sink
           |                                  ^
           +----------------------------------+
                        (implicit flow)

    """

    # Constraints
    # ----------------------------------------------------------------------


    constraints = [ 
    NodeConstraint(
        name= "single_flow_fill",
        description= """
                     All flows must have only one outgoing 'flow' edge to a
                     stock. This is a model integrity constraint.
                     """,
        predicate= IsTypePredicate(Flow),
        requirement= UniqueNeighborRequirement(IsTypePredicate(Fills))
    ),

    NodeConstraint(
        name= "single_flow_drain",
        description= """
                     All flows must have only one incoming "flow" edge
                     from a stock. This is a model integrity constraint.
                     """,
        predicate= IsTypePredicate(Flow),
        requirement= UniqueNeighborRequirement(IsTypePredicate(Drains),
                                               direction=EdgeDirection.INCOMING)
    ),

    # NodeConstraint(
    #     name= "drain_and_fill_is_different",
    #     description= """
    #                  Drains edge of a flow node must be different from the
    #                  fills edge.
    #                  """,
    #     predicate= SameDrainFill(),
    #     requirement= RejectAll()
    # ),

    NodeConstraint(
        name= "unique_node_name",
        description= """
                     Expression nodes (flows, stocks and auxiliaries)
                     should have a unique name.
                     """,

        predicate= IsTypePredicate([Flow, Stock, Auxiliary]),
        requirement= UniqueAttribute(
                        AttributeReference(ExpressionComponent, "name")
                        )
    ),
    ]

    # Queries
    # ----------------------------------------------------------------------
     
    expression_nodes = HasComponentPredicate(ExpressionComponent)
    flow_nodes = IsTypePredicate(Flow)

    parameter_edges = IsTypePredicate(Parameter)
    incoming_parameters = NeighborhoodSelector(
            predicate=parameter_edges,
            direction=EdgeDirection.INCOMING,
        )

    # FIXME: This is emegent complexity that needs to be polished.
    # TODO: Have Graph.select_neigbors(object_type)
    fills_edge = IsTypePredicate(Fills)
    fills = NeighborhoodSelector(
            predicate=fills_edge,
            direction=EdgeDirection.OUTGOING,
        )
    drains_edge = IsTypePredicate(Drains)
    drains = NeighborhoodSelector(
            predicate=drains_edge,
            direction=EdgeDirection.INCOMING,
        )

    # Edge between stocks, derived by the compiler (not user).
    #
    implicit_flow_edge = IsTypePredicate(ImplicitFlow)
    implicit_fills = NeighborhoodSelector(
            predicate=implicit_flow_edge,
            direction=EdgeDirection.OUTGOING,
        )
    implicit_drains = NeighborhoodSelector(
            predicate=implicit_flow_edge,
            direction=EdgeDirection.INCOMING,
        )


    def __init__(self):
        raise RuntimeError("Metamodel should not be instantiated")
