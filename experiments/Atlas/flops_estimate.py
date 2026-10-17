"""Compute cost of one training iteration of the planned networks, from nnU-Net's own plans (planner_sweep.py
output): instantiate the exact architecture on the 'meta' device, count conv MACs via hooks for one forward pass
at the planned patch size and batch size. Training step ~ 3x forward FLOPs (forward + 2x backward).
Converts to H100 time under stated utilisation assumptions. Usage: flops_estimate.py <plans_dir>"""
import sys, json, glob, os
import torch, torch.nn as nn
from nnunetv2.utilities.plans_handling.plans_handler import PlansManager
from nnunetv2.utilities.get_network_from_plans import get_network_from_plans
d = sys.argv[1]
for pf in sorted(glob.glob(os.path.join(d, 'p_*.json'))):
    name = os.path.basename(pf)[2:-5]
    if not any(k in name for k in ('ResEnc_60GB_iso', 'ResEnc_75GB_nat', 'ResEnc_60GB_nat', 'ResEncL_nat', 'ResEncXL_iso', 'plain_70GB_nat', 'ResEncL_iso')):
        continue
    pm = PlansManager(pf); cm = pm.get_configuration('3d_fullres')
    net = get_network_from_plans(cm.network_arch_class_name, cm.network_arch_init_kwargs, cm.network_arch_init_kwargs_req_import,
                                 1, 5, allow_init=False, deep_supervision=True).to('meta')
    macs = [0]
    def hook(m, i, o):
        k = m.weight.shape  # (out, in/groups, kd, kh, kw) for conv; (in, out, ...) for transposed
        if isinstance(m, nn.ConvTranspose3d):
            macs[0] += i[0].numel() * k[1] * k[2] * k[3] * k[4]
        else:
            macs[0] += o.numel() * k[1] * k[2] * k[3] * k[4]
    for m in net.modules():
        if isinstance(m, (nn.Conv3d, nn.ConvTranspose3d)): m.register_forward_hook(hook)
    ps = cm.patch_size; bs = cm.batch_size
    with torch.no_grad():
        net(torch.zeros((bs, 1, *ps), device='meta'))
    params = sum(p.numel() for p in net.parameters())
    fwd = 2 * macs[0]; step = 3 * fwd
    tflop_epoch = step * 250 / 1e12
    # H100 SXM dense bf16 peak ~989 TFLOP/s; nnU-Net 3D conv training typically reaches well below peak
    hrs = {u: tflop_epoch * 1000 / (989 * u) / 3600 for u in (0.15, 0.25, 0.40)}
    print(f"{name:22s} patch={ps} bs={bs} params={params/1e6:.1f}M fwd={fwd/1e12:.2f} TFLOP/iter "
          f"train-step={step/1e12:.2f} TFLOP; 1000 epochs = {tflop_epoch*1000/1e6:.1f} EFLOP -> H100-h at 15/25/40% util: "
          + ' / '.join(f'{v:.0f}' for v in hrs.values()))
