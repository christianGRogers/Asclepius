"""Load a fine-tune source checkpoint into a network **completely**, output heads included
(Round 6, A17a; Foxtrot F1).

nnU-Net's own ``-pretrained_weights`` (``nnunetv2.run.load_pretrained_weights``, 2.8.1) skips every
key containing ``.seg_layers.``: all deep-supervision output heads restart from random. That is
right for transfer to a new label set and wrong for our waves, which keep the same 4 + 1 classes.
This loader instead requires the source to match exactly and copies every tensor:

* the same configuration plans (spacing, patch, architecture, normalisation) and the same
  normalisation constants (the CT window, A16), compared field by field;
* the same output classes (``dataset.json`` labels, ``ignore`` aside: it is not an output channel);
* the same state-dict keys and shapes, loaded with ``strict=True``, then verified bitwise.

Needs torch only (not nnU-Net), so it is tested on CPU with a tiny network.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Optional

import torch

_PREFIXES = ("module.", "_orig_mod.")


def _strip(key: str) -> str:
    changed = True
    while changed:
        changed = False
        for p in _PREFIXES:
            if key.startswith(p):
                key, changed = key[len(p):], True
    return key


def _module(network):
    mod = getattr(network, "module", network)          # DDP
    return getattr(mod, "_orig_mod", mod)               # torch.compile


def output_labels(dataset_json: dict) -> dict:
    """The labels that are network outputs: everything but ``ignore``."""
    return {k: v for k, v in (dataset_json or {}).get("labels", {}).items() if k != "ignore"}


def _diff(a: dict, b: dict, prefix: str = "") -> list:
    out = []
    for k in sorted(set(a) | set(b)):
        if k not in a or k not in b:
            out.append(f"{prefix}{k}: only in {'source' if k in a else 'target'}")
        elif isinstance(a[k], dict) and isinstance(b[k], dict):
            out += _diff(a[k], b[k], f"{prefix}{k}.")
        elif a[k] != b[k]:
            out.append(f"{prefix}{k}: source {a[k]!r} != target {b[k]!r}")
    return out


def check_compatible(source_init_args: dict, plans: dict, configuration: str,
                     dataset_json: dict) -> None:
    """Raise ValueError unless the source checkpoint was trained with identical plans for
    ``configuration`` (and identical normalisation constants) and identical output classes."""
    src_plans = (source_init_args or {}).get("plans") or {}
    problems = []
    if source_init_args.get("configuration") not in (None, configuration):
        problems.append(f"configuration: source {source_init_args.get('configuration')!r} != "
                        f"target {configuration!r}")
    s_conf = (src_plans.get("configurations") or {}).get(configuration)
    t_conf = (plans.get("configurations") or {}).get(configuration)
    if s_conf is None or t_conf is None:
        problems.append(f"configuration {configuration!r} missing from source or target plans")
    else:
        problems += _diff(s_conf, t_conf, f"plans.configurations.{configuration}.")
    for key in ("foreground_intensity_properties_per_channel", "transpose_forward",
                "transpose_backward"):
        if src_plans.get(key) != plans.get(key):
            problems.append(f"plans.{key}: source {src_plans.get(key)!r} != "
                            f"target {plans.get(key)!r}")
    s_lab = output_labels(source_init_args.get("dataset_json"))
    t_lab = output_labels(dataset_json)
    if s_lab != t_lab:
        problems.append(f"output classes: source {s_lab} != target {t_lab}")
    if problems:
        raise ValueError("fine-tune source is not compatible with this training; refusing:\n  "
                         + "\n  ".join(problems[:20]))


def load_full_state(network, state_dict: dict) -> dict:
    """Copy every tensor of ``state_dict`` into ``network`` (strict; heads included) and verify
    that the result is bitwise identical. Returns a summary."""
    mod = _module(network)
    src = {_strip(k): v for k, v in state_dict.items()}
    target = mod.state_dict()
    missing = sorted(set(target) - set(src))
    unexpected = sorted(set(src) - set(target))
    shapes = sorted(k for k in set(src) & set(target)
                    if tuple(src[k].shape) != tuple(target[k].shape))
    if missing or unexpected or shapes:
        raise ValueError(f"state-dict keys differ: missing {missing[:5]}, unexpected "
                         f"{unexpected[:5]}, shape mismatch {shapes[:5]}; refusing")
    mod.load_state_dict(src, strict=True)
    after = mod.state_dict()
    bad = [k for k in src if not torch.equal(after[k].cpu(), src[k].cpu())]
    if bad:
        raise RuntimeError(f"{len(bad)} tensor(s) differ after loading, e.g. {bad[:3]}")
    heads = [k for k in src if ".seg_layers." in k]
    return {"n_tensors": len(src), "n_head_tensors": len(heads), "heads_loaded": bool(heads)}


def load_finetune_source(network, checkpoint_path, plans: dict, configuration: str,
                         dataset_json: dict, map_location: Optional[str] = "cpu") -> dict:
    """Check and load an nnU-Net checkpoint (``checkpoint_final.pth`` of the last accepted model)
    into ``network``. Returns a summary for the run's event stream."""
    path = Path(checkpoint_path)
    if not path.is_file():
        raise FileNotFoundError(f"fine-tune source checkpoint not found: {path}")
    ckpt = torch.load(str(path), map_location=map_location, weights_only=False)
    check_compatible(ckpt.get("init_args") or {}, plans, configuration, dataset_json)
    summary = load_full_state(network, ckpt["network_weights"])
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    summary.update(source=str(path), source_sha256=h.hexdigest(),
                   source_trainer=ckpt.get("trainer_name"),
                   source_epoch=ckpt.get("current_epoch"))
    return summary
