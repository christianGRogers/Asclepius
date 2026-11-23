"""Bridge, Janus 1-L round 3 (§5 item 6): does `nnUNetv2_ensemble` output feed threshold_export.py and rule_t.py?

Toy, CPU, no data: two fake prediction folders written the way `nnUNetv2_predict --save_probabilities` writes them
(<case>.npz with `probabilities` in SimpleITK axis order, <case>.pkl, <case>.nii.gz, dataset.json, plans.json),
ensembled by nnU-Net 2.8.1's own `ensemble_folders`, with and without save_merged_probabilities (= `--save_npz`).
Checks: (1) without --save_npz there is no .npz, so threshold_export has nothing to read; (2) with it, E's npz is the
mean of the two; (3) threshold_export at t = 0.5 reproduces the ensemble's own segmentation, and the export dirs are
named t0.60 ... t0.25 as rule_t.py reads them; (4) `nnUNetv2_ensemble` of two copies of one fold reproduces that
fold (L-A21 self-test 8).
Usage: <venv with nnunetv2==2.8.1>/bin/python ensemble_chain.py <scratch dir>
"""
import json, os, pickle, subprocess, sys, shutil
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
GRID = ['0.6', '0.55', '0.5', '0.45', '0.4', '0.35', '0.3', '0.25']


def write_fold(d, case, prob_sitk, spacing_xyz):
    import SimpleITK as sitk
    os.makedirs(d, exist_ok=True)
    np.savez_compressed(os.path.join(d, case + '.npz'), probabilities=prob_sitk.astype(np.float32))
    seg = prob_sitk.argmax(0).astype(np.uint8)                       # (z, y, x)
    im = sitk.GetImageFromArray(seg); im.SetSpacing(spacing_xyz)
    sitk.WriteImage(im, os.path.join(d, case + '.nii.gz'))
    props = {'sitk_stuff': {'spacing': spacing_xyz, 'origin': (0.0, 0.0, 0.0), 'direction': tuple(np.eye(3).ravel())},
             'spacing': list(spacing_xyz[::-1])}
    pickle.dump(props, open(os.path.join(d, case + '.pkl'), 'wb'))
    json.dump(dict(channel_names={'0': 'CT'}, labels=dict(background=0, LM=1, LAD=2, LCx=3, RCA=4), numTraining=1,
                   file_ending='.nii.gz'), open(os.path.join(d, 'dataset.json'), 'w'))
    json.dump(dict(dataset_name='Dataset999_T', plans_name='p', original_median_spacing_after_transp=[0.5] * 3,
                   original_median_shape_after_transp=[1, 1, 1], image_reader_writer='SimpleITKIO',
                   transpose_forward=[0, 1, 2], transpose_backward=[0, 1, 2], configurations={},
                   experiment_planner_used='x', label_manager='LabelManager',
                   foreground_intensity_properties_per_channel={}), open(os.path.join(d, 'plans.json'), 'w'))


def main(scratch):
    from nnunetv2.ensembling.ensemble import ensemble_folders
    import nibabel as nib
    shutil.rmtree(scratch, ignore_errors=True)
    rng = np.random.default_rng(0)
    case = 'c0005'                                   # a D60 id (rule_t refuses others; nothing is read from disk)
    shape = (5, 12, 14, 16)
    probs = []
    for k in range(2):
        lg = rng.normal(size=shape); lg[0] += 0.5
        p = np.exp(lg) / np.exp(lg).sum(0); probs.append(p)
        write_fold(os.path.join(scratch, f'f{k}'), case, p, (0.4, 0.4, 0.5))
    f0, f1 = (os.path.join(scratch, f'f{k}') for k in range(2))
    ensemble_folders([f0, f1], os.path.join(scratch, 'E_noz'), save_merged_probabilities=False, num_processes=1)
    r = {'no_save_npz_has_npz': os.path.exists(os.path.join(scratch, 'E_noz', case + '.npz'))}
    ensemble_folders([f0, f1], os.path.join(scratch, 'E'), save_merged_probabilities=True, num_processes=1)
    pe = np.load(os.path.join(scratch, 'E', case + '.npz'))['probabilities']
    r['E_is_mean'] = bool(np.allclose(pe, (probs[0] + probs[1]) / 2, atol=1e-6))
    ensemble_folders([f0, f0], os.path.join(scratch, 'E00'), save_merged_probabilities=True, num_processes=1)
    s00 = nib.load(os.path.join(scratch, 'E00', case + '.nii.gz')).get_fdata()
    s0 = nib.load(os.path.join(f0, case + '.nii.gz')).get_fdata()
    r['two_copies_reproduce_fold'] = bool((s00 == s0).all())
    out = os.path.join(scratch, 'thr')
    subprocess.run([sys.executable, os.path.join(REPO, 'experiments/Crucible/j1l_r1/threshold_export.py'), '--probs',
                    os.path.join(scratch, 'E'), '--out', out, '--np', '1', '--t'] + GRID, check=True,
                   capture_output=True)
    r['export_dirs'] = sorted(os.listdir(out))
    seg_e = np.asarray(nib.load(os.path.join(scratch, 'E', case + '.nii.gz')).dataobj)
    t05 = np.asarray(nib.load(os.path.join(out, 't0.50', case + '.nii.gz')).dataobj)
    r['t050_equals_ensemble_argmax'] = bool((t05 == seg_e).all())
    r['rule_t_dirs_present'] = all(os.path.isdir(os.path.join(out, f't{float(t):.2f}')) for t in GRID)
    ok = (not r['no_save_npz_has_npz'] and r['E_is_mean'] and r['two_copies_reproduce_fold']
          and r['t050_equals_ensemble_argmax'] and r['rule_t_dirs_present'])
    r['verdict'] = 'PASS' if ok else 'FAIL'
    print(json.dumps(r, indent=1))


if __name__ == '__main__':
    main(sys.argv[1])
