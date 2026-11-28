"""`prep` (CPU job): Dataset719_J1F = the 620 only (F-A29), plans moved and checked, fingerprint placed, preprocess.

  python -m janus1f.dataset prep    <work> <layout.json> <icx_dir> <janus0_model_dir (holds plans.json)> <n_proc>
  python -m janus1f.dataset census  <work>          # what `status` prints after prep

In order, each step refusing on doubt:
  1. the pinned split (620 / 100, no sealed id); a Dataset719 not made by this launcher is a used id: refuse;
  2. every one of the 620 has its CT (layout.json) and its ImageCAS-X label, on the same grid; else print icx4's
     idempotent fetch steps and stop;
  3. labels: the scorer of record's `stage1_labels` (F-A28, the one converter), 255 written as 13 (F-A29); the summed
     converter counts must equal F0-r2's line {d3 47, d4_to_lad 2, other_lcx 20, other_nearest 1, other_ignore 8};
  4. dataset.json: labels 0..12 and "ignore": 13; no locked or sealed id in imagesTr / labelsTr;
  5. Step T's plans.json (sha256 pinned) placed as Dataset715_ICX4/<P>.json, `nnUNetv2_move_plans_between_datasets
     -s 715 -t 719 -sp P -tp P`, Janus 0's dataset_fingerprint.json (pinned) placed; L-A21's check (`janus1f.plans`);
     no plan_experiment, no extract_fingerprint; a class-weight file refuses (Step T: unweighted DiceCE);
  6. `nnUNetv2_preprocess` only; then no locked id in the preprocessed folder; splits_final.json (F-A20) written and
     checked.
"""
import json
import os
import shutil
import subprocess
import sys
import time

import numpy as np

from . import pins, plans as plans_check, split

DS_ID, DS = 719, 'Dataset719_J1F'
SRC_ID, SRC = 715, 'Dataset715_ICX4'
PLANS = 'nnUNetResEncUNetPlans_60G_iso05'
IGNORE_DISK = 13
SCORER_IGNORE = 255
LABELS = {'background': 0, 'LM': 1, 'LAD': 2, 'LCx': 3, 'RCA': 4, 'D1': 5, 'D2': 6, 'D3': 7, 'OM1': 8, 'OM2': 9,
          'Ramus': 10, 'PDA': 11, 'PLB': 12, 'ignore': IGNORE_DISK}
OWN = '.janus1f_dataset'
FETCH_STEPS = ('the CT or label set is incomplete. Fetch with icx4\'s idempotent steps, then re-run prep:\n'
               '  python3 $SCRATCH/asclepius/repo/trillium/fetch_cases.py $SCRATCH/asclepius/cases   # CTs\n'
               '  python3 $SCRATCH/asclepius/repo/trillium/icx4/lib/fetch_icx.py $SCRATCH/icx4/icx  # labels\n'
               '  python3 $SCRATCH/asclepius/repo/trillium/icx4/lib/layout.py <cases> $SCRATCH/icx4/layout.json')


class PrepError(RuntimeError):
    pass


def paths(work):
    raw, pp, res = (os.path.join(work, d) for d in ('nnunet_raw', 'nnunet_preprocessed', 'nnunet_results'))
    return {'raw_root': raw, 'pp_root': pp, 'res_root': res, 'raw': os.path.join(raw, DS),
            'pp': os.path.join(pp, DS), 'src_pp': os.path.join(pp, SRC)}


def nnunet_env(work):
    p = paths(work)
    return dict(os.environ, nnUNet_raw=p['raw_root'], nnUNet_preprocessed=p['pp_root'], nnUNet_results=p['res_root'])


# ---------------------------------------------------------------------------- checks (each a self-test target)
def refuse_used_id(work):
    """Any Dataset719_* under this work tree that this launcher did not create is a used dataset id."""
    p = paths(work)
    for root in (p['raw_root'], p['pp_root'], p['res_root']):
        if not os.path.isdir(root):
            continue
        for d in os.listdir(root):
            if d.startswith(f'Dataset{DS_ID}_') and (d != DS or not os.path.exists(os.path.join(p['raw'], OWN))):
                raise PrepError(f'refusing: dataset id {DS_ID} is already used by {os.path.join(root, d)}')


def check_label_values(lab, case=''):
    """Labels on disk are 0..12 and 13 only. A 255 (the scorer's ignore) or anything else refuses (F-A29)."""
    v = np.unique(np.asarray(lab))
    bad = [int(x) for x in v if not 0 <= int(x) <= IGNORE_DISK]
    if bad:
        raise PrepError(f'refusing: {case} label values {bad} on disk (ignore must be written as 13, F-A29)')
    return [int(x) for x in v]


def to_disk(stage1):
    """The converter's 255 -> 13 (F-A29); refuses any other value outside 0..12."""
    lab = np.asarray(stage1).astype(np.uint8).copy()
    other = (lab > 12) & (lab != SCORER_IGNORE)
    if other.any():
        raise PrepError(f'converter wrote values {np.unique(lab[other]).tolist()}')
    lab[lab == SCORER_IGNORE] = IGNORE_DISK
    return lab


def dataset_json(n):
    return {'channel_names': {'0': 'CT'}, 'labels': dict(LABELS), 'numTraining': n, 'file_ending': '.nii.gz'}


def check_dataset_json(d, build_label_manager=True):
    """`"ignore": 13`, labels consecutive 0..12; and nnU-Net's own LabelManager accepts it when nnU-Net is here."""
    lab = d.get('labels', {})
    if lab.get('ignore') != IGNORE_DISK:
        raise PrepError(f'refusing: dataset.json "ignore" is {lab.get("ignore")!r}, not 13 (F-A29)')
    if {k: v for k, v in lab.items() if k != 'ignore'} != {k: v for k, v in LABELS.items() if k != 'ignore'}:
        raise PrepError('refusing: dataset.json labels are not 0..12 in 1-F order')
    if build_label_manager:
        try:
            from nnunetv2.utilities.label_handling.label_handling import LabelManager
        except ImportError:
            return 'LabelManager not checked (no nnU-Net here)'
        lm = LabelManager(lab, regions_class_order=None)
        if lm.ignore_label != IGNORE_DISK or lm.num_segmentation_heads != 13:
            raise PrepError('nnU-Net LabelManager does not read ignore 13 / 13 heads')
        return 'LabelManager ok: 13 heads, ignore 13'
    return 'ok'


def ids_in(folder, suffix):
    if not os.path.isdir(folder):
        return []
    return sorted(f[:-len(suffix)] for f in os.listdir(folder) if f.endswith(suffix))


def check_raw_dataset(work, sp):
    """No locked or sealed id in imagesTr / labelsTr; exactly the 620 once complete."""
    p = paths(work)
    imgs = ids_in(os.path.join(p['raw'], 'imagesTr'), '_0000.nii.gz')
    labs = ids_in(os.path.join(p['raw'], 'labelsTr'), '.nii.gz')
    split.refuse_training(imgs, sp, 'Dataset719 imagesTr')
    split.refuse_training(labs, sp, 'Dataset719 labelsTr')
    return len(imgs), len(labs)


def check_preprocessed(work, sp):
    """No locked or sealed id anywhere in Dataset719's preprocessed folder."""
    p = paths(work)
    found = set()
    for root, _, files in os.walk(p['pp']):
        for f in files:
            stem = f.split('.')[0]
            if stem.startswith('c') and stem[1:5].isdigit() and len(stem) == 5:
                found.add(stem)
            elif stem.startswith('c') and stem[1:5].isdigit():
                found.add(stem[:5])
    split.refuse_training(sorted(found), sp, 'Dataset719 preprocessed')
    return len(found)


def check_no_class_weights(*dirs):
    for d in dirs:
        if d and os.path.exists(os.path.join(d, 'ce_class_weights.json')):
            raise PrepError(f'refusing: a class-weight file in {d} (Step T: J1F-A is unweighted DiceCE)')


# ---------------------------------------------------------------------------- labels
def _label_one(args):
    c, ct_path, icx_path = args
    import nibabel as nib
    sys.path.insert(0, pins.LIB)
    import j1f_scorer as S
    ct, li = nib.load(ct_path), nib.load(icx_path)
    if ct.shape[:3] != li.shape[:3] or not np.allclose(ct.affine, li.affine, atol=1e-2):
        raise PrepError(f'{c}: CT {ct.shape} and ImageCAS-X label {li.shape} grids differ')
    icx = np.asarray(li.dataobj).astype(np.uint8)
    if icx.max() > 14:
        raise PrepError(f'{c}: ImageCAS-X values outside 0..14')
    z = np.array(li.header.get_zooms()[:3], float)
    out = np.zeros(icx.shape, np.uint8)
    info = {k: 0 for k in pins.CONVERTER_LINE}
    nz = np.argwhere(icx > 0)
    if len(nz):
        lo, hi = np.maximum(nz.min(0) - 8, 0), nz.max(0) + 9
        box = tuple(slice(a, b) for a, b in zip(lo, hi))
        sub, info = S.stage1_labels(icx[box], z)
        out[box] = sub
    lab = to_disk(out)
    vals = check_label_values(lab, c)
    return c, lab, ct.affine, info, vals


def write_labels(work, sp, layout, icx_dir, n_proc):
    import nibabel as nib
    from multiprocessing import Pool
    p = paths(work)
    for d in ('imagesTr', 'labelsTr'):
        os.makedirs(os.path.join(p['raw'], d), exist_ok=True)
    open(os.path.join(p['raw'], OWN), 'w').write('made by trillium/janus1f prep\n')
    cases = layout['cases']
    todo, missing = [], []
    for c in sp['train620']:
        icx = os.path.join(icx_dir, f'{int(c[1:]) + 1}.coronary.nii.gz')
        if c not in cases or not os.path.exists(cases[c]['ct']) or not os.path.exists(icx):
            missing.append(c)
        else:
            todo.append((c, cases[c]['ct'], icx))
    if missing:
        raise PrepError(f'{len(missing)} of the 620 lack a CT or label (e.g. {missing[:5]}); {FETCH_STEPS}')
    tot = {k: 0 for k in pins.CONVERTER_LINE}
    present = {}
    with Pool(n_proc) as pool:
        for c, lab, aff, info, vals in pool.imap_unordered(_label_one, todo):
            img = os.path.join(p['raw'], 'imagesTr', f'{c}_0000.nii.gz')
            if not os.path.lexists(img):
                os.symlink(cases[c]['ct'], img)
            dst = os.path.join(p['raw'], 'labelsTr', f'{c}.nii.gz')
            nib.save(nib.Nifti1Image(lab, aff), dst + '.part.nii.gz')
            os.replace(dst + '.part.nii.gz', dst)
            for k in tot:
                tot[k] += int(info[k])
            present[c] = vals
    return tot, present


def check_converter_line(tot):
    if tot != pins.CONVERTER_LINE:
        raise PrepError(f'refusing: converter counts {tot} != F0-r2\'s line {pins.CONVERTER_LINE} (stop; PM)')
    return True


# ---------------------------------------------------------------------------- plans
def place_plans(work, j0_model_dir):
    """Step T's plans as Dataset715_ICX4/<P>.json; move to 719 (-tp = -sp); fingerprint placed; L-A21's check."""
    p = paths(work)
    j0_plans = os.path.join(j0_model_dir, 'plans.json')
    j0_fp = os.path.join(j0_model_dir, 'dataset_fingerprint.json')
    pins.check_file(j0_plans, pins.PLANS_SHA256, "Janus 0's plans.json (Step T)")
    pins.check_file(j0_fp, pins.FINGERPRINT_SHA256, "Janus 0's dataset_fingerprint.json (Step T)")
    os.makedirs(p['src_pp'], exist_ok=True)
    shutil.copyfile(j0_plans, os.path.join(p['src_pp'], PLANS + '.json'))
    os.makedirs(p['pp'], exist_ok=True)
    run(['nnUNetv2_move_plans_between_datasets', '-s', str(SRC_ID), '-t', str(DS_ID), '-sp', PLANS, '-tp', PLANS],
        nnunet_env(work))
    shutil.copyfile(j0_fp, os.path.join(p['pp'], 'dataset_fingerprint.json'))
    errs = plans_check.check(open(j0_plans, 'rb').read(), open(os.path.join(p['pp'], PLANS + '.json'), 'rb').read(),
                             open(j0_fp, 'rb').read(), open(os.path.join(p['pp'], 'dataset_fingerprint.json'),
                                                            'rb').read())
    if errs:
        raise PrepError('refusing: plans check: ' + '; '.join(errs))
    check_no_class_weights(j0_model_dir, p['pp'], p['raw'])
    return 'plans check OK (Step T b7178bbc...3cc2, fingerprint e41c772f...7e05, batch_dice False)'


def run(cmd, env=None):
    print('[janus1f] +', ' '.join(cmd), flush=True)
    t = time.time()
    subprocess.run(cmd, check=True, env=env)
    print(f'[janus1f]   done in {time.time() - t:.0f}s', flush=True)


def prep(work, layout_json, icx_dir, j0_model_dir, n_proc):
    sp = split.load()
    refuse_used_id(work)
    p = paths(work)
    layout = pins.load_json(layout_json)
    census = os.path.join(work, 'prep_census.json')
    if not os.path.exists(os.path.join(work, '.labels_done')):
        tot, present = write_labels(work, sp, layout, icx_dir, n_proc)
        check_converter_line(tot)
        with open(os.path.join(p['raw'], 'dataset.json'), 'w') as f:
            json.dump(dataset_json(len(present)), f, indent=1)
        per_class = {k: sum(v in vals for vals in present.values()) for k, v in LABELS.items() if v}
        json.dump({'converter': tot, 'cases': len(present), 'cases_with_label': per_class}, open(census, 'w'),
                  indent=1)
        open(os.path.join(work, '.labels_done'), 'w').write('ok')
    lm = check_dataset_json(pins.load_json(os.path.join(p['raw'], 'dataset.json')))
    n_img, n_lab = check_raw_dataset(work, sp)
    if (n_img, n_lab) != (620, 620):
        raise PrepError(f'Dataset719 holds {n_img} images and {n_lab} labels, not 620 and 620')
    print(f'[janus1f] Dataset719_J1F: 620 images, 620 labels, no locked or sealed id; {lm}', flush=True)
    print(f'[janus1f] converter {pins.load_json(census)["converter"]} = F0-r2\'s line', flush=True)
    if not os.path.exists(os.path.join(work, '.plans_done')):
        msg = place_plans(work, j0_model_dir)
        open(os.path.join(work, '.plans_done'), 'w').write(msg)
    print('[janus1f] ' + open(os.path.join(work, '.plans_done')).read(), flush=True)
    if not os.path.exists(os.path.join(work, '.preprocess_done')):
        run(['nnUNetv2_preprocess', '-d', str(DS_ID), '-plans_name', PLANS, '-c', '3d_fullres',
             '-np', str(min(n_proc, 10))], nnunet_env(work))
        open(os.path.join(work, '.preprocess_done'), 'w').write('ok')
    sf = split.splits_final(sp)
    with open(os.path.join(p['pp'], 'splits_final.json'), 'w') as f:
        json.dump(sf, f, indent=1)
    split.check_splits_final(pins.load_json(os.path.join(p['pp'], 'splits_final.json')), sp)
    n_pp = check_preprocessed(work, sp)
    print(f'[janus1f] preprocessed: {n_pp} case ids, none locked or sealed; splits_final.json: two entries, train 620, '
          'val the fit-check 20', flush=True)
    open(os.path.join(work, '.prep_done'), 'w').write('ok')
    return 0


def main(argv):
    if argv[:1] == ['prep']:
        return prep(argv[1], argv[2], argv[3], argv[4], int(argv[5]))
    if argv[:1] == ['census']:
        c = os.path.join(argv[1], 'prep_census.json')
        print(open(c).read() if os.path.exists(c) else '[janus1f] no prep census yet')
        return 0
    print(__doc__)
    return 2


if __name__ == '__main__':
    try:
        sys.exit(main(sys.argv[1:]))
    except (PrepError, split.SplitError, pins.PinError) as e:
        sys.exit(f'[janus1f] {e}')
