"""segtrain -- training pipeline for whole-body CT anatomical segmentation.

Layered so that the parts which must run on a laptop never import the parts that
need a GPU:

    config, labels, splits, convert, events, metrics   pure python + numpy/nibabel
    plans, trainer, preview, evaluate                  need nnU-Net / torch

Importing this package pulls in only the first group. The heavy modules are
imported lazily inside the CLI subcommands that need them, so `segtrain convert`
works on a machine with no torch installed.
"""

__version__ = "0.1.0"

__all__ = ["__version__"]
