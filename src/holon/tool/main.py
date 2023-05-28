import click
from ..db import ObjectMemory
from ..flows.example import create_predator_prey
from ..persistence.store import JSONStore

@click.group()
def cli():
    pass

@cli.command()
def initdb():
    click.echo('Initialized the database')

@cli.command()
def create_demo():
    click.echo("Creating demo model...")
    mem = ObjectMemory()
    frame = mem.derive_frame()
    create_predator_prey(frame.mutable_graph)
    mem.accept(frame)

    store = JSONStore("demo.json", writing=True)
    mem.save(store)


def tool_main():
    cli()
