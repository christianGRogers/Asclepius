"""Install SegmentEditorExtraEffects into a fresh Slicer, for the self-test job.

    Slicer --no-splash --no-main-window --python-script tests/slicer_install_extension.py

The module is built around *Draw tube*, which this extension provides and Slicer
core does not. The Extensions Manager loads what it installed at the *next*
start, so this runs as its own Slicer invocation before the self-tests.

This is a script file, not ``--python-code``, because Slicer's launcher rejects a
``--python-code`` value that contains a newline ("Problem parsing command line
arguments").
"""

import traceback

NAME = "SegmentEditorExtraEffects"


def main():
    import slicer

    model = slicer.app.extensionsManagerModel()
    # Never stop to ask a question: there is nobody to answer it.
    model.interactive = False
    if model.isExtensionInstalled(NAME):
        print("already installed:", NAME)
        return 0
    # Blocking metadata refresh, so the lookup by name sees the server's list.
    model.updateExtensionsMetadataFromServer(True, True)
    # (name, installDependencies, waitForCompletion)
    ok = model.downloadAndInstallExtensionByName(NAME, True, True)
    if ok and model.isExtensionInstalled(NAME):
        print("installed:", NAME)
        return 0
    print("could not install:", NAME)
    return 1


if __name__ == "__main__":
    code = 1
    try:
        code = main()
    except Exception:
        print(traceback.format_exc())
    # Slicer swallows a bare sys.exit from a --python-script.
    import slicer

    slicer.util.exit(code)
