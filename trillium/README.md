# Trillium experiments from the plan tournament

Each advocate in the plan tournament (`vault/Plans/`) gets one GPU experiment
on SciNet Trillium. This folder holds them, one sub-folder per advocate. The
project lead copies them next to the case data, runs one command each, and
returns the results.

## The contract (every experiment follows it)

Layout on Trillium:

```
<root>/
  cases/            # the 1000 cases, provided by the project lead (see "Case data")
  experiments/
    atlas/          # = trillium/atlas/ from this repo
      atlas         # the single entry point (executable)
    bridge/   bridge
    crucible/ crucible
    delta/    delta
```

Run with nothing else:

```sh
cd <root>/experiments/atlas && ./atlas
```

Rules for the entry point `./<name>`:

1. **One command, no arguments, no editing.** It runs on a **login node**: it
   prepares the environment, fetches anything it needs from the internet
   (compute nodes have none), stages data to `$SCRATCH`, and submits the GPU
   job(s) with `sbatch`. It then exits and prints the job ids and where results
   will appear.
2. **Finds the cases itself**: walks up from its own directory to the first
   parent that has a `cases/` directory. `CASES=/path ./atlas` overrides, but
   must never be needed. Fails loudly, listing what it found, if the layout is
   not recognised.
3. **Re-runnable**: running it again resumes or skips finished steps, never
   duplicates a running job (check `squeue -u $USER --name ...`).
4. **Writes under `$SCRATCH` only** (compute nodes cannot write `$HOME` or
   `$PROJECT`). The venv lives in `$HOME` and is built on the login node.
5. **Results** land in `<root>/experiments/<name>/results/` (or a printed
   `$SCRATCH` path, copied back at the end): a `SUMMARY.md` with the numbers and
   what they mean, a machine-readable `results.json`, and the SLURM logs. Keep
   it small (< 50 MB, no model weights, no volumes) so it can be sent back as is.
   `./<name> status` and `./<name> collect` are allowed as optional extras.
6. **Budget**: at most **one H100 for 24 h of walltime in total** per experiment
   (a job chain is allowed within that), unless the project lead says otherwise.
7. **Never** writes to Girder, never needs a password or token typed in, never
   commits anything.

## Case data

What `cases/` contains is the project lead's choice; the entry point must
accept the ImageCAS release layout (`<id>.img.nii.gz` + `<id>.label.nii.gz` in
one directory) and the Girder export layout (`<case>/ct.nii.gz` +
`<case>/coronary_arteries.nii.gz`), map them to the tournament's case ids
(ImageCAS id `n` = tournament case `c{n-1:04d}`, see
`vault/Plans/Experiments/Crucible - ImageCAS-X is real and its 800 cases are our cases c(id-1).md`),
and print which layout it detected. Four-class team labels do not exist yet;
any experiment needing per-branch labels derives them (e.g. ImageCAS-X names
projected onto the ImageCAS mask, fetched on the login node from Zenodo).

## Trillium facts

- **SLURM account: `def-aso22`** (user `croger`; the only allocation, from `sshare -U`). Pass `--account=def-aso22`; an `ACCOUNT=` override is allowed but must never be needed.


Read the Alliance Trillium documentation (docs.alliancecan.ca, "Trillium" and
"Trillium Quickstart") rather than trusting memory; the repo's
`src/segtrain/slurm.py` and `docs/TRAINING-PHASE1.md` hold what was already
learned (paths under `$SCRATCH`, venv in `$HOME`, account required).
