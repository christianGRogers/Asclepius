"""``segcheck.Geometry``: the grid a submission declares.

Both Slicer modules build one from the volume node and send ``to_dict()`` with
every submission, and the server stores it as sent. Nothing judges it, so the
only thing to get right is the round trip and its tolerance of what an older or
hand-written client might send.
"""

import dataclasses

import pytest

from segqueue.segcheck import Geometry


def test_round_trip_is_lossless_and_json_shaped():
    geometry = Geometry(size=(512, 512, 300), spacing=(0.4, 0.4, 0.5),
                        origin=(-100.0, -120.5, 30.0))
    data = geometry.to_dict()
    assert data == {"size": [512, 512, 300], "spacing": [0.4, 0.4, 0.5],
                    "origin": [-100.0, -120.5, 30.0]}
    assert Geometry.from_dict(data) == geometry


def test_values_are_coerced_to_their_types():
    # A JSON round trip can turn sizes into floats and spacings into strings in
    # a hand-written payload; the reader normalises rather than storing a mix.
    geometry = Geometry.from_dict({"size": [64.0, "64", 40], "spacing": ["1", 1, 2.5],
                                   "origin": [0, 0, 0]})
    assert geometry.size == (64, 64, 40)
    assert all(isinstance(v, int) for v in geometry.size)
    assert geometry.spacing == (1.0, 1.0, 2.5)
    assert all(isinstance(v, float) for v in geometry.spacing + geometry.origin)


@pytest.mark.parametrize("empty", [None, {}])
def test_nothing_declared_is_none(empty):
    assert Geometry.from_dict(empty) is None


def test_missing_or_null_fields_become_empty_and_unknown_keys_are_ignored():
    geometry = Geometry.from_dict({"size": [8, 8, 8], "spacing": None,
                                   "direction": [1, 0, 0, 0, 1, 0, 0, 0, 1]})
    assert geometry == Geometry(size=(8, 8, 8), spacing=(), origin=())
    assert geometry.to_dict() == {"size": [8, 8, 8], "spacing": [], "origin": []}


def test_geometry_is_immutable_and_hashable():
    geometry = Geometry(size=(1, 2, 3))
    with pytest.raises(dataclasses.FrozenInstanceError):
        geometry.size = (4, 5, 6)
    assert len({geometry, Geometry(size=(1, 2, 3))}) == 1
