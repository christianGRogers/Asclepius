"""Overlapping classes while editing: "Modify other segments: Allow overlap" (0.25.3).

D39 keeps every class whole on export, overlaps included, and D44's materials
(stent, calcified and non-calcified plaque) sit *inside* LM, LAD, LCx, RCA and
their branches. That only reaches a submission if the editor never takes a
voxel from one class while another is painted. The Segment Editor decides that
with one setting on its parameter node, the overwrite mode, shown in the
Masking panel as "Modify other segments":

* ``OverwriteAllSegments`` ("Overwrite all"), **Slicer's default**: painting
  plaque inside the LAD erases the LAD there.
* ``OverwriteNone`` ("Allow overlap"): both keep the voxel.

SegQueue14's own editor node has been set to Allow overlap since 0.17, and it
stays there through every path (checked in a real Slicer 5.8.1 and 5.12.4). But
Slicer's own **Segment Editor module** edits the same case through a node of its
own, made with Slicer's default, so a material painted there erased the vessel
under it. Every node made after a scene clear starts the same way.

So the module registers a scene *default node* with Allow overlap: every
``vtkMRMLSegmentEditorNode`` the scene makes from then on -- the Segment Editor
module's, the one made again after ``mrmlScene.Clear``, any other -- starts with
Allow overlap. Nodes that already exist are set when a case or a submission is
bound. Nothing observes the setting afterwards: an annotator who chooses
another one in the Masking panel keeps it until the next case opens.

Free of Slicer, Qt and VTK -- the node class and scene are passed in -- so pytest
checks it with stand-ins. Python 3.9-clean, as Slicer 5.8 bundles 3.9.
"""

#: The scene's class name for a Segment Editor parameter node.
EDITOR_NODE_CLASS = "vtkMRMLSegmentEditorNode"
#: The singleton tag of the Segment Editor *module's* parameter node.
SEGMENT_EDITOR_SINGLETON = "SegmentEditor"
#: The overwrite mode's name for "Allow overlap", as
#: ``ConvertOverwriteModeToString`` spells it (5.8.1 and 5.12.4 alike).
ALLOW_OVERLAP_NAME = "OverwriteNone"


def allow_overlap_mode(editor_class):
    """The overwrite-mode value meaning "Allow overlap", or None if unknown.

    The enum constant (``OverwriteNone``, current from Slicer 4.10 to 5.12), and
    failing that the mode looked up by name, so a Slicer that drops the wrapped
    constant still gets the right number rather than a guessed one.
    """
    mode = getattr(editor_class, "OverwriteNone", None)
    if mode is not None:
        return int(mode)
    convert = getattr(editor_class, "ConvertOverwriteModeFromString", None)
    if convert is None:
        return None
    try:
        mode = int(convert(ALLOW_OVERLAP_NAME))
    except Exception:
        return None
    return mode if mode >= 0 else None


def allows_overlap(editor_node, editor_class):
    """Whether ``editor_node`` is set to "Allow overlap"."""
    if editor_node is None:
        return False
    mode = allow_overlap_mode(editor_class)
    return mode is not None and int(editor_node.GetOverwriteMode()) == mode


def allow_overlap(editor_node, editor_class):
    """Set ``editor_node`` to "Modify other segments: Allow overlap".

    Returns whether it is set. Never raises: a node that cannot be set is worse
    for the annotator than one that is, but it must never stop a case opening.
    """
    if editor_node is None:
        return False
    mode = allow_overlap_mode(editor_class)
    if mode is None:
        return False
    try:
        if int(editor_node.GetOverwriteMode()) != mode:
            editor_node.SetOverwriteMode(mode)
    except Exception:
        return False
    return True


def allow_overlap_by_default(scene, editor_class):
    """Make every Segment Editor node ``scene`` creates start with Allow overlap.

    Through the scene's default node for the class: kept as it is if another
    module already registered one (only its overwrite mode is set), added
    otherwise. Slicer keeps default nodes across ``mrmlScene.Clear``. Returns the
    default node, or None if the scene has no default nodes.
    """
    if scene is None or not hasattr(scene, "AddDefaultNode"):
        return None
    try:
        default = scene.GetDefaultNodeByClass(EDITOR_NODE_CLASS)
        if default is None:
            default = editor_class()
            allow_overlap(default, editor_class)
            scene.AddDefaultNode(default)
        else:
            allow_overlap(default, editor_class)
    except Exception:
        return None
    return default


def segment_editor_module_node(scene):
    """The Segment Editor module's parameter node in ``scene``, or None."""
    if scene is None:
        return None
    try:
        return scene.GetSingletonNode(SEGMENT_EDITOR_SINGLETON, EDITOR_NODE_CLASS)
    except Exception:
        return None


def allow_overlap_everywhere(scene, editor_class, editor_nodes=()):
    """On binding a case: the default for new nodes, and Allow overlap on
    ``editor_nodes`` and on the Segment Editor module's node if it exists.

    Returns the nodes set (the default node not counted).
    """
    allow_overlap_by_default(scene, editor_class)
    done = []
    for node in list(editor_nodes) + [segment_editor_module_node(scene)]:
        if node is None or any(node is seen for seen in done):
            continue
        if allow_overlap(node, editor_class):
            done.append(node)
    return done
