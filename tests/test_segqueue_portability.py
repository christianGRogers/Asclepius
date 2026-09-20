"""The two constraints that make shared code shareable, enforced.

``src/segqueue/`` is imported by both halves of the labelling app, and they do
not run the same Python. The Girder plugin runs 3.11 in a container we build;
the Slicer extension runs whatever Slicer 5.8 bundles, which is 3.9, inside an
interpreter we do not control and cannot pip-install into. So the shared package
has two rules:

* **Standard library only.** ``pip install numpy`` is not available inside
  Slicer's Python, and vendoring a dependency into an extension archive is a
  supply chain nobody is auditing. A stray ``import requests`` in
  ``src/segqueue/`` passes every test on a developer's machine and every test in
  CI, and then fails on thirty laptops at once with ``ModuleNotFoundError``.
* **Python 3.9 syntax.** Same failure, earlier: a ``match`` statement in shared
  code is a ``SyntaxError`` at import, which in Slicer means the module does not
  appear in the module list at all.

Neither rule can be checked by importing the files -- this suite runs on 3.11,
where both violations import perfectly. So they are checked statically instead.

The 3.9 syntax rule also covers ``slicer/SegQueue/``, which runs in the same
interpreter, even though the stdlib rule does not: Slicer ships Qt, VTK and
``requests``, and the extension is entitled to use them.
"""

import ast
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SHARED = REPO / "src" / "segqueue"
EXTENSION = REPO / "slicer" / "SegQueue"

#: What Slicer's bundled Python provides beyond the standard library. The
#: extension may import these; the shared package may not. Kept short and by
#: hand -- an addition here is a claim that Slicer 5.8 ships it, and that claim
#: should be checked against a real Slicer rather than assumed.
SLICER_PROVIDES = {"slicer", "qt", "ctk", "vtk", "requests", "numpy", "SegQueueLib"}

#: The shared package's own modules, which are of course importable from within
#: it. Derived rather than listed so that a new module needs no edit here.
OWN = {"segqueue"} | {path.stem for path in SHARED.glob("*.py")}

PY39 = (3, 9)


def _modules(directory):
    return sorted(p for p in directory.rglob("*.py") if "__pycache__" not in p.parts)


def _ids(paths):
    return [str(p.relative_to(REPO)).replace("\\", "/") for p in paths]


def _toplevel_imports(tree):
    """Every module name the file imports, as ``(root_name, lineno)``.

    Relative imports are skipped: ``from . import x`` cannot reach outside the
    package and so cannot break either rule.
    """
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                found.append((alias.name.split(".")[0], node.lineno))
        elif isinstance(node, ast.ImportFrom):
            if node.level:  # from . / from .. -- inside the package
                continue
            if node.module:
                found.append((node.module.split(".")[0], node.lineno))
    return found


@pytest.mark.parametrize("path", _modules(SHARED), ids=_ids(_modules(SHARED)))
def test_the_shared_package_imports_only_the_standard_library(path):
    """A third-party import here is a ``ModuleNotFoundError`` inside Slicer.

    Nothing else catches it: the server installs whatever the import needs, and
    so does CI, so the module works everywhere except the one interpreter that
    cannot be fixed after the fact.
    """
    if not hasattr(sys, "stdlib_module_names"):  # pragma: no cover - 3.9 runner
        pytest.skip("sys.stdlib_module_names needs Python 3.10+")

    tree = ast.parse(path.read_text(encoding="utf-8"))
    outside = [
        (name, lineno)
        for name, lineno in _toplevel_imports(tree)
        if name not in sys.stdlib_module_names and name not in OWN
    ]
    assert not outside, (
        "{} imports outside the standard library: {}.\n"
        "src/segqueue is imported by the Slicer extension, whose Python cannot "
        "be pip-installed into. Move the dependency to the caller.".format(
            path.relative_to(REPO),
            ", ".join("{} (line {})".format(n, ln) for n, ln in sorted(outside)),
        )
    )


@pytest.mark.parametrize(
    "path",
    _modules(SHARED) + _modules(EXTENSION),
    ids=_ids(_modules(SHARED) + _modules(EXTENSION)),
)
def test_everything_slicer_imports_parses_as_python_39(path):
    """Slicer 5.8 bundles Python 3.9, and a SyntaxError there is a missing module.

    Not a traceback an annotator can report -- the module simply does not appear
    in Slicer's module list, which looks like a failed installation.
    """
    source = path.read_text(encoding="utf-8")
    try:
        ast.parse(source, filename=str(path), feature_version=PY39)
    except SyntaxError as exc:
        pytest.fail(
            "{} is not valid Python 3.9 (line {}): {}\n"
            "Slicer 5.8 bundles 3.9; this file has to parse there.".format(
                path.relative_to(REPO), exc.lineno, exc.msg
            )
        )


@pytest.mark.parametrize(
    "path",
    _modules(SHARED) + _modules(EXTENSION),
    ids=_ids(_modules(SHARED) + _modules(EXTENSION)),
)
def test_no_pep604_unions_where_python_39_would_evaluate_them(path):
    """``int | None`` parses on 3.9 and then raises ``TypeError`` at import.

    ``feature_version`` cannot catch this one: the syntax is legal in every
    version, and only the *evaluation* is new. ``from __future__ import
    annotations`` makes annotations strings and defuses it, so files that opt in
    are exempt -- which is why ``src/segqueue`` uses it and this check is mostly
    here for the extension, which does not.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))

    futures = {
        alias.name
        for node in tree.body
        if isinstance(node, ast.ImportFrom) and node.module == "__future__"
        for alias in node.names
    }
    if "annotations" in futures:
        pytest.skip("annotations are strings here, so PEP 604 is inert")

    annotations = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.AnnAssign, ast.arg)) and node.annotation:
            annotations.append(node.annotation)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.returns:
            annotations.append(node.returns)

    offenders = [
        ann.lineno
        for ann in annotations
        for sub in ast.walk(ann)
        if isinstance(sub, ast.BinOp) and isinstance(sub.op, ast.BitOr)
    ]
    assert not offenders, (
        "{} uses PEP 604 unions (X | Y) in annotations at line(s) {}.\n"
        "Python 3.9 evaluates those at import and raises TypeError. Use "
        "Optional[X], or add `from __future__ import annotations`.".format(
            path.relative_to(REPO), ", ".join(str(n) for n in sorted(set(offenders)))
        )
    )
