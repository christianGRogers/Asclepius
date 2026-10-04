"""Run nnU-Net v2's own experiment planners (default plain U-Net and ResEnc M/L/XL presets, plus custom VRAM
targets) on a synthetic fingerprint built from the real cohort headers (all 1000 cases), at native median
spacing and at 0.5 mm isotropic. Prints patch size, batch size, patch fraction of median volume, whether a
3d_lowres/cascade is planned. No images needed: planners only read dataset.json + fingerprint.
Usage: planner_sweep.py <workdir> <headers.json>"""
import os, sys, json, shutil
import numpy as np
work, hj = sys.argv[1], sys.argv[2]
os.environ['nnUNet_raw'] = os.path.join(work, 'raw'); os.environ['nnUNet_preprocessed'] = os.path.join(work, 'pp')
os.environ['nnUNet_results'] = os.path.join(work, 'res')
import nibabel as nib
H = json.load(open(hj)); sp = np.array(H['sp']); sh = np.array(H['sh'])
name = 'Dataset710_CCTA'
raw = os.path.join(work, 'raw', name); pp = os.path.join(work, 'pp', name)
if not os.path.isdir(raw):
    os.makedirs(raw + '/imagesTr'); os.makedirs(raw + '/labelsTr'); os.makedirs(pp)
    tiny = nib.Nifti1Image(np.zeros((2, 2, 2), np.int16), np.eye(4))
    for i in range(len(sp)):
        nib.save(tiny, f'{raw}/imagesTr/c{i:04d}_0000.nii.gz'); nib.save(tiny, f'{raw}/labelsTr/c{i:04d}.nii.gz')
    json.dump({'channel_names': {'0': 'CT'}, 'labels': {'background': 0, 'left_main': 1, 'left_anterior_descending': 2,
               'left_circumflex': 3, 'right_coronary_artery': 4}, 'numTraining': len(sp), 'file_ending': '.nii.gz'},
              open(raw + '/dataset.json', 'w'))
    # SimpleITK convention: (z, y, x)
    json.dump({'spacings': sp[:, ::-1].tolist(), 'shapes_after_crop': sh[:, ::-1].tolist(),
               'foreground_intensity_properties_per_channel': {'0': {'mean': 400., 'median': 400., 'std': 120.,
                   'min': -200., 'max': 1500., 'percentile_99_5': 800., 'percentile_00_5': 100.}},
               'median_relative_size_after_cropping': 1.0}, open(pp + '/dataset_fingerprint.json', 'w'))
from nnunetv2.experiment_planning.experiment_planners.default_experiment_planner import ExperimentPlanner
from nnunetv2.experiment_planning.experiment_planners.residual_unets.residual_encoder_unet_planners import (
    nnUNetPlannerResEncM, nnUNetPlannerResEncL, nnUNetPlannerResEncXL, ResEncUNetPlanner)
import io, contextlib
runs = [('plain_8GB', ExperimentPlanner, dict()), ('plain_24GB', ExperimentPlanner, dict(gpu_memory_target_in_gb=24)),
        ('plain_40GB', ExperimentPlanner, dict(gpu_memory_target_in_gb=40)), ('plain_70GB', ExperimentPlanner, dict(gpu_memory_target_in_gb=70)),
        ('ResEncM', nnUNetPlannerResEncM, dict()), ('ResEncL', nnUNetPlannerResEncL, dict()), ('ResEncXL', nnUNetPlannerResEncXL, dict()),
        ('ResEnc_60GB', ResEncUNetPlanner, dict(gpu_memory_target_in_gb=60)), ('ResEnc_75GB', ResEncUNetPlanner, dict(gpu_memory_target_in_gb=75))]
med_sp = np.median(sp[:, ::-1], 0)
for iso in (False, True):
    for nm, cls, kw in runs:
        if iso: kw = dict(kw, overwrite_target_spacing=[0.5, 0.5, 0.5])
        pl = cls(name, plans_name=f'p_{nm}_{"iso" if iso else "nat"}', **kw)
        with contextlib.redirect_stdout(io.StringIO()):
            plans = pl.plan_experiment()
        c = plans['configurations']['3d_fullres']
        ts = np.array(c['spacing']); ps = np.array(c['patch_size']); med_shape = np.array(c['median_image_size_in_voxels'])
        frac = np.prod(ps) / np.prod(med_shape)
        print(f"{nm:12s} {'0.5iso' if iso else 'native'} spacing={np.round(ts,3).tolist()} median_shape={med_shape.tolist()} "
              f"patch={ps.tolist()} ({np.prod(ps)/1e6:.1f} Mvox, {ps*ts} mm) bs={c['batch_size']} "
              f"patch/median_vol={frac:.3f} lowres_planned={'3d_lowres' in plans['configurations']} "
              f"stages={len(c['architecture']['arch_kwargs']['n_stages']) if isinstance(c['architecture']['arch_kwargs']['n_stages'], list) else c['architecture']['arch_kwargs']['n_stages']}")
