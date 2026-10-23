"""A fresh install points at the project's server, janus (#99).

The Server field used to start as ``https://segqueue.example.edu``, a placeholder
nobody ever saw while a saved setting overrode it, and every fresh install got.
``SegQueue14.py`` imports Slicer, so the default and its helper are lifted out of
the parsed module and run here; the ``install-anywhere`` job checks the real
field on a fresh Slicer.
"""

import ast
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
MODULE = REPO / "slicer" / "SegQueue14" / "SegQueue14.py"
JANUS = "https://janus.bradensbay.com"
NAMES = {"_SETTING_SERVER", "_LIVE_SETTING_SERVER", "DEFAULT_SERVER_URL", "initialServerUrl"}


def _helper():
    tree = ast.parse(MODULE.read_text(encoding="utf-8"))
    keep = []
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id in NAMES for t in node.targets):
            keep.append(node)
        elif isinstance(node, ast.FunctionDef) and node.name in NAMES:
            keep.append(node)
    namespace = {}
    exec(compile(ast.Module(body=keep, type_ignores=[]), str(MODULE), "exec"), namespace)
    assert NAMES <= set(namespace), NAMES - set(namespace)
    return namespace


def _settings(saved):
    return lambda key, default=None: saved.get(key, default)


def test_the_default_is_janus():
    assert _helper()["DEFAULT_SERVER_URL"] == JANUS


def test_a_fresh_install_shows_janus():
    assert _helper()["initialServerUrl"](_settings({})) == JANUS


@pytest.mark.parametrize("saved, shown", [
    ({"SegQueue14/serverUrl": "https://mine.example"}, "https://mine.example"),
    ({"SegQueue/serverUrl": "https://from-0.13.example"}, "https://from-0.13.example"),
    ({"SegQueue14/serverUrl": "https://mine.example",
      "SegQueue/serverUrl": "https://from-0.13.example"}, "https://mine.example"),
])
def test_a_saved_server_still_wins(saved, shown):
    assert _helper()["initialServerUrl"](_settings(saved)) == shown


def test_the_server_field_starts_from_the_helper():
    source = MODULE.read_text(encoding="utf-8")
    assert "qt.QLineEdit(initialServerUrl(slicer.util.settingsValue))" in source


def test_nothing_an_annotator_installs_carries_a_placeholder_server():
    shipped = [p for root in ("slicer/SegQueue14", "src/segqueue14", "src/segqueue")
               for p in (REPO / root).rglob("*") if p.suffix in (".py", ".md", ".ui", ".json")]
    shipped.append(REPO / "slicer" / "install-segqueue.py")
    offenders = [str(p.relative_to(REPO)) for p in shipped
                 if "example.edu" in p.read_text(encoding="utf-8", errors="ignore")]
    assert offenders == []


def test_the_project_server_is_the_one_the_deploy_docs_name():
    assert JANUS.split("//")[1] in (REPO / "deploy" / "README.md").read_text(encoding="utf-8")
