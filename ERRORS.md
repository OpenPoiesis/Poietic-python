# List of Errors

This file contains a list of errors that might be caused either by the user or
by the system.

If no further information is specified, then the error is not handled
gracefully.

All errors must be handled gracefully except fatal errors.

- TODO: Assign each error a number
- TODO: For each error specify how it is expected to be handled
- TODO: For each error specify how it is handled currently

## Persistence Errors

- File not found (for reading)
- File can not be created (for writing)
- Unknown version number
    - Current: Unhandled generic exception. Must be exact match.
- Missing info
- Missing snapshot collection
- Missing frames collection
- Missing 'object_id'
    - Current: KeyError exception
- Missing 'snapshot_id'
    - Current: KeyError exception
- Missing 'type' for object type
    - Current: KeyError exception
- No 'type' in metamodel
    - Current: KeyError exception
- No component in metamodel
    - Current: KeyError exception

- No `frame_id` in frame record
- No `snapshots` in frame record
