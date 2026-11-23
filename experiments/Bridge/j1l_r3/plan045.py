"""Bridge, Janus 1-L round 3 (#302, §5 item 3): what nnU-Net 2.8.1's own planner gives at 0.45 mm.

Janus 0 was planned by `nnUNetv2_plan_experiment -pl ResEncUNetPlanner -gpu_memory_target 60
-overwrite_target_spacing 0.5 0.5 0.5` (trillium/icx4/lib/prepare.py): patch 256^3, batch 2. This script runs the
same planner, on CPU, on a fingerprint built from the D45 train 620's ImageCAS-X label headers (the labels share their
CT's grid, so spacings and shapes are the CT's; cropping to nonzero leaves a full-FOV CT unchanged). Intensity
properties do not enter the patch/batch choice and are placeholders here. It plans at 0.5 mm (to check it reproduces
Janus 0's 256^3 / batch 2) and at 0.45 mm, and prints patch, batch, the field of view in mm, and the network.
Labels' headers only are read (no voxel data, no CT); ids outside the 620 are refused.
Usage: <venv with nnunetv2==2.8.1>/bin/python plan045.py <dir of the 620 labels> <scratch dir> [out.json]
"""
import json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))


def main(lab_dir, scratch):
    import nibabel as nib
    sp = json.load(open(os.path.join(REPO, 'experiments/Delta/j1l_r1/janus1_split_proposal.json')))
    train = set(sp['train620'])
    files = sorted(f for f in os.listdir(lab_dir) if f.endswith('.nii.gz'))
    ids = [f.split('.')[0] for f in files]
    assert set(ids) == train, 'not exactly the train 620'
    raw, pre, res = (os.path.join(scratch, d) for d in ('raw', 'pre', 'res'))
    name = 'Dataset999_J1LPLAN'
    os.environ.update(nnUNet_raw=raw, nnUNet_preprocessed=pre, nnUNet_results=res)
    os.makedirs(os.path.join(raw, name, 'imagesTr'), exist_ok=True)
    os.makedirs(os.path.join(raw, name, 'labelsTr'), exist_ok=True)
    os.makedirs(os.path.join(pre, name), exist_ok=True)
    spacings, shapes = [], []
    for c, f in zip(ids, files):
        h = nib.load(os.path.join(lab_dir, f)).header
        z = [float(x) for x in h.get_zooms()[:3]]; s = [int(x) for x in h.get_data_shape()[:3]]
        spacings.append(z[::-1]); shapes.append(s[::-1])        # SimpleITK order (z, y, x), as nnU-Net reads .nii.gz
        tiny = nib.Nifti1Image(np.zeros((2, 2, 2), np.int16), np.diag(z + [1]))
        for d, fn in (('imagesTr', f'{c}_0000.nii.gz'), ('labelsTr', f'{c}.nii.gz')):
            p = os.path.join(raw, name, d, fn)
            if not os.path.exists(p):
                nib.save(tiny, p)
    dj = dict(channel_names={'0': 'CT'}, labels=dict(background=0, LM=1, LAD=2, LCx=3, RCA=4),
              numTraining=len(ids), file_ending='.nii.gz')
    json.dump(dj, open(os.path.join(raw, name, 'dataset.json'), 'w'))
    json.dump(dj, open(os.path.join(pre, name, 'dataset.json'), 'w'))
    fp = dict(spacings=spacings, shapes_after_crop=shapes, median_relative_size_after_cropping=1.0,
              foreground_intensity_properties_per_channel={'0': dict(mean=300.0, median=300.0, std=100.0, min=-1024.0,
                                                                      max=3000.0, percentile_99_5=719.0,
                                                                      percentile_00_5=-169.0)})
    json.dump(fp, open(os.path.join(pre, name, 'dataset_fingerprint.json'), 'w'))
    from nnunetv2.experiment_planning.experiment_planners.residual_unets.residual_encoder_unet_planners import \
        ResEncUNetPlanner
    out = {'n': len(ids), 'median_spacing_zyx': np.median(spacings, 0).round(3).tolist(),
           'median_shape_zyx': np.median(shapes, 0).tolist(), 'plans': {}}
    for t, pn in ((0.5, 'iso05'), (0.45, 'iso045')):
        p = ResEncUNetPlanner(999, gpu_memory_target_in_gb=60, plans_name=f'nnUNetResEncUNetPlans_60G_{pn}',
                              overwrite_target_spacing=[t, t, t], suppress_transpose=False)
        plans = p.plan_experiment()
        c3 = plans['configurations']['3d_fullres']
        arch = c3['architecture']['arch_kwargs']
        out['plans'][f'{t}'] = dict(patch=c3['patch_size'], batch=c3['batch_size'], spacing=c3['spacing'],
                                    fov_mm=[round(a * b, 1) for a, b in zip(c3['patch_size'], c3['spacing'])],
                                    median_image_size_in_voxels=c3.get('median_image_size_in_voxels'),
                                    n_stages=arch['n_stages'], features=arch['features_per_stage'],
                                    blocks=arch.get('n_blocks_per_stage'))
    s = json.dumps(out, indent=1)
    if len(sys.argv) > 3:
        open(sys.argv[3], "w").write(s)
    print(s)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
