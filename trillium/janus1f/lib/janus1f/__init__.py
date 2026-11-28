"""Janus 1-F stage 1 (J1F-A) launcher library (#392; master plan `vault/Plans/Master plan - Janus 1-F.md` §5).

The spec is Delta v3 §4 as amended by F-A27 to F-A35 ([[Janus 1-F Round 3]] F-A36). Modules:

  pins       the hashes of record (scorer, gates, labels.py, tf1.py, Step T's plans and fingerprint, the split) and
             the refusals on a mismatch
  split      the pinned 620 / 100 split, the sealed and locked guards, the fit-check 20, `splits_final.json`
  parents    the parent copy of Janus 0's output heads into 13 (configs/janus1/j1f_parents.json)
  decode     F, T and G (F-A19, F-A31), the chunked decode-and-delete with its marker, collect's marker check
  plans      L-A21's plans check pinned to Step T (Delta v3 plans_check.py)
  dataset    `prep`: Dataset719_J1F = the 620 only, ignore 13 on disk, F0-r2's converter line
  ledger     the looks ledger (F-A22: at most two looks in the track; J1F-A once)
  verdict    V (track 1-L's H1 rule), the verdict table (F-A6, F-A32)
  sbatch     the Fir headers (F-A34), the one place they are written
  collect    `collect`: ledger first, V on F, B on F and T (and T_L), the verdict, results/
  selftest   every self-test `check` runs; each fails on a broken fixture first

Standard library + numpy (+ scipy/scikit-image through the scorer). No module here reads a volume at import.
"""
