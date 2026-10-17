"""R0 pre-measurement on CPU: nnU-Net v2.8.1's OWN training data pipeline for the master configuration
(nnUNetTrainerNoMirroring, plans nnUNetResEncUNetPlans_60G_iso05: 256^3, batch 2, 0.5 mm, fixed window), on real
preprocessed cases (r0cpu_setup.py). Measures batches/s and CPU-seconds per batch with nnUNet_n_proc_DA = 0
(single-threaded: pure per-batch cost) and with k worker processes, plus per-worker RSS.
Usage: loader_benchmark.py <workdir> <n_proc_DA> <n_batches>"""
import os, sys, time, json
W, nproc, nb = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
os.environ.update(nnUNet_raw=W + '/raw', nnUNet_preprocessed=W + '/pp', nnUNet_results=W + '/res', nnUNet_n_proc_DA=str(nproc))
import torch, psutil, numpy as np
torch.set_num_threads(1)
from batchgenerators.utilities.file_and_folder_operations import load_json
from nnunetv2.training.nnUNetTrainer.variants.data_augmentation.nnUNetTrainerNoMirroring import nnUNetTrainerNoMirroring
pp = W + '/pp/Dataset712_CCTAr0'
plans = load_json(pp + '/nnUNetResEncUNetPlans_60G_iso05.json'); plans['continue_training'] = False; dj = load_json(pp + '/dataset.json')
tr = nnUNetTrainerNoMirroring(plans, '3d_fullres', 0, dj, device=torch.device('cpu'))
tr._set_batch_size_and_oversample()
t0 = time.time(); gen_tr, gen_val = tr.get_dataloaders(); t_start = time.time() - t0
proc = psutil.Process()
cpu0 = sum(p.cpu_times().user + p.cpu_times().system for p in [proc] + proc.children(recursive=True))
ts = []; t0 = time.time()
for i in range(nb):
    t1 = time.time(); b = next(gen_tr); ts.append(time.time() - t1)
    if i == 0:
        shp = tuple(b['data'].shape); tshp = [tuple(t.shape) for t in b['target']]
wall = time.time() - t0
kids = proc.children(recursive=True)
cpu1 = sum(p.cpu_times().user + p.cpu_times().system for p in [proc] + kids)
rss = [p.memory_info().rss / 2**30 for p in kids]
res = dict(n_proc_DA=nproc, n_batches=nb, batch_shape=shp, target_shapes=tshp[:2], startup_s=round(t_start, 1),
           wall_s=round(wall, 1), batches_per_s=nb / wall, s_per_batch_mean=float(np.mean(ts)), s_per_batch_median=float(np.median(ts)),
           cpu_s_total=round(cpu1 - cpu0, 1), cpu_s_per_batch=(cpu1 - cpu0) / nb,
           main_rss_gib=proc.memory_info().rss / 2**30, worker_rss_gib=[round(r, 2) for r in rss], load_avg=os.getloadavg())
print(json.dumps(res), flush=True)
os._exit(0)
