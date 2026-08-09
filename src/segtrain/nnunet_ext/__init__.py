"""Trainer classes discovered by nnU-Net through the ``nnUNet_extTrainer`` path.

nnU-Net searches only its own package for trainer classes unless
``nnUNet_extTrainer`` points at another directory. It imports what it finds
there as *top-level* modules, so modules in this package must use absolute
imports (``from segtrain.events import ...``) rather than relative ones -- a
relative import would fail once nnU-Net imports the file as
``nnUNetTrainer_segtrain`` instead of ``segtrain.nnunet_ext.nnUNetTrainer_segtrain``.

``segtrain.plans.configure_nnunet_env`` points the variable here automatically.
"""
