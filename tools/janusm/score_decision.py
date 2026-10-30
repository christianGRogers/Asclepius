"""Score Janus-M 0 on the decision set: the one lead-run decision scorer (R4-S23, JA62; issue #215).

Round 4 rest-ccta ruling (``vault/JanusM/Judgements/Round 4 - rest-ccta.md`` on ``jm/rest-ccta``),
JA62, implementing JA8's d, JA37's transfer check, JA39 and JA42's input. This is the **only** code
that opens decision reads.

**It never runs outside a Fir Slurm job.** Run without ``--run`` it prints the lead's commands and
exits. With ``--run`` and no ``SLURM_JOB_ID`` it refuses before reading anything.

**Guard first** (every step before any image, mask, label or read file is opened; any error stops
the run and nothing is written):

1. ``janusm.guard.refuse(decision, purpose="decision_scoring")`` on the decision list of
   ``configs/janusm/sealed-r1.json`` (loaded through :func:`janusm.sealed_r1.load`, so its hash is
   checked);
2. the same guard call on every case named in the export manifests (``--manifest``, written by
   ``janusm-export``); a seal or seal-extension case, or any coronary hold-out, is refused;
3. an explicit JM-0 refusal (the guard does not hold ``jm0``), then every manifest case must be a
   decision case.

**Order.** Cases are taken in the **list order** of ``sealed-r1.json``'s ``decision`` (not the set
:func:`janusm.sealed_r1.load` returns). A case counts only with exactly two accepted reads under
``border_protocol: 1``; third reads are dropped (JA47: they are for rule 2 only). So ``reads[:20]``
are the first 20 complete decision cases in that order.

**Read 1 and read 2** are fixed per reader: the read whose reader has the smaller stable key
(sha256 of a fixed salt and the reader id) is read 1. The key and the reader id are never written.

**Per case:** :func:`janusm.features.case_features` on each read with **one** reference coronary
tree (the same array) for both; :func:`janusm.harness.compare` with ``roi="ja37"`` for
model-vs-read 1, model-vs-read 2 and read-vs-read (reference read 1, JA61). JA8's d per border is
the mean over the two reads of the model-vs-read pp ASSD minus the read-vs-read pp ASSD (JA39). The
1.0 mm ASSD guard is reported on each model-vs-read pp ASSD; the voxel ASSD is reported beside.

**Transfer check** (JA37, JA62): ``harness.transfer_check`` on the first 20 complete cases, once
for each comparison (model-vs-read 1, model-vs-read 2, read-vs-read). The guard is 0.5 mm if any of
the three fails, else 0.3 mm, and never below ``harness.BIAS_GUARD_VALIDATED_MM`` (JA61's
open-base check; 0.3 mm since JA71 passed, R5-S3). Fewer than 20 complete cases is an error, never a
default. The count of cases over the limit is reported; no id is.

**Output.** One anonymous JSON (``reads``, ``assd_pp``, ``transfer_check`` and the versions),
refused by :func:`janusm.reference.assert_anonymous` if any id appears, and its sha256.
``tools/janusm/build_reference.py --reads`` takes it as the decision read records.

    python tools/janusm/score_decision.py                 # prints the Fir commands
    python tools/janusm/score_decision.py --run ...       # inside a Fir Slurm job only

**Depends on R4-S4 and R4-S5 (#212):** ``harness.ja37_band`` and ``harness.transfer_check``. Until
they are on ``dev`` a ``--run`` refuses before anything is opened.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Tuple

REPO = Path(__file__).resolve().parents[2]
if str(REPO / "src") not in sys.path:
    sys.path.insert(0, str(REPO / "src"))
from janusm import features as F  # noqa: E402
from janusm import guard as guard  # noqa: E402
from janusm import harness as H  # noqa: E402
from janusm import reference as R  # noqa: E402
from janusm import sealed_r1 as sealed_r1  # noqa: E402

SCORE_VERSION = "1.0.0"
PURPOSE = guard.DECISION_SCORING
BORDER_PROTOCOL = 1
SOURCE = guard.ICX_SOURCE
N_TRANSFER = 20                         # JA37 / JA62: the first 20 complete decision cases
ROI = "ja37"
ASSD_GUARD_MM = 1.0                     # JA8 / JA16
BORDERS = ("endo", "epi")
COMPARISONS = ("model_vs_read_1", "model_vs_read_2", "read_vs_read")
#: compare() keys written per comparison (numbers only; no id).
KEEP = tuple(f"{m}_{b}" for b in BORDERS
             for m in ("assd_pp", "assd_voxel", "bias", "bias_pp", "mean_abs_d")) + (
    "thick_err_median_mm", "thick_bias_median_mm", "n_segments", "dice_myo", "aha_failed", "sta")
_READER_SALT = "asclepius-janusm-reader-order-r1:"
JM0R = REPO / "experiments/JanusM/fir/jm0r_readout.py"

FIR_COMMAND = r"""# Janus-M decision scoring (R4-S23, JA62; #215). Lead only, on Fir (def-aso22).
# Run AFTER the LQ12 seeding job has written Janus-M 0 masks for the decision cases and the read
# waves are exported (janusm-export --out $SCRATCH/janusm/waveN ...). CPU only, 0 GPU-h.
module load StdEnv/2023 python/3.11.5
cd $SCRATCH/asclepius/repo && git fetch origin dev && git checkout dev && git pull --ff-only
sbatch --account=def-aso22 --job-name=jm-decision --cpus-per-task=4 --mem=32G --time=08:00:00 \
    --output=$SCRATCH/janusm/jm-decision-%j.log \
    --wrap "source $HOME/icx4-tseg-venv/bin/activate && \
    python tools/janusm/score_decision.py --run \
    --manifest $SCRATCH/janusm/wave1/manifest.json \
    --manifest $SCRATCH/janusm/wave2/manifest.json \
    --hc $SCRATCH/janusm/hc_decision --layout $SCRATCH/icx4/layout.json --icx $SCRATCH/icx4/icx \
    --out $SCRATCH/janusm/decision_read_features.json"

# when it ends: the guard line, then the transfer verdict and the sha256 (no case id anywhere)
grep -m1 '^guard:' $SCRATCH/janusm/jm-decision-*.log
python -c "import json; d=json.load(open('$SCRATCH/janusm/decision_read_features.json')); \
print(json.dumps(d['transfer_check'], indent=1)); print(d['n_cases'], 'cases')"
sha256sum $SCRATCH/janusm/decision_read_features.json
# Send back on #215: the transfer_check block, n_cases and the sha256. The JSON itself feeds
# build_reference.py --reads on Fir. If the guard line says REFUSED, send only that line:
# nothing was opened.
"""


class ScoreError(RuntimeError):
    """The decision scorer refuses its inputs or its environment."""


# ------------------------------------------------------------------------------------ guard
def decision_order(path=None) -> List[str]:
    """The decision cases in ``sealed-r1.json``'s list order, after the pinned-hash check."""
    p = Path(path) if path else REPO / sealed_r1.PATH
    sealed_r1.load(p)  # hash and overlap checks; a changed file raises
    return list(json.loads(p.read_text())["decision"])


def guard_cases(names: Iterable[str], order: Sequence[str], *, sealed_path=None,
                root=None) -> List[str]:
    """Steps 1-3 of the guard. Returns ``names``; raises before anything is opened."""
    names = list(names)
    guard.refuse(order, what="the Janus-M decision list", source=SOURCE, purpose=PURPOSE,
                 root=root)
    guard.refuse(names, what="the decision read manifests", source=SOURCE, purpose=PURPOSE,
                 root=root)
    p = Path(sealed_path) if sealed_path else REPO / sealed_r1.PATH
    jm0 = set(json.loads(p.read_text())["jm0"])
    hit = [n for n in names if n in jm0]
    if hit:
        raise guard.HeldOutError(f"REFUSING the decision read manifests: {len(hit)} JM-0 case(s)")
    outside = [n for n in names if n not in set(order)]
    if outside:
        raise guard.HeldOutError(
            f"REFUSING the decision read manifests: {len(outside)} case(s) are not decision cases")
    return names


def harness_api() -> Tuple[Callable, Callable]:
    """``(compare, transfer_check)`` from the harness; refuses if R4-S4 / R4-S5 are missing."""
    missing = [n for n in ("ja37_band", "transfer_check") if not hasattr(H, n)]
    if missing:
        raise ScoreError(f"janusm.harness lacks {', '.join(missing)} (R4-S4/R4-S5, #212); "
                         "decision scoring needs JA37's band and the transfer check")
    return H.compare, H.transfer_check


# ------------------------------------------------------------------------------------ order
def reader_key(reader) -> str:
    """The stable per-reader key that fixes read 1 and read 2. Never written out."""
    return hashlib.sha256((_READER_SALT + str(reader)).encode()).hexdigest()


def manifest_rows(manifests: Iterable[Tuple[Path, dict]]) -> Dict[str, dict]:
    """case -> row, with each read's path resolved against its manifest's folder."""
    rows: Dict[str, dict] = {}
    for base, m in manifests:
        if m.get("border_protocol") not in (None, BORDER_PROTOCOL):
            raise ScoreError(f"a manifest is border protocol {m.get('border_protocol')!r}, "
                             f"not {BORDER_PROTOCOL}")
        for row in m.get("cases", []):
            c = row["case"]
            if c in rows:
                raise ScoreError("a case appears in two manifests")
            rows[c] = {**row, "_base": str(base)}
    return rows


def select_pairs(order: Sequence[str], rows: Dict[str, dict]) -> List[Tuple[str, list]]:
    """``[(case, [read 1, read 2])]`` in decision-list order, each read ``{"path", "reader"}``.

    Only the two non-third reads with ``border_protocol == 1`` count; a case without exactly two
    is skipped. Read 1 is the read whose reader has the smaller :func:`reader_key`."""
    out = []
    for case in order:
        row = rows.get(case)
        if row is None:
            continue
        reads = []
        for path, rec in zip(row.get("reads", []), row.get("readRecords", [])):
            if rec.get("third") or rec.get("border_protocol") != BORDER_PROTOCOL:
                continue
            reads.append({"path": str(Path(row["_base"]) / path), "reader": rec["reader"]})
        if len(reads) != 2:
            continue
        if reads[0]["reader"] == reads[1]["reader"]:
            raise ScoreError("a decision case has two reads by one reader")
        reads.sort(key=lambda r: reader_key(r["reader"]))
        out.append((case, reads))
    return out


# ------------------------------------------------------------------------------------ score
def _keep(row: dict) -> dict:
    return {k: row[k] for k in KEEP if k in row}


def score_case(model, read_1, read_2, ct, affine, coronary, *, compare: Callable,
               features_fn: Callable = F.case_features, guard_mm: float = F.DEFAULT_GUARD_MM
               ) -> Tuple[dict, dict]:
    """One case: (read record, assd_pp row). ``coronary`` is the one reference tree, passed as
    the same object to both reads' features."""
    rec = {"read_1": features_fn(read_1, ct, affine, coronary, guard_mm=guard_mm),
           "read_2": features_fn(read_2, ct, affine, coronary, guard_mm=guard_mm)}
    c = {"model_vs_read_1": compare(read_1, model, affine=affine, roi=ROI),
         "model_vs_read_2": compare(read_2, model, affine=affine, roi=ROI),
         "read_vs_read": compare(read_1, read_2, affine=affine, roi=ROI)}
    row = {k: _keep(v) for k, v in c.items()}
    for b in BORDERS:
        mv = [c["model_vs_read_1"][f"assd_pp_{b}"], c["model_vs_read_2"][f"assd_pp_{b}"]]
        row[f"d_{b}"] = (mv[0] + mv[1]) / 2.0 - c["read_vs_read"][f"assd_pp_{b}"]
        row[f"assd_guard_pass_{b}"] = bool(max(mv) <= ASSD_GUARD_MM)
    return rec, row


def transfer(rows: List[dict], transfer_fn: Callable) -> dict:
    """JA37's check on the first 20 complete cases, per comparison; the guard is the worst."""
    if len(rows) < N_TRANSFER:
        raise ScoreError(f"the transfer check needs {N_TRANSFER} complete decision cases; "
                         f"{len(rows)} have two accepted border-protocol-1 reads")
    out = {k: transfer_fn([r[k] for r in rows[:N_TRANSFER]], n_first=N_TRANSFER)
           for k in COMPARISONS}
    guards = [float(v["bias_guard_mm"]) for v in out.values()]
    out["passed"] = all(bool(v["passed"]) for v in out.values())
    # the guard in force is the worse of the transfer check's and JA61's open-base check's
    out["transfer_bias_guard_mm"] = max(guards)
    out["open_base_bias_guard_mm"] = float(H.BIAS_GUARD_VALIDATED_MM)
    out["bias_guard_mm"] = max(guards + [float(H.BIAS_GUARD_VALIDATED_MM)])
    out["n_cases"] = N_TRANSFER
    return out


def score(items: Iterable[Callable[[], tuple]], *, compare: Callable, transfer_fn: Callable,
          features_fn: Callable = F.case_features, guard_mm: float = F.DEFAULT_GUARD_MM,
          sealed_sha256: Optional[str] = None, log=None) -> dict:
    """The output from loaders in decision order. Each item, called, returns
    ``(model, read_1, read_2, ct, affine, coronary)``; no id reaches this function."""
    reads, rows = [], []
    for i, load in enumerate(items, 1):
        model, r1, r2, ct, aff, cor = load()
        rec, row = score_case(model, r1, r2, ct, aff, cor, compare=compare,
                              features_fn=features_fn, guard_mm=guard_mm)
        reads.append(rec)
        rows.append(row)
        if log:
            log(f"case {i} scored")
    out = {
        "what": "Janus-M decision scoring (JA62): anonymous read records, JA8's d and JA37's "
                "transfer check, in sealed-r1.json decision order. No case id.",
        "score_decision_version": SCORE_VERSION,
        "features_version": F.FEATURES_VERSION,
        "harness_version": H.HARNESS_VERSION,
        "guard_mm": float(guard_mm),
        "roi": ROI,
        "border_protocol": BORDER_PROTOCOL,
        "sealed_r1_sha256": sealed_sha256,
        "n_cases": len(reads),
        "transfer_check": transfer(rows, transfer_fn),
        "reads": reads,
        "assd_pp": rows,
    }
    R.assert_anonymous(out, "the decision scoring output")
    return out


def dumps(out: dict) -> str:
    R.assert_anonymous(out, "the decision scoring output")
    return json.dumps(out, indent=1, sort_keys=True, allow_nan=True) + "\n"


# ------------------------------------------------------------------------------------ I/O (Fir)
def _jm0r():
    """JM-0R's loader helpers (mask -> JA1 labels, crop, coronary name), imported, not copied."""
    spec = importlib.util.spec_from_file_location("jm0r_readout", JM0R)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _loader(case, reads, hc_dir, ct_path, icx_dir, m, ids):
    """A thunk that opens one case's model mask, two reads, CT and coronary label."""

    def load():
        import nibabel as nib
        import numpy as np
        from territory import to_four

        from janusm import geometry as G

        def canon(p):
            return nib.as_closest_canonical(nib.load(str(p)))

        hi = canon(Path(hc_dir) / f"{case}.nii.gz")
        others = [canon(ct_path), canon(Path(icx_dir) / m.icx_label_name(case))]
        others += [canon(r["path"]) for r in reads]
        for o in others:
            if o.shape != hi.shape or not np.allclose(o.affine, hi.affine, atol=1e-3):
                raise ValueError("grid mismatch")
        model, _aorta, _other = m.to_ja1(np.asarray(hi.dataobj).astype(np.int16), ids)
        sp = np.asarray(hi.header.get_zooms()[:3], float)
        cor = to_four(np.asarray(others[1].dataobj).astype(np.int64), sp).astype(np.int16)
        ct = np.asarray(others[0].dataobj, dtype=np.float32)
        r1, r2 = (np.asarray(o.dataobj).astype(np.int16) for o in others[2:])
        for r in (r1, r2):
            if not set(np.unique(r).tolist()) <= {0, 1, 2, 3, 4}:
                raise ValueError("a read carries a label outside JA1")
        roi = np.zeros(model.shape, bool)
        for lab in (model, r1, r2):
            roi |= np.isin(lab, (G.MYO, G.LV))
        (model, r1, r2, ct, cor), aff = m.crop([model, r1, r2, ct, cor], roi, hi.affine)
        return model, r1, r2, ct, aff, cor

    return load


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--run", action="store_true", help="score (inside a Fir Slurm job only)")
    ap.add_argument("--manifest", action="append", default=None,
                    help="a janusm-export manifest.json (repeat per wave)")
    for k in ("hc", "layout", "icx", "out"):
        ap.add_argument("--" + k)
    ap.add_argument("--guard-mm", type=float, default=F.DEFAULT_GUARD_MM)
    a = ap.parse_args(argv)
    if not a.run:
        print(FIR_COMMAND)
        return 0
    if not os.environ.get("SLURM_JOB_ID"):
        print("REFUSED: --run only inside a Fir Slurm job (no SLURM_JOB_ID). Nothing was "
              "opened. Run without --run for the lead's commands.", file=sys.stderr)
        return 3
    missing = [k for k in ("manifest", "hc", "layout", "icx", "out") if getattr(a, k) is None]
    if missing:
        ap.error("--run needs " + ", ".join("--" + k for k in missing))
    try:  # before any image, mask, label or read file
        compare, transfer_fn = harness_api()
        order = decision_order()
        manifests = [(Path(p).parent, json.loads(Path(p).read_text())) for p in a.manifest]
        rows = manifest_rows(manifests)
        guard_cases(rows, order)
        pairs = select_pairs(order, rows)
        if len(pairs) < N_TRANSFER:
            raise ScoreError(f"{len(pairs)} complete decision cases; the transfer check needs "
                             f"{N_TRANSFER}")
    except Exception as e:  # noqa: BLE001 -- HeldOutError, ScoreError, I/O: all refuse
        first = str(e).splitlines()[0] if str(e) else ""
        print(f"REFUSED: {type(e).__name__}: {first}. Nothing was opened.", file=sys.stderr)
        return 3
    print(f"guard: {len(rows)} manifest cases, all decision cases, 0 refused (janusm.guard "
          f"purpose={PURPOSE}; JM-0 refused); {len(pairs)} complete", file=sys.stderr, flush=True)
    m = _jm0r()
    ids = m.hc_ids()
    layout = json.loads(Path(a.layout).read_text())["cases"]
    items = [_loader(c, reads, a.hc, layout[c]["ct"], a.icx, m, ids) for c, reads in pairs]
    out = score(items, compare=compare, transfer_fn=transfer_fn, guard_mm=a.guard_mm,
                sealed_sha256=sealed_r1.SEALED_R1_SHA256,
                log=lambda s: print(s, file=sys.stderr, flush=True))
    text = dumps(out)
    Path(a.out).write_text(text)
    sha = hashlib.sha256(text.encode()).hexdigest()
    Path(str(a.out) + ".sha256").write_text(f"{sha}  {Path(a.out).name}\n")
    print(f"sha256 {sha}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
