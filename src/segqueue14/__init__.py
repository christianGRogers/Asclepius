"""SegQueue14 -- the pooled-volume, seed-splitting variant of SegQueue.

The name is historical: it was built for 14 ImageCAS-X classes (D9) and is now
four classes again -- LM, LAD, LCx, RCA, side branches by territory (D25).

Runs **beside** the live SegQueue (``src/segqueue``, ``server/girder_segqueue``,
``slicer/SegQueue``) and changes nothing about it: its own Girder plugin
(``server/girder_segqueue14``, REST prefix ``/segqueue14``), its own Slicer module
(``slicer/SegQueue14``) and its own wire-protocol version. See
``vault/Plans/Human decisions.md`` D8-D25 for the decisions it implements.

Like ``segqueue`` this package is stdlib-only and Python 3.9 compatible, because
the Slicer module imports it inside Slicer's bundled Python. It may import from
``segqueue`` -- but only names that already exist in the live release, because in
an installed Slicer the live module's vendored ``segqueue`` copy can be the one on
``sys.path`` first.
"""

__version__ = "0.1.0"

#: SegQueue14's own wire-protocol version. Deliberately far from the live
#: protocol's numbering (1): a live SegQueue client, or a SegQueue14 module from
#: before a breaking change, is refused with a message telling the annotator to
#: update the SegQueue14 module, instead of writing a submission in the wrong
#: classes. 15 (D25): four classes; a 14-class module (protocol 14, SegQueue
#: 0.14.0) is refused.
PROTOCOL_VERSION = 15
