# JanusMRead (Janus-M Read)

The 3D Slicer module Janus-M readers use to read the reference borders (JA7) against
the Janus-M read queue (`/api/v1/janusm`). Protocol: `docs/JANUSM-READ-PROTOCOL.md`.
Issues: #156, #195 (border protocol v1).

1. **Log in** with your Janus-M reader account.
2. **Get next case**: the CT loads with the four segments (LV myocardium, LV blood pool,
   RV blood pool, LA blood pool). A seeded case starts from its seed; a blank case starts
   empty. Hover a class in the legend for what it includes (JA1).
3. **Half-maximum** (border protocol v1): a seeded case opens with its plateaus measured
   from the seed and on the endocardial **border window** (level at the half-maximum,
   width 1.5 x the gap between the plateaus). On a blank case, measure the plateaus with
   an ROI per tissue first; until then it shows 800 / 300. Press a border to switch to
   its window; *800 / 300* is there on request. Draw on the half-way transition.
4. **Read form**: the CAD-RADS 2.0 grade of each vessel's worst lesion (LM, LAD, LCx,
   RCA), and optionally *Mark lesion* on it. Never shown to another reader.
5. **Submit read**. Values outside 0-4, overlapping classes, an empty class or an
   ungraded vessel are refused before upload. The server runs the automatic check;
   *Refresh status* shows its result. A returned read comes back with the reasons and its
   half-maximum profile plot (*Show half-maximum profile*). It is returned once: a read
   that fails the check again is accepted and flagged.

Not SegQueue14: its own module, settings (`JanusMRead/...`), cache (`~/.janusm-read`),
archive (`JanusMRead-<v>-Slicer-<x.y>.zip`, built by `slicer/build-extension-janusm.py`)
and release tag (`janusm-read-v<v>`).

Tests: `pytest tests/test_janusm_read_module.py` and, inside Slicer,
`tests/slicer_selftest_janusm.py`.
