# Contributing to Asclepius

This repository holds two things that ship on very different schedules, and most
of the rules below exist because of that difference.

| Component | Lives in | Who it reaches |
|---|---|---|
| **The labelling app** — Girder plugin, Slicer extension, shared protocol | `server/`, `slicer/`, `src/segqueue/` | A class of annotators, on their own laptops, today |
| **The training pipeline** — nnU-Net v2 data prep, planning, SciNet jobs | `src/segtrain/`, `configs/`, `scripts/` | One operator, on one cluster |

A mistake in the training pipeline costs an afternoon of compute. A mistake in
the labelling app is thirty people who cannot work — and because the extension
updates itself from this repository's releases, it can reach them within minutes
of a merge to `main`. The testing and release rules are weighted accordingly.

The reasoning behind the model itself is not in `docs/`; it lives in the Obsidian
vault at [`vault/`](vault/README.md).

---

## 1. Ground rules

These are the ones that are not a matter of taste. Everything below them is.

**`src/segqueue/` is stdlib-only and Python 3.9-clean.** It is the wire protocol
and the state machine, and it is imported by *both* the Girder plugin (Python
3.11) and the Slicer extension (Slicer 5.8 bundles Python 3.9). No numpy, no
requests, no `match`, no `X | None`. `tests/test_segqueue_portability.py`
enforces this, so the build fails before a reviewer has to notice.

**Changing `src/segqueue/protocol.py` is changing a deployed API.** Annotators
run whatever extension version they last installed. A server that starts
requiring a field the old client never sends locks those annotators out
mid-case. Add fields as optional, tolerate unknown ones, and state in the pull
request what an old client does against the new server.

**Never push to `main`.** A push to `main` that bumps `__version__` publishes a
release, and the module then offers every annotator "Update and restart" the
next time they open it. That is a deployment, not a merge. See §6.

**No data, weights, or credentials in git.** `.gitignore` covers the nnU-Net
roots, `*.nii.gz`, `*.pth` and `deploy/.env`. If something large slipped
through, say so in the pull request rather than rewriting history on a shared
branch.

---

## 2. Getting set up

```sh
python -m venv .venv && . .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -e ".[dev]" requests                 # pipeline, shared package, pytest, ruff
pip install -e ./server                          # only if you are touching the Girder plugin
```

Training itself needs the `[train]` extra (nnU-Net, SimpleITK) and a GPU. You
need neither to work on data prep, the protocol, or the extension — that
separation is deliberate and worth keeping.

---

## 3. Testing

Run this before opening a pull request:

```sh
pytest                  # ~480 tests: no network, no database, no dataset
ruff check .
```

Tests that need something the machine may not have are marked, and skip cleanly
rather than failing. That is the bargain: the suite always runs, and the marked
tests run wherever they can.

| Marker / harness | Needs | How to run it |
|---|---|---|
| *(unmarked)* | nothing | `pytest` |
| `needs_mongo` | a MongoDB | `docker run -d -p 27099:27017 mongo:7`, then `SEGQUEUE_TEST_MONGO=mongodb://localhost:27099 pytest -m needs_mongo` |
| `needs_data` | the TotalSegmentator dataset | point `configs/dataset.local.yaml` at it |
| `needs_network` | a reachable public API | `pytest -m needs_network` |
| `tests/segqueue_e2e.py` | a running server with cases in the pool | `python tests/segqueue_e2e.py --url http://localhost:8099` |
| `tests/slicer_selftest.py` | a real Slicer install | `Slicer --no-splash --python-script tests/slicer_selftest.py` |

The last two are deliberately not collected by pytest — they need a live system,
and a filename pytest ignores is more reliable than a marker somebody forgets.
CI runs both (§5), so a pull request does not have to.

> **Known failure on Windows:** `test_slurm.py::test_write_script_is_executable`
> checks a POSIX permission bit and fails on Windows. It is expected. Do not
> "fix" it by weakening the assertion — CI runs on Linux, where it is a real
> check.

### What a change to the labelling app brings with it

`SegQueue.py` imports Qt, VTK and Slicer, so pytest cannot import it, and the
module's worst bugs fail *silently*: a Segment Editor effect parameter
misspelled by one capital letter leaves a button that activates and does
nothing. Two suites exist for that class of bug, and a change to the panel is
expected to keep both meaningful.

- `tests/test_segqueue_module.py` parses `SegQueue.py` and checks that every
  `self.x` it reads is something the class defines, that every signal is wired
  to a method that exists, and the same for the keyboard shortcuts. If you add
  a new kind of wiring, extend this file to cover it.
- `tests/slicer_selftest.py` runs *inside* Slicer and checks what only a real
  Slicer can answer: effect parameters that are strings converted to enums by
  name, and segment arithmetic that produces wrong voxels rather than an error.

New behaviour in the protocol, the state machine, or the scoring policy belongs
in the ordinary pytest suite, where it is cheap to run and cheap to trust.

---

## 4. Branches

Two permanent branches:

- **`main`** — released. Protected. Every commit on it is, or could be, on an
  annotator's laptop. Reached only by pull request from `dev`.
- **`dev`** — integration. Topic branches merge here first, and `dev` is what
  gets proposed to `main` once it is coherent.

Topic branches are named `<type>/<short-slug>`, lowercase and hyphenated:

| Prefix | For |
|---|---|
| `feat/` | new behaviour — `feat/branch-trim-tool` |
| `fix/` | a defect — `fix/dead-panel-0-7-0` |
| `docs/` | documentation and the vault — `docs/annotator-guide` |
| `ci/` | workflows, packaging, tooling — `ci/mongo-integration-job` |
| `chore/` | dependencies, renames, cleanup — `chore/normalise-line-endings` |
| `exp/` | an experiment that may never merge — `exp/heart-crop-paired-run` |

`.github/workflows/ci.yml` checks this on every pull request. The rule is not
about tidiness: the prefix tells a reviewer, before they open the diff, whether
this is something that can reach an annotator.

**Archive branches are frozen and exempt:** `plan-v1` (the retired training
plan), `scinet-training`, and `segqueue-platform`. Do not build on them; they
exist so that `git show plan-v1:README.md` keeps working.

---

## 5. Commits and pull requests

Write commit subjects the way this repository already does: **imperative mood,
sentence case, no type prefix, describing the effect rather than the edit.**

```
Fix the trim tool not drawing, and test the module inside Slicer
Divide the mask by trimming, one vessel at a time
Orthonormalise oblique volumes at ingest, so Slicer can open them
```

Not `fix(slicer): scissors shape enum`, and not `updater 2`. The body is for
why, and for anything a future reader would otherwise have to reconstruct from
the diff.

A pull request should say what changes for the person on the other end — the
annotator, or the operator — and what you ran.
`.github/PULL_REQUEST_TEMPLATE.md` asks for that and little else.

CI must be green before merge. If a job fails for a reason unrelated to your
change, say so in the pull request rather than merging past it silently.

---

## 6. Releasing the labelling app

The release is automatic and its trigger is a version number, so treat that
number as the deployment switch it is.

1. Merge to `main` through a pull request as usual.
2. If the change should reach annotators, bump `__version__` in
   `slicer/SegQueue/SegQueue.py` **in that same pull request**.
3. On the push to `main`, `.github/workflows/segqueue-release.yml` runs the
   shared-package tests, builds the `.zip`, checks it has the shape the updater
   expects, and — only if the tag `segqueue-v<version>` does not already exist —
   publishes a GitHub release.
4. Annotators are offered **Update and restart** the next time they open the
   module.

A push that does not bump the version builds and tests but publishes nothing.
That is what keeps a README typo from prompting thirty people to restart Slicer.

**Before bumping the version**, check that the server and the extension can talk
to each other across the change. If the release needs a server that is not
deployed yet, deploy the server first — the extension updates itself and the
server does not.

---

## 7. Review

`.github/CODEOWNERS` routes review by path. Anything under `slicer/`, `server/`
or `src/segqueue/` reaches annotators and is reviewed as such: a reviewer is
entitled to ask "what happens to someone running the previous extension?" and to
block on the answer.
