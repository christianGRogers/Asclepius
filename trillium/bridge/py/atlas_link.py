"""A13: decide whether Bridge can run INFERENCE/SCORING ONLY against the Atlas run's outputs, instead of training.

Looks, in order, for an Atlas manifest (any of):
  $ATLAS_MANIFEST, <root>/experiments/atlas/results/manifest.json, $SCRATCH/atlas/results/manifest.json,
  $SCRATCH/atlas/manifest.json
and otherwise for Atlas's conventional layout under $SCRATCH/atlas (trillium/atlas/lib/prepare.py, job_body.sh):
  nnunet_raw/Dataset713_AtlasProxy/{imagesTr,labelsTr}, nnunet_preprocessed/Dataset713_AtlasProxy/splits_final.json,
  nnunet_results/Dataset713_AtlasProxy/nnUNetTrainerAtlas__<plans>__3d_fullres/fold_0/{checkpoint_final.pth,validation/}

Writes OUT.json with mode = 'atlas-ready' (checkpoint and/or validation predictions exist),
'atlas-pending' (Atlas job queued/running: wait for it), or 'train' (no Atlas run: Bridge trains its own model).
usage: python atlas_link.py BRIDGE_DIR OUT.json [ATLAS_JOBID_IF_QUEUED]
"""
import glob
import json
import os
import sys


def _first(paths):
    for p in paths:
        if p and os.path.exists(p):
            return p
    return None


def from_manifest(m, base):
    """accept the keys Atlas is likely to use; resolve relative paths against the manifest's folder"""
    def get(*keys):
        for k in keys:
            v = m.get(k)
            if isinstance(v, str) and v:
                return v if os.path.isabs(v) else os.path.join(base, v)
        return None
    fold = get('model_dir', 'fold_dir')
    env = m.get('env') or {}
    seg = get('val_segmentations_dir', 'validation_dir') or (fold and os.path.join(fold, 'validation'))
    return dict(fold_dir=fold, validation_dir=seg, softmax_dir=get('val_softmax_dir') or seg,
                labels_dir=get('reference_labels_dir', 'labels_dir'),
                images_dir=get('images_dir'),
                nnunet_results=env.get('nnUNet_results') or get('nnUNet_results'),
                splits=get('splits_json', 'splits'),
                trainer_py=get('trainer_source', 'trainer_py'),
                checkpoint_hint=get('checkpoint_final'),
                plans=m.get('plans'), dataset_id=m.get('dataset_id', 713), trainer=m.get('trainer', 'nnUNetTrainerAtlas'),
                val_cases=m.get('val_cases'), sealed_cases_touched=m.get('sealed_cases_touched'))


def conventional(W):
    ds = 'Dataset713_AtlasProxy'
    folds = sorted(glob.glob(f'{W}/nnunet_results/{ds}/nnUNetTrainerAtlas__*__3d_fullres/fold_0'))
    if not folds:
        return None
    fold = folds[-1]
    plans = os.path.basename(os.path.dirname(fold)).split('__')[1]
    return dict(fold_dir=fold, validation_dir=os.path.join(fold, 'validation'),
                labels_dir=f'{W}/nnunet_raw/{ds}/labelsTr', images_dir=f'{W}/nnunet_raw/{ds}/imagesTr',
                nnunet_results=f'{W}/nnunet_results', splits=f'{W}/nnunet_preprocessed/{ds}/splits_final.json',
                trainer_py=None, plans=plans, dataset_id=713, trainer='nnUNetTrainerAtlas', val_cases=None)


def main(bridge_dir, out, queued_jobid=''):
    scratch = os.environ.get('SCRATCH', '')
    W = os.environ.get('ATLAS_W') or (os.path.join(scratch, 'atlas') if scratch else '')
    root_atlas = os.path.join(os.path.dirname(bridge_dir), 'atlas')
    man = _first([os.environ.get('ATLAS_MANIFEST'), os.path.join(root_atlas, 'results', 'manifest.json'),
                  W and os.path.join(W, 'results', 'manifest.json'), W and os.path.join(W, 'manifest.json')])
    info, source = None, None
    if man:
        info, source = from_manifest(json.load(open(man)), os.path.dirname(man)), f'manifest {man}'
    elif W and os.path.isdir(W):
        info, source = conventional(W), f'Atlas work dir {W} (no manifest)'
    if info and not info.get('trainer_py'):
        info['trainer_py'] = _first([os.path.join(root_atlas, 'lib', 'atlas_trainers.py')])
    res = dict(source=source, atlas_jobid=queued_jobid or None)
    if info:
        res.update(info)
        val = info.get('val_cases')
        if not val and info.get('splits') and os.path.exists(info['splits']):
            val = json.load(open(info['splits']))[0]['val']
        res['val_cases'] = val
        vdir = info.get('validation_dir'); sdir = info.get('softmax_dir') or vdir
        val = val or []
        preds = [c for c in val if vdir and os.path.exists(os.path.join(vdir, c + '.nii.gz'))]
        npz = [c for c in val if sdir and os.path.exists(os.path.join(sdir, c + '.npz'))
               and os.path.getsize(os.path.join(sdir, c + '.npz')) > 1000]
        ckpt = _first([info.get('checkpoint_hint'), info.get('fold_dir') and os.path.join(info['fold_dir'], 'checkpoint_final.pth')])
        if ckpt and os.path.getsize(ckpt) < 1000:
            ckpt = None   # placeholder / truncated checkpoint
        res.update(n_val_pred=len(preds), n_val_npz=len(npz), checkpoint=ckpt,
                   labels_ok=bool(info.get('labels_dir') and os.path.isdir(info['labels_dir'])))
        both_ok = len(npz) >= 0.9 * len(val) and len(preds) >= 0.9 * len(val)
        ready = res['labels_ok'] and bool(val) and (both_ok or bool(ckpt and info.get('trainer_py') and info.get('images_dir')))
        if ready:
            res['mode'] = 'atlas-ready'
            res['need_predict'] = not both_ok   # no (complete) saved softmax: re-predict val with the checkpoint
        elif queued_jobid:
            res['mode'] = 'atlas-pending'
        else:
            res['mode'] = 'train'
            res['why'] = 'Atlas outputs incomplete (no val softmax and no usable checkpoint/trainer) and no Atlas job queued'
    else:
        res['mode'] = 'atlas-pending' if queued_jobid else 'train'
        res['why'] = 'no Atlas manifest or work dir found' if not queued_jobid else 'Atlas job queued/running'
    json.dump(res, open(out, 'w'), indent=1)
    print(f"A13 decision: {res['mode']}  ({res.get('source') or res.get('why')})"
          + (f"; val preds {res.get('n_val_pred')}, softmax {res.get('n_val_npz')}, checkpoint {'yes' if res.get('checkpoint') else 'no'}"
             if info else ''))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else '')
