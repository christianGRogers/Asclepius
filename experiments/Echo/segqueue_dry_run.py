"""A21 dry run: a SegQueue export through `segtrain index -> convert -> splits -> reads-report`.

No approved four-class export exists yet, so this builds the closest stand-in there is from the
two real SegQueue test submissions (binary, LPS, z running downwards, named imagecas_NNNN):

  read 1  = the real submission's voxels, named by projecting ImageCAS-X's per-branch labels onto
            them (segtrain.proxy.project_names; the same as a proxy, but on the submitted voxels);
  read 2  = read 1 with a synthetic annotator habit: the LM end moved ~3 mm distally into the LAD;

each written back onto the SUBMISSION's own grid and exported with the real exporter's own
helpers (server/girder_segqueue/export.py: splitLabels, _writeMask; DEFAULT_SEGMENTS from
settings.py), in the layout `segqueue-export --replicas all` writes:
  <export>/imagecas_NNNN/ct.nii.gz, <export>/imagecas_NNNN/segmentations/<vessel>.nii.gz,
  <export>/imagecas_NNNN__r2/...
Two decoys test A14: a copy of an open case renamed imagecas_0003 (= c0002, sealed; no sealed
data is read) and one with an unmappable name.

To run a REAL export instead, pass --export <dir> (the build step is skipped).

  python3 experiments/Echo/segqueue_dry_run.py <workdir> [--export DIR] [--fast]

--fast skips the namer and tF1 in the report (the pytest version). Writes <workdir>/dry_run.json
and exits non-zero if any check fails.
"""
from __future__ import annotations

import argparse
import ast
import importlib.util
import json
import os
import shutil
import sys
import types
from pathlib import Path

import nibabel as nib
import numpy as np

REPO = Path(__file__).resolve().parents[2]
SCR = Path("/tmp/claude-0/-home-user-Asclepius/1b43aea1-ed14-5dd0-84ee-25f776047e09/scratchpad")
SUBMISSIONS = SCR / "data" / "submissions"
ICX_ROOT = SCR / "work" / "Bridge" / "icx"
CASES = {"imagecas_0002": "c0001", "imagecas_0005": "c0004"}   # Crucible's c(id-1) mapping


def _exporter():
    """The real exporter module, loaded standalone (its package __init__ needs Girder)."""
    spec = importlib.util.spec_from_file_location("sq_export",
                                                  REPO / "server/girder_segqueue/export.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _segments():
    """DEFAULT_SEGMENTS read out of settings.py, so the dry run cannot drift from the server."""
    tree = ast.parse((REPO / "server/girder_segqueue/settings.py").read_text())
    for node in tree.body:
        if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "DEFAULT_SEGMENTS":
            return [types.SimpleNamespace(**d) for d in ast.literal_eval(node.value)]
    raise RuntimeError("DEFAULT_SEGMENTS not found")


def _paths(case):
    sys.path.insert(0, str(SCR / "tools"))
    from girder import ct_path, mask_path  # noqa: E402
    return Path(ct_path(case)), Path(mask_path(case))


def _sitk_to_np(img):
    import SimpleITK as sitk
    return sitk.GetArrayFromImage(img).transpose(2, 1, 0)


def _np_to_sitk(arr, like):
    import SimpleITK as sitk
    out = sitk.GetImageFromArray(np.ascontiguousarray(arr.transpose(2, 1, 0)))
    out.CopyInformation(like)
    return out


def _resample(img, onto):
    import SimpleITK as sitk
    return sitk.Resample(img, onto, sitk.Transform(), sitk.sitkNearestNeighbor, 0, img.GetPixelID())


def build_export(export: Path, icx_flat: Path) -> dict:
    """Write the stand-in export. Returns per-case facts used by the checks."""
    import SimpleITK as sitk

    from segtrain.proxy import project_names
    from segtrain.reads import LAD, LM

    ex, segments = _exporter(), _segments()
    facts = {}
    for name, case in CASES.items():
        ct, mask = _paths(case)
        sub = sitk.ReadImage(str(SUBMISSIONS / f"{name}_attempt1.seg.nrrd"))
        ref = sitk.ReadImage(str(mask))
        on_grid = _sitk_to_np(_resample(sub, ref)) > 0                     # our (RAS) grid
        m = nib.load(str(mask))
        ours = np.asarray(m.dataobj) > 0.5
        dice = float(2 * (on_grid & ours).sum() / (on_grid.sum() + ours.sum()))
        icx = np.asarray(nib.load(str(icx_flat / f"{int(case[1:]) + 1}.coronary.nii.gz")).dataobj)
        read1, _ = project_names(on_grid, icx, m.header.get_zooms()[:3])
        from scipy import ndimage
        d_lm = ndimage.distance_transform_edt(read1 != LM, sampling=m.header.get_zooms()[:3])
        read2 = read1.copy()
        read2[(read1 == LAD) & (d_lm <= 3.0)] = LM                        # LM end ~3 mm distal
        for k, read in ((1, read1), (2, read2)):
            folder = export / (name if k == 1 else f"{name}__r2")
            (folder / "segmentations").mkdir(parents=True, exist_ok=True)
            stored = _resample(_np_to_sitk(read.astype(np.uint8), ref), sub)  # submission grid
            arr = sitk.GetArrayFromImage(stored)                             # exporter's order
            for s, a in ex.splitLabels(arr, segments).items():
                ex._writeMask(a, stored, str(folder / "segmentations" / f"{s}.nii.gz"))
            if not (folder / "ct.nii.gz").exists():   # the exporter copies the stored .nii.gz
                os.symlink(ct, folder / "ct.nii.gz")     # verbatim; a link saves 90 MB a read
            np.save(export.parent / f"truth_{case}_r{k}.npy", read)          # for the checks
        facts[name] = dict(case=case, submission_vs_mask_dice=round(dice, 4),
                           submission_space_directions=[list(r) for r in np.array(
                               sub.GetDirection()).reshape(3, 3) * np.array(sub.GetSpacing())],
                           n_vessel=int((read1 > 0).sum()),
                           lm_voxels_r1=int((read1 == LM).sum()), lm_voxels_r2=int((read2 == LM).sum()))
    # A14 decoys: data of an open case under a sealed name, and an unmappable name.
    for decoy in ("imagecas_0003", "scan_xyz"):
        shutil.copytree(export / "imagecas_0005", export / decoy, symlinks=True)
    return facts


def _icx_flat(work: Path) -> Path:
    d = work / "icx"
    d.mkdir(parents=True, exist_ok=True)
    for f in ("train", "val", "test", "exclude"):
        if not (d / f"{f}.txt").exists():
            os.symlink(ICX_ROOT / f"{f}.txt", d / f"{f}.txt")
    for case in CASES.values():
        n = f"{int(case[1:]) + 1}.coronary.nii.gz"
        if not (d / n).exists():
            os.symlink(ICX_ROOT / "segmentations" / n, d / n)
    return d


def run(work: Path, export: Path | None = None, fast: bool = False, report_step: bool = True) -> dict:
    from segtrain.cli import main
    from segtrain.config import load_config, load_task
    from segtrain.reads import first_reads_report, load_read_folder

    work.mkdir(parents=True, exist_ok=True)
    icx = _icx_flat(work)
    built = export is None
    if built:
        export = work / "export"
        if export.exists():
            shutil.rmtree(export)
        facts = build_export(export, icx)
    else:
        facts = {}
    roots = ["--zenodo-root", str(export), "--nnunet-raw", str(work / "raw"),
             "--nnunet-preprocessed", str(work / "pre"), "--nnunet-results", str(work / "res"),
             "--runs-root", str(work / "runs")]
    for d in ("raw", "pre", "res", "runs"):
        shutil.rmtree(work / d, ignore_errors=True)
    (export / "meta.csv").unlink(missing_ok=True)
    rc = {}
    rc["index"] = main(["index", "--root", str(export), "--layout", "nested",
                        "--val-fraction", "0", "--test-fraction", "0", *roots[:2]])
    rc["convert"] = main(["convert", "--task", "712", "--layout", "nested", "--link-mode",
                          "symlink", *roots])
    rc["splits"] = main(["splits", "--task", "712", "--explicit-icx", str(icx), *roots])
    out = work / "report"
    # reads-report has no A14 filter (Echo E1): give it a view of the export without the decoys,
    # so no sealed-named case reaches it (and no sealed mask is opened).
    view = work / "reads_view"
    shutil.rmtree(view, ignore_errors=True)
    view.mkdir()
    from segtrain.proxy import load_sealed, sealed_reason
    sealed = load_sealed()
    for d in sorted(p for p in export.iterdir() if p.is_dir()):
        if not sealed_reason(d.name, sealed):
            os.symlink(d, view / d.name)
    masks = SCR / "data" / "masks"
    if not report_step:
        report = {"cases": [], "wave": {}}
    elif fast:
        cases = load_read_folder(str(view), mask_dir=str(masks), icx_dir=str(icx))
        report = first_reads_report(cases, scorer=None, use_namer=False)
        out.mkdir(parents=True, exist_ok=True)
        (out / "report.json").write_text(json.dumps(report, indent=1, default=str))
        rc["reads-report"] = 0
    else:
        rc["reads-report"] = main(["reads-report", str(view), "--masks", str(masks),
                                   "--icx", str(icx), "--out", str(out)])
        report = json.loads((out / "report.json").read_text())

    cfg = load_config(None, {"zenodo_root": str(export), "nnunet_raw": str(work / "raw"),
                             "nnunet_preprocessed": str(work / "pre"),
                             "nnunet_results": str(work / "res"), "runs_root": str(work / "runs")})
    task = load_task(712)
    raw = task.raw_dir(cfg)
    trained = sorted(p.name[:-len("_0000.nii.gz")] for p in (raw / "imagesTr").glob("*_0000.nii.gz"))
    split = json.loads((task.preprocessed_dir(cfg) / "splits_final.json").read_text())[0]
    checks = {}
    checks["commands_exit_0"] = all(v == 0 for v in rc.values())
    checks["sealed_and_unmappable_decoys_refused"] = (not any(t.startswith(("imagecas_0003", "scan_"))
                                                             for t in trained))
    if built:
        expect = sorted([*CASES, *[f"{n}__r2" for n in CASES]])
        checks["both_reads_of_both_cases_converted"] = trained == expect
        # labels landed on the CT grid voxel-for-voxel equal to the reads (z reversal undone)
        eq = {}
        for name, case in CASES.items():
            for k, folder in ((1, name), (2, f"{name}__r2")):
                got = np.asarray(nib.load(str(raw / "labelsTr" / f"{folder}.nii.gz")).dataobj)
                eq[folder] = bool(np.array_equal(got, np.load(work / f"truth_{case}_r{k}.npy")))
        checks["labels_equal_reads_on_ct_grid"] = all(eq.values())
        checks["export_is_z_reversed"] = all(
            nib.load(str(export / n / "segmentations" / "left_main.nii.gz")).affine[2, 2] < 0
            for n in CASES)
        checks["reads_of_one_case_in_one_split"] = (
            set(split["val"]) == {"imagecas_0002", "imagecas_0002__r2"}
            and set(split["train"]) == {"imagecas_0005", "imagecas_0005__r2"})
    rows = {r["case"]: r for r in report["cases"]}
    if not report_step:
        result = dict(facts=facts, exit_codes=rc, trained=trained, split=split, checks=checks,
                      ok=all(checks.values()))
        (work / "dry_run.json").write_text(json.dumps(result, indent=1, default=str))
        return result
    checks["report_cases_mapped"] = (sorted(rows) == sorted(CASES.values())) if built else bool(rows)
    checks["report_two_reads_each"] = all(r["n_reads"] >= 2 for r in rows.values())
    conv = [c for r in rows.values() for c in r.get("convention", {}).values()]
    checks["convention_ran_with_calibre"] = bool(conv) and all(c["calibre_icx"] is not None
                                                             for c in conv)
    # A3 controls: imagecas_0002 is the whole mask (Dice 1.0) and must pass; imagecas_0005 is a
    # partial test submission (Dice 0.49 against c0004's mask) and must be flagged thin.
    if built:
        thin = {c: [v["thin"] for v in r.get("convention", {}).values()] for c, r in rows.items()}
        checks["a3_passes_full_split"] = thin.get("c0001") == [False, False]
        checks["a3_flags_partial_submission"] = thin.get("c0004") == [True, True]
        checks["a3_wave_halts"] = report["wave"].get("a3_halt") is True
    checks["anchor_computed"] = all("anchor" in r for r in rows.values())
    result = dict(facts=facts, exit_codes=rc, trained=trained, split=split,
                  wave={k: report["wave"].get(k) for k in ("n_cases", "a3_thin_reads",
                                                           "a3_reads_checked", "a3_halt",
                                                           "adjudication_rate",
                                                           "inter_read_tf1", "anchor_reviewed")},
                  per_case={c: dict(convention={k: {kk: v[kk] for kk in ("union_dice_vs_mask",
                                                                       "calibre_read",
                                                                       "calibre_icx", "thin")}
                                                for k, v in r.get("convention", {}).items()},
                                    third_read=r.get("third_read", {}).get("reasons"),
                                    lm_end_mm=r.get("lm_end_distance_mm"),
                                    anchor={k: v.get("offset_mm") for k, v in
                                            r.get("anchor", {}).items()})
                            for c, r in rows.items()},
                  checks=checks, ok=all(checks.values()))
    (work / "dry_run.json").write_text(json.dumps(result, indent=1, default=str))
    return result


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("work", type=Path)
    ap.add_argument("--export", type=Path)
    ap.add_argument("--fast", action="store_true")
    ap.add_argument("--no-report", action="store_true")
    a = ap.parse_args()
    r = run(a.work, a.export, a.fast, not a.no_report)
    print(json.dumps(r["checks"], indent=1))
    sys.exit(0 if r["ok"] else 1)
