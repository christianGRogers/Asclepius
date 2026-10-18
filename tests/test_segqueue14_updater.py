"""SegQueue14's updater, held to the live updater's tests.

``SegQueue14Lib/updater.py`` is a copy of ``SegQueueLib/updater.py`` that differs
only in which module an archive must carry. ``test_segqueue14_release_line.py``
covers that difference end to end; everything else the copy does -- the GitHub
check, the download and its refusals, the install-location checks and the check
cache -- was tested only against the original. This file re-runs those tests
with the SegQueue14 updater swapped in, so the copy cannot drift unnoticed.

The archive and install tests are not reused: they build 4-class packages, which
this updater is meant to refuse.
"""

import sys
from pathlib import Path

import pytest

_EXTENSION14 = Path(__file__).resolve().parents[1] / "slicer" / "SegQueue14"
if str(_EXTENSION14) not in sys.path:
    sys.path.insert(0, str(_EXTENSION14))

import test_segqueue_updater as live  # noqa: E402
from SegQueue14Lib import updater as updater14  # noqa: E402

# Collected here as well as in their own file; the fixture below makes this copy
# of each run against SegQueue14's updater.
from test_segqueue_updater import (  # noqa: E402, F401
    test_cache_is_fresh_inside_the_window_and_stale_outside,
    test_cache_round_trips,
    test_cache_treats_junk_as_no_cache,
    test_can_install_accepts_a_real_install,
    test_can_install_refuses_a_checkout,
    test_can_install_refuses_a_directory_that_is_not_an_extension,
    test_check_explains_a_rate_limit_rather_than_failing_vaguely,
    test_check_ignores_an_archive_for_another_slicer,
    test_check_is_silent_when_current,
    test_check_offers_a_newer_release,
    test_check_raises_update_error_not_something_random,
    test_download_refuses_a_short_read_and_leaves_nothing_behind,
    test_download_refuses_an_implausible_size,
    test_download_writes_the_file_and_reports_progress,
    test_is_checkout_walks_up_to_the_git_directory,
    test_module_roots_finds_the_extension_root,
    test_module_roots_reports_no_root_for_some_other_directory,
)


@pytest.fixture(autouse=True)
def _segqueue14_updater(monkeypatch):
    # The reused tests look both names up in their own module's globals.
    monkeypatch.setattr(live, "updater", updater14)
    monkeypatch.setattr(live, "UpdateError", updater14.UpdateError)


def test_the_swap_is_real():
    assert live.updater is updater14
    assert updater14.UpdateError is not sys.modules["SegQueueLib.updater"].UpdateError
