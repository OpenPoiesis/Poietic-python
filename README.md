# Holon Project 

Toolikt and a library for developing interactive applications to support
creative modelling and experimentation process of the user.

Suitable for:

- Modelling and simulation applications where the domain model is represented
  as a graph.
- Allowing the user to experiment with the creation, move back in time, compare
  different versions of the creation.

Feature highlights:

- Object model that supports versioning (undo/redo, time machine).
- Graph representation of the model.
- Custom domain/application specific meta-models.
- Transparent storage model with focus on repairability by available tooling
  and for durability.

Included and planned problem domains:

- Stocks and Flows, including simulator/solver
- Causal Maps (planned)


Let's see what this will turn into.


## Requirements

Developed using Python 3.11.

- [Click](https://click.palletsprojects.com)

## Development

- [MyPy](https://mypy.readthedocs.io/en/stable/).

Testing:

```
python -m unittest discover -s test
```


## Documentation

The documentation is created using [Sphinx](https://www.sphinx-doc.org/en/master/usage/installation.html).

To build the documentation:


```
cd docs
make html
```

The documentation will be created in the `_build/html` directory.


## Development Note

- Technical debt is marked with TODO or FIXME (serious)
- Trying not to use too advanced python features, so that the code can be
  understood by non-advanced python developers as well as it would be possible
  to rewrite the library into another programming language(s).

## Authors

* Stefan Urbanek, stefan.urbanek@gmail.com
