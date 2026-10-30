"""Build ``configs/janusm/reference-r1.json``: the Janus-M reference population (S6, issue #196).

Round 3 rest-ccta ruling (``vault/JanusM/Judgements/Round 3 - rest-ccta.md`` on ``jm/rest-ccta``):
Hotel v3 §4.1 as amended by JA41 (gates), JA42 (RC) and JA48. The computation is in
:mod:`janusm.reference`; this script is the guarded job around it.

**It never runs outside a Fir Slurm job**, and only after the lead's LQ12 seeding job has produced
Janus-M 0's masks on the reference cases. Run without ``--run`` it prints the commands for the
lead and exits.

Guard, before any image, mask, label, layout or read file is opened (any error stops the run):

1. the case list must equal the derived reference population: ``splits.json`` train minus every
   list in ``configs/janusm/sealed-r1.json`` (seal, seal extension, decision, JM-0); 360 cases;
2. ``janusm.guard.refuse(cases, purpose="any")`` (refuses seal, extension and decision cases and
   every coronary hold-out), then an explicit JM-0 refusal (the guard does not hold ``jm0``);
3. the operator's ``splits.json`` must hash to the guard's pin (JA6).

Inputs: the case list; Janus-M 0's ``heartchambers_highres`` masks; the CT (``layout.json``); the
ImageCAS-X reference coronary labels; the anonymous read records of the decision cases
(``--reads``: the output of ``tools/janusm/score_decision.py``,
``{"reads": [{"read_1": features, "read_2": features}, ...], ...}`` in draw order, the outputs of
:func:`janusm.features.case_features` on the two accepted reads; no id; refused if any id
appears, or if its ``features_version`` or ``guard_mm`` differs from this run's); and three
verdicts of the JA43 decision script (R5 rest TPR gate, R7 septal-arc column, R2 halves note).

Outputs: the config (``--out``; no case id, the sorted list's sha256 only) and
``OUT.cases.jsonl`` beside it, per-case features with ids, which **stays on Fir**.

    python tools/janusm/build_reference.py                 # prints the Fir commands
    python tools/janusm/build_reference.py --run ...       # inside a Fir Slurm job only

Then commit the config by PR and pin its sha256 in ``janusm.guard.REFERENCE_SHA256``.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))
from janusm import features as F  # noqa: E402
from janusm import reference as R  # noqa: E402

JM0R = REPO / "experiments/JanusM/fir/jm0r_readout.py"
MODEL = "heartchambers_highres (Janus-M 0) + janusm.geometry"

FIR_COMMAND = r"""# Janus-M S6 reference population (issue #196). Lead only, on Fir (def-aso22).
# Run AFTER the LQ12 seeding job has written Janus-M 0 masks for the reference cases, and after
# the decision-scoring path has written the anonymous read records. CPU only, 0 GPU-h.
module load StdEnv/2023 python/3.11.5
cd $SCRATCH/asclepius/repo && git fetch origin dev && git checkout dev && git pull --ff-only
python -c "import sys; sys.path.insert(0, 'src'); from janusm import reference as R; \
print('\n'.join(R.derive_cases()))" > $SCRATCH/janusm/reference_cases.txt
wc -l $SCRATCH/janusm/reference_cases.txt          # must print 360
sbatch --account=def-aso22 --job-name=jm-ref --cpus-per-task=8 --mem=48G --time=08:00:00 \
    --output=$SCRATCH/janusm/jm-ref-%j.log --wrap "source $HOME/icx4-tseg-venv/bin/activate && \
    python tools/janusm/build_reference.py --run \
    --cases $SCRATCH/janusm/reference_cases.txt --hc $SCRATCH/janusm/hc_ref \
    --layout $SCRATCH/icx4/layout.json --icx $SCRATCH/icx4/icx --splits $SCRATCH/icx4/splits.json \
    --reads $SCRATCH/janusm/decision_read_features.json \
    --rest-tpr-gate <R5: pass|fail|not_evaluable> --septal-arc-column <R7: keep|drop> \
    --halves-note <R2: yes|no> --out $SCRATCH/janusm/reference-r1.json --np 8"

# when it ends: the guard line, then the config (aggregates only, no case id)
grep -m1 '^guard:' $SCRATCH/janusm/jm-ref-*.log
cat $SCRATCH/janusm/reference-r1.json
sha256sum $SCRATCH/janusm/reference-r1.json
# Send back on #196: reference-r1.json and its sha256 only. reference-r1.json.cases.jsonl and the
# log stay on Fir. If the guard line says REFUSED, send only that line: nothing was opened.
"""


def _jm0r():
    """JM-0R's loader (mask -> JA1 labels, CT, coronary), imported, not copied."""
    spec = importlib.util.spec_from_file_location("jm0r_readout", JM0R)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _features_one(job):
    case, hc_dir, ct_path, icx_dir, ids, guard_mm = job
    t0 = time.time()
    try:
        m = _jm0r()
        lab, ct, aff, cor, _aorta, _other = m.load_case(case, hc_dir, ct_path, icx_dir, ids)
        r = F.case_features(lab, ct, aff, cor, guard_mm=guard_mm)
    except Exception as e:  # noqa: BLE001 -- the type only: a message can carry a path
        r = {"error": type(e).__name__, "frame": "error"}
    r["seconds"] = round(time.time() - t0, 1)
    return r


def load_decision_reads(obj, guard_mm: float = F.DEFAULT_GUARD_MM) -> list:
    """The decision read records from ``tools/janusm/score_decision.py``'s output (a path or the
    loaded dict). Refuses an output with an id, or whose ``features_version`` or ``guard_mm``
    (at the top or on any read) differs from this run's: the reads and the reference population
    must be measured by one feature code at one guard band."""
    d = obj if isinstance(obj, dict) else json.loads(Path(obj).read_text())
    R.assert_anonymous(d, "--reads")
    reads = d["reads"]
    recs = [d] + [r[k] for r in reads for k in ("read_1", "read_2")]
    for r in recs:
        if r.get("features_version") != F.FEATURES_VERSION:
            raise R.ReferenceError(
                f"--reads: features_version {r.get('features_version')!r} is not this "
                f"code's {F.FEATURES_VERSION!r}; rescore the decision reads")
        if r.get("guard_mm") is None or abs(float(r["guard_mm"]) - float(guard_mm)) > 1e-9:
            raise R.ReferenceError(
                f"--reads: guard_mm {r.get('guard_mm')!r} is not this run's {guard_mm}")
    return reads


def build(cases, feats, reads, *, rest_tpr_gate, septal_arc_column, halves_note,
          guard_mm=F.DEFAULT_GUARD_MM, seed=R.SEED) -> dict:
    """The config from already-measured features. ``cases`` has passed :func:`R.refuse_cases`."""
    return R.build_config(
        feats, reads, cases_sha=R.cases_sha256(cases), n_cases=len(cases),
        rest_tpr_gate=rest_tpr_gate, septal_arc_column=septal_arc_column,
        halves_note=halves_note, model=MODEL, guard_mm=guard_mm, seed=seed)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--run", action="store_true", help="build (inside a Fir Slurm job only)")
    for k in ("cases", "hc", "layout", "icx", "splits", "reads", "out"):
        ap.add_argument("--" + k)
    ap.add_argument("--rest-tpr-gate", choices=("pass", "fail", "not_evaluable"))
    ap.add_argument("--septal-arc-column", choices=("keep", "drop"))
    ap.add_argument("--halves-note", choices=("yes", "no"))
    ap.add_argument("--guard-mm", type=float, default=F.DEFAULT_GUARD_MM)
    ap.add_argument("--np", type=int, default=8)
    a = ap.parse_args(argv)
    if not a.run:
        print(FIR_COMMAND)
        return 0
    if not os.environ.get("SLURM_JOB_ID"):
        print("REFUSED: --run only inside a Fir Slurm job (no SLURM_JOB_ID). Nothing was "
              "opened. Run without --run for the lead's commands.", file=sys.stderr)
        return 3
    missing = [k for k in ("cases", "hc", "layout", "icx", "splits", "reads", "out",
                           "rest_tpr_gate", "septal_arc_column", "halves_note")
               if getattr(a, k) is None]
    if missing:
        ap.error("--run needs " + ", ".join("--" + m.replace("_", "-") for m in missing))
    try:  # before any image, mask, label, layout or read file
        cases = R.refuse_cases(Path(a.cases).read_text().split(), splits_path=a.splits)
    except Exception as e:  # noqa: BLE001 -- HeldOutError, ReferenceError, I/O: all refuse
        first = str(e).splitlines()[0] if str(e) else ""
        print(f"REFUSED: {type(e).__name__}: {first}. Nothing was opened.", file=sys.stderr)
        return 3
    print(f"guard: {len(cases)} cases, the derived reference population, 0 refused "
          "(janusm.guard purpose=any; JM-0 refused; splits.json hash ok)", file=sys.stderr,
          flush=True)
    try:
        reads = load_decision_reads(a.reads, a.guard_mm)
    except R.ReferenceError as e:
        print(f"REFUSED: {e}", file=sys.stderr)
        return 3
    m = _jm0r()
    layout = json.loads(Path(a.layout).read_text())["cases"]
    ids = m.hc_ids()
    jobs = [(c, a.hc, layout[c]["ct"], a.icx, ids, a.guard_mm) for c in cases]
    out = Path(a.out)
    feats = []
    if a.np > 1:
        from multiprocessing import Pool

        pool = Pool(a.np)
        it = pool.imap(_features_one, jobs)
    else:
        pool, it = None, map(_features_one, jobs)
    try:
        with open(str(out) + ".cases.jsonl", "w") as fh:  # per-case rows: stay on Fir
            for i, (c, r) in enumerate(zip(cases, it), 1):
                fh.write(json.dumps({"id": c, **r}) + "\n")
                feats.append(r)
                print(f"case {i}/{len(cases)} {r.get('frame')} {r['seconds']}s",
                      file=sys.stderr, flush=True)
    finally:
        if pool is not None:
            pool.close()
            pool.join()
    for r in feats:
        r.pop("seconds", None)
    cfg = build(cases, feats, reads, rest_tpr_gate=a.rest_tpr_gate,
                septal_arc_column=a.septal_arc_column == "keep",
                halves_note=a.halves_note == "yes", guard_mm=a.guard_mm)
    text = R.dumps(cfg)
    out.write_text(text)
    print(text, end="")
    print(f"sha256 {hashlib.sha256(text.encode()).hexdigest()}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
