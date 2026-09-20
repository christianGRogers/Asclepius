<!--
Branch naming: <type>/<slug> — feat, fix, docs, ci, chore, exp. See CONTRIBUTING.md §4.
Topic branches target `dev`. Only `dev` targets `main`.
-->

## What changes, and for whom

<!-- One or two sentences from the point of view of the annotator or the
operator, not the diff. "Annotators can now trim a branch without losing the
second vessel", not "refactor TrimWidget". -->

## Why

<!-- The reasoning a future reader would otherwise reconstruct from the diff. -->

## What I ran

- [ ] `pytest` passes
- [ ] `ruff check .` is clean
- [ ] Tested by hand: <!-- what, where, against which server -->

## If this touches the labelling app

<!-- Delete this section if it does not touch slicer/, server/ or src/segqueue/. -->

- [ ] **Old clients:** an annotator running the *previous* extension version
      still works against this server — or this PR explains why not and what
      they see.
- [ ] **`src/segqueue/` is still stdlib-only and 3.9-clean** (no new imports
      outside the standard library, no 3.10+ syntax).
- [ ] **Version:** `__version__` in `slicer/SegQueue/SegQueue.py` is bumped if
      this should reach annotators, and left alone if it should not.
      Merging this to `main` with a bump publishes a release and prompts
      everyone to update.
- [ ] Panel wiring changes are covered by `tests/test_segqueue_module.py`, and
      anything only a real Slicer can check by `tests/slicer_selftest.py`.

## Anything a reviewer should look at first

<!-- Optional: the risky hunk, the decision you are least sure about. -->
