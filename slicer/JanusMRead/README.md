# JanusMRead (Janus-M Read)

The 3D Slicer module Janus-M readers use to read the reference borders (JA7) against
the Janus-M read queue (`/api/v1/janusm`). Protocol: `docs/JANUSM-READ-PROTOCOL.md`.
Issue: #156.

1. **Log in** with your Janus-M reader account.
2. **Get next case**: the CT loads with the four segments (LV myocardium, LV blood pool,
   RV blood pool, LA blood pool). A seeded case starts from its seed; a blank case starts
   empty. Hover a class in the legend for what it includes (JA1).
3. **Half-maximum**: measure the plateaus (an ROI per tissue, or *Plateaus from the
   segments*), then press a border to set the window level to its threshold, width 50 HU.
   Draw where the image turns from white to black.
4. **Submit read**. Values outside 0-4, overlapping classes or an empty class are refused
   before upload. The server runs the automatic check; *Refresh status* shows whether it
   accepted the read or returned it with reasons.

Not SegQueue14: its own module, settings (`JanusMRead/...`), cache (`~/.janusm-read`),
archive (`JanusMRead-<v>-Slicer-<x.y>.zip`, built by `slicer/build-extension-janusm.py`)
and release tag (`janusm-read-v<v>`).

Tests: `pytest tests/test_janusm_read_module.py` and, inside Slicer,
`tests/slicer_selftest_janusm.py`.
