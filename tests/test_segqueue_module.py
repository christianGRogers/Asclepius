"""Static checks on the Slicer module, for the mistakes pytest cannot otherwise reach.

`SegQueue.py` imports Qt, VTK and Slicer, so it cannot be imported here and none
of it is covered by the rest of the suite. That is tolerable for behaviour --
there is no CT and no renderer on a laptop -- but not for *typos*, because a
panel is a web of ``self.something()`` calls wired to buttons, and Qt swallows
the exception when one of them is wrong.

The symptom is the worst kind: the button does nothing. No error on screen, no
crash, just a dead control and an annotator who assumes they misunderstood the
tool. It has happened once already -- a method was deleted in a refactor and one
call to it survived, and every vessel button in the panel stopped responding.
``pyflakes`` cannot catch it, because ``self.foo`` is an attribute access and
attributes are not resolvable statically in general.

They are resolvable *here*, though, because this module is one file of plain
classes with no metaclasses, no ``setattr`` and no mixins. So: parse it, and
check every ``self.x`` it reads is something the same class defines.
"""

import ast
import io
from pathlib import Path

import pytest

MODULE = (Path(__file__).resolve().parents[1]
          / "slicer" / "SegQueue" / "SegQueue.py")

#: Attributes that come from Slicer's own ``ScriptedLoadableModule*`` base
#: classes rather than from this file. Deliberately tiny and listed by hand: the
#: point of the check is to notice new unresolved names, so anything added here
#: should be a base-class attribute somebody has confirmed exists.
INHERITED = {
    "parent",       # ScriptedLoadableModule: the qSlicerAbstractCoreModule
    "layout",       # ScriptedLoadableModuleWidget: the panel's own QVBoxLayout
    "developerMode",
}


def _module_tree():
    return ast.parse(io.open(MODULE, encoding="utf-8").read())


def _self_attributes(classdef):
    """(defined, used) attribute names for one class.

    ``defined`` counts methods and anything ever assigned to ``self``; ``used``
    maps each attribute read to the first line that reads it.
    """
    defined, used = set(), {}
    for node in ast.walk(classdef):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            defined.add(node.name)
        if (isinstance(node, ast.Attribute)
                and isinstance(node.value, ast.Name) and node.value.id == "self"):
            if isinstance(node.ctx, ast.Store):
                defined.add(node.attr)
            elif isinstance(node.ctx, ast.Load):
                used.setdefault(node.attr, node.lineno)
    return defined, used


def _classes():
    return [n for n in ast.walk(_module_tree()) if isinstance(n, ast.ClassDef)]


def test_the_module_parses():
    assert _module_tree() is not None


@pytest.mark.parametrize("classdef", _classes(), ids=lambda c: c.name)
def test_every_self_attribute_the_class_reads_is_one_it_defines(classdef):
    """No call to a method that no longer exists.

    A refactor that deletes a method and misses one call site produces a panel
    control that silently does nothing, which is indistinguishable from a
    misunderstood tool and is not caught by any other check here.
    """
    defined, used = _self_attributes(classdef)
    missing = {name: line for name, line in used.items()
               if name not in defined and name not in INHERITED}
    assert not missing, (
        "{} reads attributes it never defines: {}".format(
            classdef.name,
            ", ".join("self.{} (line {})".format(name, line)
                      for name, line in sorted(missing.items(),
                                               key=lambda kv: kv[1]))))


def test_every_widget_signal_is_connected_to_something_that_exists():
    """``x.connect(self.onThing)`` where ``onThing`` was renamed or removed.

    The same failure as above and the same symptom, but worth asserting on its
    own: these are exactly the lines that turn into dead buttons, and naming
    them in the failure message is more use than a list of attributes.
    """
    widget = next(c for c in _classes() if c.name == "SegQueueWidget")
    defined, _ = _self_attributes(widget)

    handlers = []
    for node in ast.walk(widget):
        if not (isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr in ("connect", "clicked")):
            continue
        for arg in node.args:
            # bare  self.onThing
            if (isinstance(arg, ast.Attribute)
                    and isinstance(arg.value, ast.Name) and arg.value.id == "self"):
                handlers.append((arg.attr, arg.lineno))
            # lambda ...: self.onThing(...)
            if isinstance(arg, ast.Lambda):
                for inner in ast.walk(arg):
                    if (isinstance(inner, ast.Attribute)
                            and isinstance(inner.value, ast.Name)
                            and inner.value.id == "self"):
                        handlers.append((inner.attr, inner.lineno))

    assert handlers, "found no signal connections at all -- has the parse drifted?"
    dead = [(name, line) for name, line in handlers if name not in defined]
    assert not dead, "signals wired to nothing: {}".format(
        ", ".join("self.{} (line {})".format(n, l) for n, l in sorted(dead)))


def test_the_keyboard_shortcuts_are_wired_to_methods_that_exist():
    """Same again for the key bindings, which bypass the buttons entirely."""
    widget = next(c for c in _classes() if c.name == "SegQueueWidget")
    defined, _ = _self_attributes(widget)
    install = next(n for n in ast.walk(widget)
                   if isinstance(n, ast.FunctionDef) and n.name == "_installShortcuts")

    bound = []
    for node in ast.walk(install):
        if (isinstance(node, ast.Attribute)
                and isinstance(node.value, ast.Name) and node.value.id == "self"
                and isinstance(node.ctx, ast.Load)):
            bound.append((node.attr, node.lineno))

    assert bound, "no shortcut bindings found"
    dead = [(n, l) for n, l in bound if n not in defined]
    assert not dead, "shortcuts bound to nothing: {}".format(
        ", ".join("self.{} (line {})".format(n, l) for n, l in sorted(dead)))
