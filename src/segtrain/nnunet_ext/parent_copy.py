"""Janus 1-F's warm start: Janus 0 loaded with its output heads grown from 5 to 13 by parent copy
(F-A2).

A17a's loader (:mod:`segtrain.nnunet_ext.finetune_load`) requires identical output classes. Janus
1-F has 13 where Janus 0 has 5, so here:

* the plans and normalisation must still be identical (``check_compatible``, with the target's
  labels replaced by the source's for that comparison only), and the target's classes must be
  exactly ``configs/janus1/j1f_parents.json``'s, with ``ignore`` 13;
* every non-head tensor is loaded strictly and verified bitwise;
* every ``decoder.seg_layers.<i>`` head (deep supervision included) becomes: a class Janus 0 has
  keeps its row, a new class copies its parent's row, and every channel of a territory gets the
  parent's bias minus log(k), so each territory's softmax mass is Janus 0's probability of it
  (experiments/Delta/j1f_r1/parent_copy.py);
* :func:`step0_identity` then checks, on a real input, that the 13-channel territory sums equal
  Janus 0's softmax within 1e-5 and that the hierarchical decode's territory equals Janus 0's
  argmax. The trainer refuses otherwise.

Torch only (not nnU-Net), so it is tested on CPU with a tiny network.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Optional

import torch

from segtrain.nnunet_ext.finetune_load import _module, _strip, check_compatible, output_labels
from segtrain.nnunet_ext.janus1f_rules import F_GROUPS

IDENTITY_TOL = 1e-5


def load_parents(path) -> dict:
    with open(path) as fh:
        p = json.load(fh)
    src, tgt = p["source_classes"], p["target_classes"]
    if tgt[: len(src)] != src:
        raise ValueError("j1f_parents.json: target classes must extend the source classes")
    for c in tgt[len(src) :]:
        if p["parent"].get(c) not in src:
            raise ValueError(f"j1f_parents.json: {c} has no parent among the source classes")
    return p


def source_index(p: dict) -> list:
    src = p["source_classes"]
    return [src.index(c) if c in src else src.index(p["parent"][c]) for c in p["target_classes"]]


def bias_offset(p: dict) -> list:
    idx = source_index(p)
    return [-math.log(idx.count(i)) for i in idx]


def check_classes(p: dict, source_dataset_json: dict, target_dataset_json: dict) -> None:
    s = output_labels(source_dataset_json)
    t = output_labels(target_dataset_json)
    want_s = {c: i for i, c in enumerate(p["source_classes"])}
    want_t = {c: i for i, c in enumerate(p["target_classes"])}
    if s != want_s:
        raise ValueError(f"source classes {s} are not j1f_parents.json's {want_s}")
    if t != want_t:
        raise ValueError(f"target classes {t} are not j1f_parents.json's {want_t}")
    ign = (target_dataset_json.get("labels") or {}).get("ignore")
    if ign != len(want_t):
        raise ValueError(
            f"target ignore label {ign!r} is not {len(want_t)} (F-A29: ignore 13 on disk)"
        )


def grow_heads(state_dict: dict, p: dict) -> dict:
    """Source state dict -> the same with every ``.seg_layers.`` weight/bias grown by parent
    copy."""
    idx = torch.tensor(source_index(p))
    off = torch.tensor(bias_offset(p), dtype=torch.float64)
    out = {}
    for k, v in state_dict.items():
        if ".seg_layers." in k and k.endswith(".weight"):
            out[k] = v.index_select(0, idx.to(v.device)).clone()
        elif ".seg_layers." in k and k.endswith(".bias"):
            b = v.index_select(0, idx.to(v.device)).to(torch.float64) + off.to(v.device)
            out[k] = b.to(v.dtype)
        else:
            out[k] = v
    return out


def load_parent_copy(
    network,
    checkpoint_path,
    parents_path,
    plans: dict,
    configuration: str,
    dataset_json: dict,
    map_location: Optional[str] = "cpu",
) -> dict:
    """Check and load Janus 0's checkpoint into a 13-head ``network``. Returns a summary (and keeps
    the source heads in ``summary['_source_heads']`` for :func:`step0_identity`)."""
    path = Path(checkpoint_path)
    if not path.is_file():
        raise FileNotFoundError(f"parent-copy source checkpoint not found: {path}")
    p = load_parents(parents_path)
    ckpt = torch.load(str(path), map_location=map_location, weights_only=False)
    init = dict(ckpt.get("init_args") or {})
    check_classes(p, init.get("dataset_json") or {}, dataset_json)
    # plans and normalisation identical; the class lists were checked above
    same_labels = dict(
        dataset_json, labels=dict((init.get("dataset_json") or {}).get("labels") or {})
    )
    check_compatible(init, plans, configuration, same_labels)
    src = {_strip(k): v for k, v in ckpt["network_weights"].items()}
    grown = grow_heads(src, p)
    mod = _module(network)
    target = mod.state_dict()
    missing = sorted(set(target) - set(grown))
    unexpected = sorted(set(grown) - set(target))
    shapes = sorted(
        k for k in set(grown) & set(target) if tuple(grown[k].shape) != tuple(target[k].shape)
    )
    if missing or unexpected or shapes:
        raise ValueError(
            f"state-dict keys differ: missing {missing[:5]}, unexpected {unexpected[:5]}, "
            f"shape mismatch {shapes[:5]}; refusing"
        )
    mod.load_state_dict(grown, strict=True)
    after = mod.state_dict()
    bad = [k for k in grown if not torch.equal(after[k].cpu(), grown[k].cpu())]
    if bad:
        raise RuntimeError(f"{len(bad)} tensor(s) differ after loading, e.g. {bad[:3]}")
    heads = sorted(k for k in src if ".seg_layers." in k)
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return {
        "n_tensors": len(grown),
        "n_head_tensors": len(heads),
        "n_body_bitwise": len(grown) - len(heads),
        "heads": f"{len(p['source_classes'])} -> {len(p['target_classes'])} by parent copy",
        "source": str(path),
        "source_sha256": h.hexdigest(),
        "source_epoch": ckpt.get("current_epoch"),
        "_source_heads": {k: src[k] for k in heads},
    }


def last_head_name(network) -> str:
    """The full-resolution head: the last ``decoder.seg_layers.<i>``."""
    mod = _module(network)
    names = [
        n
        for n, _ in mod.named_modules()
        if n.startswith("decoder.seg_layers.") and n.count(".") == 2
    ]
    if not names:
        raise ValueError("network has no decoder.seg_layers")
    return max(names, key=lambda n: int(n.rsplit(".", 1)[1]))


def step0_identity(network, x, source_heads: dict, tol: float = IDENTITY_TOL) -> dict:
    """On input ``x`` (a real training patch), Janus 0's full-resolution head applied to the same
    decoder features gives Janus 0's softmax (the body is bitwise Janus 0's). The 13-channel
    territory sums must equal it within ``tol``, and the hierarchical decode's territory must equal
    its argmax. Raises otherwise."""
    mod = _module(network)
    name = last_head_name(network)
    head = dict(mod.named_modules())[name]
    feats = {}
    hook = head.register_forward_hook(lambda m, inp, out: feats.__setitem__("x", inp[0].detach()))
    was_training = mod.training
    mod.eval()
    try:
        with torch.no_grad():
            mod(x)
    finally:
        hook.remove()
        mod.train(was_training)
    f = feats["x"].double()
    w13, b13 = head.weight.detach().double(), head.bias.detach().double()
    w0, b0 = (
        source_heads[name + ".weight"].double().to(f.device),
        source_heads[name + ".bias"].double().to(f.device),
    )
    conv = torch.nn.functional.conv3d if f.dim() == 5 else torch.nn.functional.conv2d
    p13 = torch.softmax(conv(f, w13, b13), 1)
    p0 = torch.softmax(conv(f, w0, b0), 1)
    sums = torch.stack([p13[:, list(g)].sum(1) for g in F_GROUPS], 1)
    err = float((sums - p0).abs().max())
    terr = sums.argmax(1)
    agree = float((terr == p0.argmax(1)).double().mean())
    out = {
        "max_abs_territory_error": err,
        "territory_argmax_agreement": agree,
        "tol": tol,
        "head": name,
        "voxels": int(terr.numel()),
    }
    if err > tol or agree != 1.0:
        raise RuntimeError(
            f"step-0 identity fails: territory sums differ from Janus 0's softmax by {err:.2e} "
            f"(tol {tol}), territory argmax agreement {agree:.6f}; refusing to train"
        )
    return out
