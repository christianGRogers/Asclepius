# Watching training in Slicer

Moved out of the README, which now covers the training method only.

1. Slicer → **Edit → Application Settings → Modules**, drag
   `slicer/SegmentatorTrainMonitor` into **Additional module paths**, restart.
2. Open **Segmentation → Segmentator Train Monitor**.
3. Point it at a run directory — a local path, or
   `you@trillium.alliancecan.ca:/scratch/g/grp/you/runs/Dataset710_Coronary__fold0`,
   optionally with an **SSH key** if `~/.ssh/config` does not already name one.

`segtrain scinet submit` prints the exact `host:path` to paste.

The run directory lives on `$SCRATCH`, which the login nodes share with the
compute nodes, so the monitor reads the live file while the job writes it —
there is no staging step and nothing to synchronise. Setting up `ControlMaster`
for the host in `~/.ssh/config` is worth the two lines: the monitor polls every
ten seconds, and Toronto is several hundred milliseconds of handshake away.

You get loss and pseudo-Dice curves, a per-structure Dice table sorted weakest
first, and the live model's segmentation of a **held-out** case loaded over the
CT in the 3D view — with an epoch slider, so you can watch a structure sharpen,
or catch a vertebra label sliding by one.

Per-structure Dice in the table comes from the preview daemon scoring real
held-out cases. nnU-Net's own pseudo-Dice is computed on training patches and
reads far too high early on; it is shown on the curve but is not what the table
reports once previews exist.

No pip installs into Slicer's Python: the module imports the stdlib-only
`segtrain.events` from `src/`, and shells out to the system `ssh`/`scp`.

Verify the module against a finished run:

```bash
"…/Slicer.exe" --no-splash --python-script tests/slicer_selftest.py \
    --run-dir /data/runs/Dataset710_Coronary__fold0
```

---
