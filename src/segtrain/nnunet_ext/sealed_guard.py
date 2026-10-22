"""The trainer-side A14 guard: refuse to train when any training or validation identifier maps to
a sealed case (or to no case at all). Torch-free. The data path (proxy, convert, splits) already
refuses sealed cases; this is the last check, on what nnU-Net is actually about to read, under
every name a case travels under (``c0002``, ``imagecas_0003``, ``c0002__r2``; Echo D2).

``SEGTRAIN_SEALED_LIST`` points at another sealed-list JSON; the default is the repository's
``trillium/sealed_test.json``. A missing list is an error, never a pass.

The D27 pool seal (:mod:`segtrain.pool_seal`, ``configs/segqueue14/sealed-pool-2026-10.json``) is
checked first, so a sealed SegQueue14 pool volume is refused by name (D27) rather than only as an
unmappable A14 name. ``SEGTRAIN_POOL_SEAL`` points at the seal file outside a checkout; it must be
the pinned file. There is no exclude mode here: this is the last line of defence."""

from __future__ import annotations

import os
from typing import Iterable, Optional


def refuse_sealed(identifiers: Iterable[str], sealed: Optional[set] = None,
                  pool_seal=None) -> int:
    """Raise RuntimeError if any identifier is sealed (A14 or D27) or unmappable; else the count.

    A D27 pool-sealed identifier raises :class:`segtrain.pool_seal.SealedPoolError` (a
    RuntimeError). ``pool_seal`` is a loaded :class:`~segtrain.pool_seal.PoolSeal`; default, the
    pinned seal file."""
    from segtrain.pool_seal import apply as apply_pool_seal
    from segtrain.proxy import load_sealed, sealed_reason

    ids = list(identifiers)
    apply_pool_seal(ids, mode="refuse", what="training (nnU-Net train/val identifiers)",
                    seal=pool_seal)
    if sealed is None:
        sealed = load_sealed(os.environ.get("SEGTRAIN_SEALED_LIST") or None)
    bad = [why for why in (sealed_reason(i, set(sealed)) for i in ids) if why]
    if bad:
        raise RuntimeError(f"refusing to train: {len(bad)} identifier(s) are sealed or unmappable "
                           f"(A14), e.g. {bad[:3]}")
    return len(ids)
