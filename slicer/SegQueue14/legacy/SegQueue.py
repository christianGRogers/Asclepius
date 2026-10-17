"""SegQueue has been replaced by SegQueue14.

Shipped as ``SegQueue.py`` in every SegQueue release from 0.14.0 on (project lead,
2026-10-17). The update button of SegQueue 0.13 and older installs a release by
copying it over the extension's files, and never deletes a file, so the old
4-class module would otherwise keep loading beside SegQueue14. Overwriting it with
this stub retires it: the module stays registered under its old name, so anyone
who opens SegQueue from a menu or a favourite is taken to SegQueue14.

Nothing here talks to a server, and nothing here installs anything.
"""

import qt
import slicer
from slicer.ScriptedLoadableModule import ScriptedLoadableModule, ScriptedLoadableModuleWidget

__version__ = "retired"


class SegQueue(ScriptedLoadableModule):
    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = "SegQueue (replaced by SegQueue14)"
        self.parent.categories = ["Segmentation"]
        self.parent.dependencies = []
        self.parent.contributors = ["Christian Rogers"]
        self.parent.helpText = __doc__
        self.parent.acknowledgementText = ""


class SegQueueWidget(ScriptedLoadableModuleWidget):
    def setup(self):
        ScriptedLoadableModuleWidget.setup(self)
        label = qt.QLabel(
            "<b>SegQueue has been replaced by SegQueue14.</b><br><br>"
            "Annotation now happens in the SegQueue14 module "
            "(Segmentation -> SegQueue14), on the same server.")
        label.setWordWrap(True)
        self.layout.addWidget(label)
        button = qt.QPushButton("Open SegQueue14")
        button.clicked.connect(self._open)
        self.layout.addWidget(button)
        self.layout.addStretch(1)

    def enter(self):
        # Deferred: switching modules from inside enter() confuses Slicer's
        # module panel.
        qt.QTimer.singleShot(0, self._open)

    def _open(self):
        try:
            slicer.util.selectModule("SegQueue14")
        except Exception:
            pass
