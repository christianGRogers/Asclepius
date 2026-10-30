"""Janus-M border reads (JA7): labels, read protocol, read checker and anchoring report.

Janus-M learns four structures on rest CCTA (JA1); its reference standard is two
independent reads of each of the 60 seal and 40 decision cases, under the written
protocol in ``docs/JANUSM-READ-PROTOCOL.md``. This package is what code checks
about those reads. It is separate from SegQueue14 (``src/segqueue14``) on purpose:
another protocol number, other labels, another queue.

Two halves, kept apart like ``src/segqueue``:

* **stdlib only, Python 3.9** -- :mod:`.labels`, :mod:`.protocol`, :mod:`.readset`
  and :mod:`.holdout`. A Slicer client can import these.
* **numpy / scipy** -- :mod:`.checker` (half-maximum rule and label conventions),
  :mod:`.anchoring` (the per-wave report) and :mod:`.seeds` (coarsened seeds).
  These run on the server's worker, on Fir, or on a laptop; never inside Slicer.
"""

#: The Janus-M read protocol version. Its own number line, starting at 1: it is
#: not SegQueue's or SegQueue14's, and is never compared with them.
PROTOCOL_VERSION = 1

#: The name a client and server use for this protocol in headers and refusals.
PROTOCOL_NAME = "janusm-read"

__all__ = ["PROTOCOL_VERSION", "PROTOCOL_NAME"]
