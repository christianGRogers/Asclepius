"""The trainer-side A14 guard: refuse to train when any training or validation identifier maps to
a sealed case (or to no case at all). Torch-free. The data path (proxy, convert, splits) already
refuses sealed cases; this is the last check, on what nnU-Net is actually about to read, under
every name a case travels under (``c0002``, ``imagecas_0003``, ``c0002__r2``; Echo D2).

``SEGTRAIN_SEALED_LIST`` points at another sealed-list JSON; the default is the repository's
``trillium/sealed_test.json``. A missing list is an error, never a pass."""

from __future__ import annotations

import os
from typing import Iterable, Optional


def refuse_sealed(identifiers: Iterable[str], sealed: Optional[set] = None) -> int:
    """Raise RuntimeError if any identifier is sealed or unmappable; else return the count."""
    from segtrain.proxy import load_sealed, sealed_reason

    if sealed is None:
        sealed = load_sealed(os.environ.get("SEGTRAIN_SEALED_LIST") or None)
    ids = list(identifiers)
    bad = [why for why in (sealed_reason(i, set(sealed)) for i in ids) if why]
    if bad:
        raise RuntimeError(f"refusing to train: {len(bad)} identifier(s) are sealed or unmappable "
                           f"(A14), e.g. {bad[:3]}")
    return len(ids)
