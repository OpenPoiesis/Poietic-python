# Technical Debt

This document lists major technical debt that has been acquired during
prototyping and needs to be resolved.

## Debt Markers

In the code the most obvious debt can be found by searching for:

- `FIXME` statements where ones with `IMPORTANT` and/or `DEBT` are more serious
  or complex
- raising `RuntimeError` – the code should be written in a way that there is no
  need to raise `RuntimeError` (unless there is no other way how to write in in
  Python).
- raising `NotImplementedError`

Other signs of technical debt in this project:

- too deep object paths, usually 3 or more levels means that there is something
  quickly put together without proper desing
- typealiases to `Any` or using `Any`, unless explicitly specified that it is
  intended to be used as such
- unhandled project exceptions
- unhandled potential `KeyError`, `ValueError` or `IndexError`

# Debt: Structural Objects

Description: objects to represent structure such as graph nodes and edges are
now implemented using python subclasses of `ObjectSnapshot`.


