"""SegQueue -- the annotation workforce layer that produces the labels segtrain trains on.

Two processes speak the code in this package and they do not share an interpreter:

* the **server**, a Girder 5 plugin (``server/girder_segqueue``) running on
  CPython 3.11 in a container, and
* the **Slicer extension** (``slicer/SegQueue``), running inside 3D Slicer's
  bundled Python.

So everything here is stdlib-only and Python 3.9 compatible, for the same reason
``segtrain.events`` is: Slicer 5.8 ships Python 3.9 and we refuse to pip-install
into a student's Slicer. Put the state machine, the wire protocol and the
validation rules here, where both sides import the *same* definitions; put
anything needing Mongo, numpy or Qt on the far side of that line.

The practical payoff is that the parts most likely to be wrong -- the assignment
state machine and the quality-sampling policy -- are plain functions with no I/O,
so they are tested by ``pytest`` on a laptop with no server and no Slicer.
"""

__version__ = "0.1.0"

# Bumped when the request/response shapes change in a way an older client cannot
# cope with. The server refuses clients below its own minimum (see protocol.py);
# this is what stops a student running a stale extension from writing
# half-migrated submissions into the middle of a semester's data.
PROTOCOL_VERSION = 1
