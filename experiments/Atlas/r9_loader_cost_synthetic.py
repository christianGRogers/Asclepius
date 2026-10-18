"""Round 9 copy of loader_cost.py on a synthetic volume (no CT here).
How many CPU data-loader workers does the master config need? Time nnU-Net v2.8.1's own training transform
pipeline (nnUNetTrainer.get_training_transforms, mirroring off, deep supervision scales of the 7-stage ResEnc,
4 foreground labels) on one sample at the planned patch, single thread, on this machine's CPU. nnU-Net's loader
first crops a larger patch (rotation padding: get_patch_size with +-30 deg, scaling 0.85-1.25) and the
SpatialTransform resamples it to the final patch only when rotation/scaling fire (p=0.2 each), so the time is a
mixture; we time many samples and report mean/p90. Input: a real CT crop resampled to 0.5 mm (c0050), labels synthetic.
Usage: loader_cost.py <n_samples> <patch e.g. 256,256,256>"""
import sys, time, os
import numpy as np, torch, nibabel as nib
from scipy import ndimage as ndi
torch.set_num_threads(1)
from nnunetv2.training.nnUNetTrainer.nnUNetTrainer import nnUNetTrainer
from nnunetv2.training.data_augmentation.compute_initial_patch_size import get_patch_size
n = int(sys.argv[1]); ps = tuple(int(x) for x in sys.argv[2].split(','))
rot = (-30. / 360 * 2. * np.pi, 30. / 360 * 2. * np.pi)
init = get_patch_size(ps, rot, rot, rot, (0.85, 1.25))
ds_scales = [[1, 1, 1], [0.5] * 3, [0.25] * 3, [0.125] * 3, [0.0625] * 3, [0.03125] * 3]
tr = nnUNetTrainer.get_training_transforms(ps, rot, ds_scales, None, False, None, False, (1, 2, 3, 4), None, None)
# no CT in this sandbox: a synthetic volume of the median ImageCAS shape at 0.5 mm (transform cost does not depend on content)
img = np.random.default_rng(1).normal(0, 1, (275, 358, 358)).astype(np.float32)
print('volume', img.shape, 'final patch', ps, 'initial (padded) patch', [int(x) for x in init], flush=True)
rng = np.random.default_rng(0); ts = []
for i in range(n):
    lb = [rng.integers(0, max(s - p, 0) + 1) for s, p in zip(img.shape, init)]
    sl = tuple(slice(l, l + p) for l, p in zip(lb, init))
    x = img[sl]; pad = [(0, p - s) for s, p in zip(x.shape, init)]
    x = np.pad(x, pad)
    seg = np.zeros_like(x, dtype=np.int16); c = [s // 2 for s in x.shape]
    seg[c[0] - 20:c[0] + 20, c[1] - 3:c[1] + 3, c[2] - 3:c[2] + 3] = 2
    t0 = time.time()
    out = tr(**{'image': torch.from_numpy(x[None]).float(), 'segmentation': torch.from_numpy(seg[None])})
    ts.append(time.time() - t0)
    print(i, round(ts[-1], 2), flush=True)
ts = np.array(ts)
print(f'per-sample transform time: mean {ts.mean():.2f} s, median {np.median(ts):.2f}, p90 {np.percentile(ts, 90):.2f}, max {ts.max():.2f} (n={n})')
