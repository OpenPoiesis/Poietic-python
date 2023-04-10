# model.py
#
# Stock and Flows Metamodel
#
# Created by: Stefan Urbanek
# Date: 2023-04-01

from typing import ClassVar

from ..graph.predicate import \
        NodePredicate, \
        EdgePredicate, \
        HasComponentPredicate, \
        IsTypePredicate

from ..graph import EdgeDirection

from ..graph import NeighborhoodSelector

from ..db import Component, ObjectType, ObjectSnapshot
from ..graph import Edge, Node

__all__ = [
    "Metamodel",
    "LocationComponent",
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

class LocationComponent(Component):
    """Component containing position within the design canvas."""
    component_name: ClassVar[str] = "Location"

    point: tuple[float, float]

class DescriptionComponent(Component):
    """Component containing human-targeted object description. Designer
    stores more detailed information in this component.
    """
    component_name: ClassVar[str] = "Description"
    description: str

class ErrorComponent(Component):
    """Component cotnaining list of compilation/interpretation errors related
    to the object."""
    errors: list[Exception]

# Specific components
#

class FlowComponent(Component):
    """Component for flow nodes."""
    component_name: ClassVar[str] = "Flow"

    priority: int
    """Flow priority for evaluation of non-negative stock outflows."""


class StockComponent(Component):
    component_name: ClassVar[str] = "Stock"

    allows_negative: bool
    """
    Flag whether the stock allows non-negative value. If `False` then the
    stock value is constrained to be >= 0. This affects the evaluation.
    """

    delayed_inflow: bool
    """
    Flag wether the inflow will be delayed during evaluation.

    Delaying inflow is required when there are flow-based cycles between
    stocks - that is when an outflow of a stock results in an inflow of the same stock
    through a chain of of other flows.
    """

class ExpressionComponent(Component):
    """Core component containing the arithemtic expression for a node."""

    component_name: ClassVar[str] = "Expression"

    name: str
    """Name of the node that is used in arithmetic expressions."""
    expression: str

    """Arithmetic expression of the node."""

    def __init__(self, name: str, expression: str):
        self.name = name
        self.expression = expression


# Flows Meta Model
# --------------------------------------------------------------------------

# TODO: This should be in some inter-change format, simple DSL or something.

# TODO: Add edge endpoint type constraints
# TODO: Add dimension

class Metamodel:
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

    .. note:
        In the future there is a plan for validation of the model based on this
        metamodel description.

    .. note:
        This metamodel will be used in the future for validatin imports of
        models from external sources.

    """


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

    # Prototypes
    # ----------------------------------------------------------------------

    prototypes: list[ObjectSnapshot] = [
        
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

