"""The one place the Janus-M read queue asks "is this a coronary hold-out?".

JA12 makes a single Janus-M guard (issue #138) the thing every Janus-M fetch,
loader and launcher calls first. Until it merges, this module is a conservative
interim check, and the read queue, its populate tool and the seed launcher call
:func:`refuse` and nothing else -- so wiring the JA12 guard in is a change here only.

What the interim check refuses, for ImageCAS-X ids (``cNNNN``):

* the A14 sealed 100, the open ImageCAS-X test cases and the development cases
  excluded from it (``trillium/icx4/sealed_test.json``);
* anything not in the ImageCAS-X **train** list of the committed ``splits.json``
  (so val 80 and test 160 are refused). Janus-M's seal and decision set are drawn
  from train only (JA5, JA6);

and for any other name, the coronary pool seal and its patients
(``segtrain.pool_seal``, which refuses by patient). A name is refused, never
silently dropped: the whole call fails, as JA12 asks.

Stdlib only.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Iterable, List, Optional, Set

#: Repository-relative inputs. Read, never written.
SEALED_TEST_RELPATH = "trillium/icx4/sealed_test.json"
SPLITS_RELPATH = "trillium-results/icx14/results/splits.json"
#: Environment variable naming the repository root, for an installed package.
ROOT_ENV = "JANUSM_REPO_ROOT"

_CASE_ID = re.compile(r"^c\d{4}$")


class HoldoutError(RuntimeError):
    """A coronary hold-out was asked for. The whole step is refused."""


def repo_root() -> Path:
    env = os.environ.get(ROOT_ENV)
    if env:
        return Path(env)
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / SEALED_TEST_RELPATH).is_file():
            return parent
    raise HoldoutError(
        f"cannot find {SEALED_TEST_RELPATH}; set {ROOT_ENV} to an Asclepius checkout")


def _load(root: Path, rel: str):
    path = root / rel
    if not path.is_file():
        raise HoldoutError(f"{path} is missing; refusing rather than guessing")
    return json.loads(path.read_text(encoding="utf-8"))


class InterimGuard:
    """The interim check, with its inputs loaded once."""

    def __init__(self, root: Optional[Path] = None):
        root = Path(root) if root else repo_root()
        sealed = _load(root, SEALED_TEST_RELPATH)
        self.sealed: Set[str] = set()
        for key in ("sealed_icx_test", "open_icx_test", "excluded_dev_cases_in_test",
                    "sealed_quality0", "excluded_dev_cases_in_quality0"):
            value = sealed.get(key) or []
            if isinstance(value, dict):
                value = value.get("cases") or []
            self.sealed.update(str(v) for v in value)
        splits = _load(root, SPLITS_RELPATH)
        self.train: Set[str] = set(splits["train"])
        self.not_train: Set[str] = set(splits.get("val", [])) | set(splits.get("test", []))

    def reasons(self, name: str) -> List[str]:
        name = str(name).strip()
        out = []
        if _CASE_ID.match(name):
            if name in self.sealed:
                out.append("A14 sealed / ImageCAS-X test (sealed_test.json)")
            if name in self.not_train:
                out.append("ImageCAS-X val or test split")
            elif name not in self.train:
                out.append("not in the ImageCAS-X train list")
            return out
        from segtrain import pool_seal

        if pool_seal.load_pool_seal().is_sealed(name):
            out.append("coronary pool seal (D27/D32)")
        else:
            # Not an ImageCAS-X id and not sealed: still not a Janus-M read case.
            out.append("not an ImageCAS-X case id")
        return out


_GUARD: Optional[InterimGuard] = None


def guard() -> InterimGuard:
    global _GUARD
    if _GUARD is None:
        _GUARD = InterimGuard()
    return _GUARD


def refuse(names: Iterable[str], what: str = "this step") -> None:
    """Raise :class:`HoldoutError` if any name is a coronary hold-out (or not a
    Janus-M read case at all). Returns None when every name is clear."""
    g = guard()
    hits = []
    for name in names:
        why = g.reasons(name)
        if why:
            hits.append(f"{name}: {'; '.join(why)}")
    if hits:
        shown = "\n  ".join(hits[:10])
        more = f"\n  ... and {len(hits) - 10} more" if len(hits) > 10 else ""
        raise HoldoutError(f"{what} refused: {len(hits)} coronary hold-out(s) or "
                           f"non-Janus-M case(s):\n  {shown}{more}")
