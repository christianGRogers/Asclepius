"""Activation-memory model of the planned networks: run one training forward pass of the exact nnU-Net
architecture (from the plans files) on PyTorch's 'meta' device at the planned patch x batch, and sum the bytes
of every tensor autograd saves for backward (torch.autograd.graph.saved_tensors_hooks). Adds parameter + gradient
+ SGD-momentum memory. fp32 throughout (meta autocast is not available), so this is the fp32 bound; nnU-Net
trains with autocast (fp16/bf16 convs, fp32 norms), which saves less. Also prints the planner's own VRAM estimate.
Usage: activation_memory.py <plans_dir>"""
import sys, glob, os
import torch, torch.nn as nn
from nnunetv2.utilities.plans_handling.plans_handler import PlansManager
from nnunetv2.utilities.get_network_from_plans import get_network_from_plans
d = sys.argv[1]
for name in ['ResEnc_60GB_iso', 'ResEncXL_iso', 'ResEncL_iso', 'ResEnc_60GB_nat', 'plain_70GB_nat']:
    pm = PlansManager(os.path.join(d, f'p_{name}.json')); cm = pm.get_configuration('3d_fullres')
    net = get_network_from_plans(cm.network_arch_class_name, cm.network_arch_init_kwargs, cm.network_arch_init_kwargs_req_import,
                                 1, 5, allow_init=False, deep_supervision=True).to('meta')
    net.train()
    saved = {'b': 0, 'n': 0, 'by_dtype': {}}
    seen = set(); keep = []
    def pack(t):
        b = t.numel() * t.element_size()
        saved['b'] += b; saved['n'] += 1
        if id(t) not in seen:  # same tensor object saved by several ops is stored once
            seen.add(id(t)); saved['u'] = saved.get('u', 0) + b; keep.append(t)
        return t
    def unpack(t): return t
    ps = cm.patch_size; bs = cm.batch_size
    x = torch.zeros((bs, 1, *ps), device='meta', requires_grad=False)
    with torch.autograd.graph.saved_tensors_hooks(pack, unpack):
        out = net(x)
    outs = out if isinstance(out, (list, tuple)) else [out]
    out_b = sum(o.numel() * 4 for o in outs)
    params = sum(p.numel() for p in net.parameters())
    pgm = params * 4 * 3  # weights, grads, momentum
    gib = 1024 ** 3
    print(f"{name:16s} patch={ps} bs={bs} saved-for-backward(fp32)={saved['b']/gib:.1f} GiB in {saved['n']} tensors (unique objects {saved['u']/gib:.1f} GiB); "
          f"outputs {out_b/gib:.1f} GiB; params+grad+momentum {pgm/gib:.2f} GiB; "
          f"total fp32 bound {(saved['b']+out_b+pgm)/gib:.1f} GiB")
