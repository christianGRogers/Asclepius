"""Round 9 (Fir): how many CPU-seconds does nnU-Net 2.8.1's training loader spend per batch of the icx4 plan?

Builds synthetic preprocessed cases the size of the icx4/icx14 median case (275 x 358 x 358 at 0.5 mm, float32,
blosc2 exactly as nnU-Net's preprocessor writes them, chunks/blocks from comp_blosc2_params for the 256^3 patch),
with a thin tube tree labelled 1-4 so foreground oversampling has something to hit. Then runs nnU-Net's own
nnUNetDataLoader with nnUNetTrainer.get_training_transforms (rotation +-30 deg, scaling, noise, blur, brightness,
contrast, low-res, gamma, deep-supervision downsampling; mirroring off as in nnUNetTrainerICX4) on one thread, the
way each augmentation worker runs (NonDetMultiThreadedAugmenter sets torch.set_num_threads(1)), and times
generate_train_batch().

Usage: fir_da_throughput.py <plans.json> <workdir> [n_batches]
The plans file is the icx14 run's nnUNetResEncUNetPlans_60G_iso05.json (same plan as icx4)."""
import json, os, sys, time, statistics, warnings
import numpy as np, torch
from scipy.ndimage import gaussian_filter

warnings.filterwarnings('ignore')
torch.set_num_threads(1)
from nnunetv2.training.dataloading.nnunet_dataset import nnUNetDatasetBlosc2, comp_blosc2_params
from nnunetv2.training.dataloading.data_loader import nnUNetDataLoader
from nnunetv2.training.nnUNetTrainer.nnUNetTrainer import nnUNetTrainer
from nnunetv2.training.data_augmentation.compute_initial_patch_size import get_patch_size
from nnunetv2.utilities.label_handling.label_handling import LabelManager
from nnunetv2.preprocessing.preprocessors.default_preprocessor import DefaultPreprocessor

plans_f, W = sys.argv[1], sys.argv[2]
NB = int(sys.argv[3]) if len(sys.argv) > 3 else 10
os.makedirs(W, exist_ok=True)
cfg = json.load(open(plans_f))['configurations']['3d_fullres']
patch = tuple(cfg['patch_size']); bs = cfg['batch_size']
shape = tuple(int(s) for s in cfg['median_image_size_in_voxels'])
pool = cfg['architecture']['arch_kwargs']['strides']  # = pool_op_kernel_sizes in nnU-Net's ConfigurationManager
print('patch', patch, 'batch', bs, 'case shape', shape)

rng = np.random.default_rng(0)


def synth_case(seed):
    r = np.random.default_rng(seed)
    img = gaussian_filter(r.standard_normal(shape).astype(np.float32), 2.0) * 8.0
    seg = np.zeros(shape, np.int16)
    # four random-walk tubes of ~3 voxel radius, one per class, starting near the middle
    zz, yy, xx = np.ogrid[:shape[0], :shape[1], :shape[2]]
    for cls in range(1, 5):
        p = np.array(shape, float) / 2 + r.normal(0, 20, 3)
        d = r.normal(0, 1, 3); d /= np.linalg.norm(d)
        for _ in range(60):
            d += r.normal(0, 0.3, 3); d /= np.linalg.norm(d); p = np.clip(p + 3 * d, 5, np.array(shape) - 6)
            z, y, x = p.astype(int)
            sl = (slice(z - 4, z + 5), slice(y - 4, y + 5), slice(x - 4, x + 5))
            m = ((zz[sl[0]] - z) ** 2 + (yy[:, sl[1]] - y) ** 2 + (xx[:, :, sl[2]] - x) ** 2) <= 9
            seg[sl][m] = cls
    img[seg > 0] += 4.0
    return img[None], seg[None]


ids = []
for k in range(3):
    ident = f'c{k:04d}'
    out = os.path.join(W, ident)
    if not os.path.exists(out + '.b2nd'):
        img, seg = synth_case(k)
        props = {'spacing': [0.5, 0.5, 0.5], 'shape_before_cropping': shape, 'bbox_used_for_cropping': [[0, s] for s in shape],
                 'shape_after_cropping_and_before_resampling': shape}
        props['class_locations'] = DefaultPreprocessor._sample_foreground_locations(seg, [1, 2, 3, 4])
        bd, cd = comp_blosc2_params(img.shape, patch, img.itemsize)
        bsg, csg = comp_blosc2_params(seg.shape, patch, seg.itemsize)
        nnUNetDatasetBlosc2.save_case(img, seg, props, out, chunks=cd, blocks=bd, chunks_seg=csg, blocks_seg=bsg)
    ids.append(ident)

ds = nnUNetDatasetBlosc2(W, ids)
lm = LabelManager({'background': 0, 'LM': 1, 'LAD': 2, 'LCx': 3, 'RCA': 4}, regions_class_order=None)
rot = (-30. / 360 * 2. * np.pi, 30. / 360 * 2. * np.pi)
init_patch = get_patch_size(patch, rot, rot, rot, (0.85, 1.25))
ds_scales = list(list(i) for i in 1 / np.cumprod(np.vstack(pool), axis=0))[:-1]
tr = nnUNetTrainer.get_training_transforms(patch, rot, ds_scales, None, False, use_mask_for_norm=[False],
                                           is_cascaded=False, foreground_labels=lm.foreground_labels,
                                           regions=None, ignore_label=None)
dl = nnUNetDataLoader(ds, bs, init_patch, patch, lm, oversample_foreground_percent=0.33,
                      sampling_probabilities=None, pad_sides=None, transforms=tr, probabilistic_oversampling=False)
print('initial (pre-rotation) patch', init_patch)
dl.generate_train_batch()  # warm-up (imports, caches)
times = []
for i in range(NB):
    t0 = time.perf_counter(); b = dl.generate_train_batch(); times.append(time.perf_counter() - t0)
    print(f'batch {i}: {times[-1]:.2f} s  data {tuple(b["data"].shape)}', flush=True)
res = {'n_batches': NB, 'batch_size': bs, 'patch': patch, 'initial_patch': [int(x) for x in init_patch],
       'cpu_s_per_batch_median': round(statistics.median(times), 3), 'cpu_s_per_batch_mean': round(statistics.mean(times), 3),
       'cpu_s_per_batch_min': round(min(times), 3), 'cpu_s_per_batch_max': round(max(times), 3),
       'cpu_model': open('/proc/cpuinfo').read().split('model name')[1].split('\n')[0].strip(': '),
       'torch': torch.__version__}
print(json.dumps(res))
json.dump(res, open(os.path.join(W, 'result.json'), 'w'), indent=1)
