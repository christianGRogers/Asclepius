"""Support code for the JanusMRead Slicer module, free of Slicer, Qt and VTK, so it
is tested by ordinary pytest.

Named ``JanusMReadLib`` so it can never shadow ``SegQueue14Lib`` (or be shadowed by
it): Slicer puts every scripted module's directory on one ``sys.path``.

* :mod:`.halfmax` -- the half-maximum helper (protocol section 3);
* :mod:`.precheck` -- the checks before upload (values 0-4, all four classes);
* :mod:`.release`, :mod:`.updater` -- self-update on the ``janusm-read-v*`` line.

The network client is ``janusm_reads.client`` itself, vendored beside the module.
"""
