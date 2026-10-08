# crucible — training on two reads per case (decision D2)

Six equal-step arms: `single`, `both`, `a11` (Round-3 A11 hybrid), `agree`, `union`, `oracle`.

```sh
cd <root>/experiments/crucible && ./crucible        # login node; builds venv, fetches ImageCAS-X labels, submits 1 job
./crucible status                                    # optional: queue state + stage markers
./crucible collect                                   # optional: copy $SCRATCH/crucible_2reads/results here
```

- **One job:** 1 × H100, `--time=23:55:00`, `--account=def-aso22` (`ACCOUNT=` overrides). It is submitted from the GPU
  login node; the script hops to `trig-login01` via ssh if started elsewhere.
- **Cases:** found by walking up to the first `cases/`. Both the ImageCAS layout (`<id>.img.nii.gz` +
  `<id>.label.nii.gz`) and the Girder layout (`c0000/ct.nii.gz` + `c0000/coronary_arteries.nii.gz`) work, and the
  detected layout is printed.
- **Internet, login node only:** pip (Alliance wheelhouse first), plus one ~13.5 MB range request to Zenodo
  10.5281/zenodo.21887809 for the ImageCAS-X names.
- **State:** everything lives in `$SCRATCH/crucible_2reads/`, and every stage has a marker. Re-running resumes, and
  never submits while a `crucible_2reads` job is queued or running. If the deadline stops an arm, a re-run resumes it
  from its checkpoint, at extra GPU time; ask first.
- **Results:** `results/SUMMARY.md`, `results.json`, `logs/` (< 1 MB, no weights).
- **What it does and the decision rule:** `vault/Plans/Experiments/Crucible - GPU experiment on training with two reads per case (pending).md`.
- **Tested on CPU** with `CRUCIBLE_SMOKE=1` (4 train / 2 test cases, tiny patch, 1 epoch): the driver ran end to end
  (prep → plan → preprocess → 6 arms, including the judge's A11 hybrid → predict → eval → SUMMARY; also resumed correctly after an arm was killed mid-run). `./crucible dryrun` was run on fake `cases/` trees
  in both layouts.
