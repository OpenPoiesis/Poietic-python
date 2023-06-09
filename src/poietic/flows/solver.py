# solver.py
#
# Created by: Stefan Urbanek
#
# Date: 2023-04-07

from typing import Optional
from abc import abstractmethod

from ..db import ObjectID
from .compiler import CompiledModel
from .compiler import BoundExpression
from .model import StockComponent
from .evaluate import evaluate_expression

from collections.abc import Container

__all__ = [
        "StateVector",
        "Solver",
        "EulerSolver",
        "RK4Solver",
]


class StateVector(Container):
    """Vector holing state of the simulation."""

    # TODO: Change this into array once we care about performance.
    values: dict[ObjectID, float]
    """Vector values. Keys are node references and values are computed values."""

    def __init__(self, values: Optional[dict[ObjectID, float]]=None):
        if (unwrapped := values):
            self.values = dict(unwrapped)
        else:
            self.values = dict()

    def __setitem__(self, key: ObjectID, value: float):
        self.values[key] = value
    
    def __getitem__(self, key: ObjectID) -> float:
        return self.values[key]

    def __contains__(self, key: ObjectID) -> bool:
        return key in self.values

    def add(self, other: "StateVector") -> "StateVector":
        new = StateVector()

        for (key, value) in self.values.items():
            new[key] = value + other.values.get(key, 0.0)

        return new

    def multiply(self, other: float) -> "StateVector":
        new = StateVector()

        for (key, value) in self.values.items():
            new[key] = value * other

        return new

    def __str__(self) -> str:
        return str(self.values)


class Solver:
    """
    Abstract class for equation solvers.

    Purpose of the solver is to initialise values of the nodes and then to
    compute each step of the simulation.

    Usage:

    .. code-block::
        :caption: Usage of a solver.

        # Assume we have the compiled model:
        compiled_model: CompiledModel

        solver: Solver = EulerSolver(compiled_model)
        t0: float = 0.0
        time_delta = 1.0

        state: StateVector
        state = solver.initialize(time = t0)

        
        t = t0

        while t < 10:
            new_state = solver.compute(time=time, state)
            t += time_delta

            # Do something with new_state, for example visualize or print
            # it...

            state = new_state
    """ 
    model: CompiledModel

    def __init__(self, model: CompiledModel):
        self.model = model

    def initialize(self, time: float = 0.0) -> StateVector:
        """Initialize the state vector."""
        vector: StateVector = StateVector()

        for node in self.model.sorted_expression_nodes:
            expression = self.model.expressions[node.id]
            vector[node.id] = self.evaluate(expression,
                                            time=time,
                                            state=vector)
        return vector

    def evaluate(self,
                 expression: BoundExpression,
                 time: float,
                 state: StateVector,
                 time_delta: float = 1.0) ->float:

        # TODO: Add time and time_delta
        return evaluate_expression(expression,
                                   variables=state.values,
                                   functions=dict())

    @abstractmethod
    def compute(self,
                time: float,
                state: StateVector,
                time_delta: float = 1.0) -> StateVector:
        ...

    def compute_stock(self,
                stock_id: ObjectID,
                time: float,
                state: StateVector) -> float:
        stock: StockComponent = self.model.stock_components[stock_id]

        total_inflow: float = 0.0
        total_outflow: float = 0.0

        if stock.allows_negative:
            for inflow in self.model.inflows[stock_id]:
                total_inflow += state[inflow]
            for outflow in self.model.outflows[stock_id]:
                total_outflow += state[outflow]
        else:
            # Non-negative stock constraint
            #
            for inflow in self.model.inflows[stock_id]:
                total_inflow += state[inflow]

            available_outflow = state[stock_id] + total_inflow
            initial_available_outflow = available_outflow

            for outflow in self.model.outflows[stock_id]:
                actual_outflow = min(available_outflow, state[outflow])
                total_outflow += actual_outflow
                available_outflow -= actual_outflow
                state[outflow] = actual_outflow

                # Sanity check
                assert state[outflow] >= 0, \
                        "Resulting state must be non-negative"

            # Another sanity check
            assert total_outflow <= initial_available_outflow, \
                    "Resulting total outflow must not exceed initial available outflow"

        delta = total_inflow - total_outflow

        return delta

    def difference(self,
                   current: StateVector,
                   time: float,
                   time_delta: float = 1.0) -> StateVector:
        estimate = StateVector()

        # 1. Evaluate auxiliaries
        for aux in self.model.auxiliaries:
            estimate[aux] = self.evaluate(expression=self.model.expressions[aux],
                                          time=time,
                                          state=current)

        # 2. Estimate flows
        for flow in self.model.flows:
            estimate[flow] = self.evaluate(expression=self.model.expressions[flow],
                                          time=time,
                                          state=current)

        # 3. Copy stock values

        for stock in self.model.stocks:
            estimate[stock] = current[stock]

        delta_vector = StateVector()

        for stock in self.model.stocks:

            delta: float

            delta = self.compute_stock(stock_id=stock,
                                       time=time,
                                       state=estimate)
            estimate[stock] += delta
            delta_vector[stock] = delta

        return delta_vector


class EulerSolver(Solver):
    def compute(self,
                time: float,
                current: StateVector,
                time_delta: float = 1.0) -> StateVector:
        delta = self.difference(time=time,
                                current=current,
                                time_delta=time_delta)
        result = current.add(delta.multiply(time_delta))

        return result


class RK4Solver(Solver):
    def compute(self,
                time: float,
                current: StateVector,
                time_delta: float = 1.0) -> StateVector:
        raise NotImplementedError
