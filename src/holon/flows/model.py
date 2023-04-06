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
        EdgeDirection, \
        IsTypePredicate

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
    component_name: ClassVar[str] = "Flow"

    priority: int


class StockComponent(Component):
    component_name: ClassVar[str] = "Stock"

    allows_negative: bool
    delayed_inflow: bool


class ExpressionComponent(Component):
    component_name: ClassVar[str] = "Expression"

    name: str
    expression: str

    def __init__(self, name: str, expression: str):
        self.name = name
        self.expression = expression


# Flows Meta Model
# --------------------------------------------------------------------------

class Metamodel:
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

    Auxiliary = ObjectType(
            name="Auxiliary",
            structural_type = Node,
            component_types=[
                ExpressionComponent,
                # LocationComponent,
                # DescriptionComponent,
                # ErrorComponent,
            ])

    Fills = ObjectType(
            name="Fills",
            structural_type = Edge,
            component_types=[
                # None for now,
            ])
     
    Drains = ObjectType(
            name="Drains",
            structural_type = Edge,
            component_types=[
                # None for now,
            ])
     
    Parameter = ObjectType(
            name="Parameter",
            structural_type = Edge,
            component_types=[
                # None for now,
            ])

    # Prototypes
    # ----------------------------------------------------------------------

    prototypes: list[ObjectSnapshot] = [
        
    ]

    # Queries
    # ----------------------------------------------------------------------
     
    expression_nodes = HasComponentPredicate(ExpressionComponent)
    incoming_parameters = NeighborhoodSelector(
            predicate=IsTypePredicate(Parameter),
            direction=EdgeDirection.INCOMING,
        )

