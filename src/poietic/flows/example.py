from .model import Metamodel
from .model import ExpressionComponent
from ..db.mutable_frame import MutableUnboundGraph
from ..db import ObjectMemory
from ..flows import Compiler, EulerSolver


def create_predator_prey(graph: MutableUnboundGraph):
    fish = graph.create_node(Metamodel.Stock,
                             [ExpressionComponent(name="fish",
                                                  expression="1000")])
    shark = graph.create_node(Metamodel.Stock,
                              [ExpressionComponent(name="shark",
                                                   expression="10")])

    fish_birth_rate = graph.create_node(Metamodel.Auxiliary,
                                   [ExpressionComponent(name="fish_birth_rate",
                                                        expression="0.01" )])
    shark_birth_rate = graph.create_node(Metamodel.Auxiliary,
                                   [ExpressionComponent(name="shark_birth_rate",
                                                        expression="0.6" )])
    shark_efficiency = graph.create_node(Metamodel.Auxiliary,
                                   [ExpressionComponent(name="shark_efficiency",
                                                        expression="0.0003")])
    shark_death_rate = graph.create_node(Metamodel.Auxiliary,
                                   [ExpressionComponent(name="shark_death_rate",
                                                        expression="0.15" )])

    fish_births = graph.create_node(Metamodel.Flow,
                                    [ExpressionComponent(name="fish_births",
                                                         expression="fish * fish_birth_rate")])
    shark_births = graph.create_node(Metamodel.Flow,
                                    [ExpressionComponent(name="shark_births",
                                                         expression="shark * shark_birth_rate * shark_efficiency * fish")])
    fish_deaths = graph.create_node(Metamodel.Flow,
                                    [ExpressionComponent(name="fish_deaths",
                                                         expression="fish * shark_efficiency * shark")])
    shark_deaths = graph.create_node(Metamodel.Flow,
                                    [ExpressionComponent(name="shark_deaths",
                                                         expression="shark_death_rate * shark")])

    graph.create_edge(Metamodel.Parameter, fish_birth_rate, fish_births)
    graph.create_edge(Metamodel.Parameter, fish, fish_births)
    graph.create_edge(Metamodel.Fills, fish_births, fish)

    graph.create_edge(Metamodel.Parameter, shark_birth_rate, shark_births)
    graph.create_edge(Metamodel.Parameter, shark, shark_births)
    graph.create_edge(Metamodel.Parameter, shark_efficiency, shark_births)
    graph.create_edge(Metamodel.Parameter, fish, shark_births)
    graph.create_edge(Metamodel.Fills, shark_births, shark)

    graph.create_edge(Metamodel.Parameter, fish, fish_deaths)
    graph.create_edge(Metamodel.Parameter, shark_efficiency, fish_deaths)
    graph.create_edge(Metamodel.Parameter, shark, fish_deaths)
    graph.create_edge(Metamodel.Drains, fish, fish_deaths)

    graph.create_edge(Metamodel.Parameter, shark, shark_deaths)
    graph.create_edge(Metamodel.Parameter, shark_death_rate, shark_deaths)
    graph.create_edge(Metamodel.Drains, shark, shark_deaths)


def predator_prey_demo(steps: int):
    """Function to experience the ergonomics of the API."""

    assert steps >= 1, \
            "Number of steps should be greater or equal than 1"

    db = ObjectMemory()
    frame = db.derive_frame()
    create_predator_prey(frame.mutable_graph)

    compiler = Compiler(frame)
    
    compiled = compiler.compile()

    solver = EulerSolver(compiled)

    initial = solver.initialize()
    state = initial

    for time in range(1, steps):
        state = solver.compute(time=time, current=state)
        print(state)

