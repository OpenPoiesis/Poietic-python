# solver.py
#
# Created by: Stefan Urbanek
#
# Date: 2023-04-07

from abc import abstractmethod

from ..db import ObjectID
from .compiler import CompiledModel
from .compiler import BoundExpression
from .model import StockComponent


class StateVector:
    values: dict[ObjectID, float]

    def __init__(self):
        self.values = dict()

    def __setitem__(self, key: ObjectID, value: float):
        self.values[key] = value
    
    def __getitem__(self, key: ObjectID) -> float:
        return self.values[key]

    def add(self, other: "StateVector") -> "StateVector":
        new = StateVector()

        for (key, value) in self.values.items():
            new[key] = value + other.values[key]

        return new

    def multiply(self, other: float) -> "StateVector":
        new = StateVector()

        for (key, value) in self.values.items():
            new[key] = value * other

        return new


class Solver:
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
        return 0.0

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
