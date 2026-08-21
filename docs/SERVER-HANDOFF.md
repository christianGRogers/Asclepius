# SegQueue server — handoff

**Audience:** an agent picking up the server side of SegQueue. You are not
starting from scratch; the platform is built, tested and deployable. What is left
is one missing feature, one real bug, and the work of running it on real data.

**Repo:** `christianGRogers/Asclepius`, branch `main`, at `0d85def` or later.
**Read first:** [`SERVER-SETUP.md`](SERVER-SETUP.md) — the operator runbook. This
document assumes it and does not repeat it.

---

## 1. What exists, and how well it is known to work

| Area | State |
|---|---|
| Girder 5 plugin: case pool, atomic claim, leases, review, QA sampling | Built. 402 unit tests, 19 more against real MongoDB including a 30-annotator claim race |
| Ingest from TotalSegmentator, heart filter, coronary seed, oblique-geometry correction | Built, verified against a running stack |
| REST surface (22 routes) | Built, exercised by `tests/segqueue_e2e.py` |
| Slicer extension, packaged for the Extension Manager | Built, verified in a real Slicer 5.8.1 end to end against a live server |
| Background worker: QA scoring + hourly lease sweep | Built. **Scoring has never run on real label volumes** |
| Deployment: Compose, Caddy, backup script | Built, image builds and boots. **Never deployed to a real host** |

Two commands establish the baseline before you change anything:

```sh
pytest                                                   # expect 402 passed
python tests/segqueue_e2e.py --url http://localhost:8099 # expect 34 passed, 0 failed
```

> `tests/test_slurm.py::test_write_script_is_executable` fails on Windows. It is
> pre-existing, unrelated to SegQueue, and checks a POSIX permission bit. Ignore
> it; do not "fix" it by weakening the assertion.

---

## 2. Ground rules

- **`src/segqueue/` is stdlib-only and Python 3.9-clean.** Both the Girder plugin
  (3.11) and the Slicer extension (3.9) import it. No numpy, no requests, no
  `match`. Anything needing numpy goes in `src/segtrain/` or the plugin.
- **Changing a response field is free; removing or repurposing one is not.**
  Readers ignore unknown keys. A breaking change means bumping
  `PROTOCOL_VERSION` *and* `MIN_CLIENT_PROTOCOL` in `src/segqueue/protocol.py`.
- **Rebuild the extension after touching `src/segqueue/`:**
  `python slicer/build-extension.py`. The package vendors a copy; a stale one
  speaks an old protocol.
- `ruff check src/ server/ slicer/ tests/` must pass. Line length 100.
- Every behavioural change needs a test. The suites are fast (~7 s) and most of
  the platform is pure functions precisely so they can be.

---

## 3. Tasks

Ordered by what blocks the project. T1 and T2 are operational.

> **T3 and T4 were completed in `2951b7c`, `3b40ce5` and `cc9836f`** —
> `segqueue-export` exists, and the drop box is swept. They are kept below,
> struck through, because the acceptance criteria have not been run against real
> approved work yet: nobody has exported a tree and fed it to `segtrain convert`.
> That check is now part of T5.

### T1 — Deploy to the real host *(blocks everything)*

Nothing has run outside a laptop. Follow `SERVER-SETUP.md` §3–§4 on the actual
machine.

Decisions you must make, not defer:

- **TLS.** A real DNS name, or a VPN with a real hostname inside it. The
  self-signed path means installing Caddy's CA root on thirty student laptops —
  the Slicer extension will otherwise refuse to connect. `SERVER-SETUP.md` §7.
- **`DATA_ROOT` on mirrored storage.** ~300 MB/case. A single-disk failure
  mid-project is a term of undergraduate labour.

**Acceptance:** `python tests/segqueue_e2e.py --url https://<domain>` reports
34 passed, 0 failed, from a machine that is not the server.

### T2 — Re-ingest the pool

Cases ingested before `0d85def` have uncorrected direction cosines, and **~11% of
TotalSegmentator cannot be opened in Slicer at all** without the fix (§6.3). Ingest
is idempotent by case name, so re-running *skips* them — it will not repair them.

Either start from a clean database (simplest if the pool is small), or retire and
re-ingest the affected cases:

```sh
docker compose exec girder segqueue-ingest --root /incoming --dry-run
docker compose exec girder segqueue-ingest --root /incoming --target coronary
```

**Acceptance:** the ingest summary's "had oblique direction cosines corrected"
count is non-zero and plausible (~1 in 9), and every case in the pool opens in
Slicer. A quick check: claim several cases and load each.

Consider a `--refresh-geometry` mode that repairs already-stored cases in place
rather than requiring a re-import. Not built; be careful with assignments in
flight.

### ~~T3 — Export approved work into the training layout~~ *(done — verify)*

This is the one thing that stops the platform being end-to-end useful. Approved
submissions sit in the assetstore as label volumes on the source grid — the right
*contents* — but nothing turns them into what `segtrain convert` reads.

Build `segqueue-export`, a third console script beside `segqueue-ingest` and
`segqueue-score` (`server/pyproject.toml` `[project.scripts]`).

**Write this layout** (see the README section *Your coronary data*):

```
<out>/<case>/ct.nii.gz
<out>/<case>/segmentations/left_main.nii.gz          one binary mask per vessel
<out>/<case>/segmentations/left_anterior_descending.nii.gz
<out>/<case>/segmentations/left_circumflex.nii.gz
<out>/<case>/segmentations/right_coronary_artery.nii.gz
```

Prefer the per-vessel form over a single `labels.nii.gz`: it distinguishes "not
labelled in this case" from "not present", which a merged integer volume has
already thrown away. `segtrain convert` reports absent structures per case.

Notes that will save you time:

- Submissions are **integer label volumes**, not `.seg.nrrd` segmentations,
  despite the filename. Label values come from `segqueue.project` settings and
  match `configs/labels/coronary.yaml`. Split by value.
- Take the **approved** assignment per case (`states.APPROVED`), not the latest
  submission — a case may have a rejected attempt 1 and an approved attempt 2.
  `Assignment().approvedForCase(caseId)` exists.
- The CT to write is the case's stored volume, which is the *corrected* one. Do
  not go back to the original dataset file; the labels were drawn on the stored
  grid.
- For a duplicated case there are two approved annotations. Decide and document:
  export both under distinct case ids, or pick one. Do not silently drop one.
- Flags worth having: `--out`, `--limit`, `--dry-run`, `--since`, and
  `--include-unreviewed` (default off).

**Acceptance:** `segtrain index --root <out>` then `segtrain convert` runs
without geometry-mismatch or missing-structure errors on the exported tree.

### ~~T4 — Empty the incoming drop box~~ *(done — verify)*

`utils.incomingFolder`'s docstring says *"The sweeper empties it; nothing
downstream ever reads from it."* **Nothing empties it.** `maintenance.sweep` only
reclaims lapsed assignments — grep confirms no other reference.

Every abandoned or failed upload therefore stays forever in a folder thirty
annotators have write access to. At ~20 MB a submission that is slow, unbounded
disk growth in the one place students can write.

Add it to `maintenance.sweep`: delete items in the incoming folder older than
some age (a day is generous — a successful submit moves the item out immediately,
in `rest/queue.py`'s `submit`). Guard against deleting an upload in flight.

**Acceptance:** a test that plants an old item and a fresh one in the incoming
folder, sweeps, and asserts only the old one is gone. Fix the docstring either
way — right now it documents behaviour that does not exist.

### T5 — Prove the QA scoring path, and the exporter, on real data

`girder_segqueue/scoring.py` computes Dice and HD95 for gold and duplicate
submissions via `segtrain.metrics`. The metric code is unit-tested; **the path
from a real submitted label volume to a number has never run.**

1. Ingest a handful of cases with `--gold-root` pointing at real expert
   references.
2. Have someone segment one (it will be served as gold — `gold_first_case` is on
   by default).
3. `docker compose logs worker`, and check the submission's `autoScore`.

Watch for: `_readLabels` reverses SimpleITK spacing to match the `(z, y, x)`
array order. If HD95 looks wrong along one axis only, that is where to look.

**Acceptance:** a gold submission gets a `mean_dice`, and one deliberately poor
segmentation is flagged `needsReview` by falling under `gold_dice_flag` (0.70).

Then close out T3 with the same real work: `segqueue-export --out <tree>`,
`segtrain index --root <tree>`, `segtrain convert`. The exporter is written and
unit-tested; what has not happened is a round trip from a human's segmentation to
a training set.

### T6 — Test the restore, not just the backup

`deploy/backup.sh` is cron-ready and never been restored from. Do it once, on
purpose, into a scratch stack: `mongorestore --archive --gzip`, then a restic
restore of the assetstore, in that order. An untested backup is a hypothesis.

### T7 — Small, optional

- Surface `geometryFixed` in `GET /segqueue/stats` — provenance a dataset
  reviewer will ask about, currently only visible at ingest time.
- The sweeper reclaims assignments but never emails anyone. If annotators go
  quiet, someone has to notice by looking.
- No admin web UI, deliberately. Resist building one; `stats` and
  `stats/annotators` answer the real questions.

---

## 4. Running things

```sh
# Unit tests, no server needed
pytest

# Concurrency tests need real MongoDB -- the point is that the atomic claim
# survives thirty annotators starting at once, which no fake demonstrates
docker run -d --rm -p 27099:27017 mongo:7
SEGQUEUE_TEST_MONGO=mongodb://localhost:27099 pytest tests/test_segqueue_server.py

# A throwaway stack (Windows/macOS: do NOT use compose, see §6.2)
docker network create segq-test
docker run -d --name segq-mongo --network segq-test mongo:7
docker build -f deploy/Dockerfile -t segqueue:test .
docker run -d --name segq-girder --network segq-test -p 8099:8080 \
  -e GIRDER_MONGO_URI=mongodb://segq-mongo:27017/girder \
  -e GIRDER_SERVER_MODE=production segqueue:test

# Acceptance test against whatever is running
python tests/segqueue_e2e.py --url http://localhost:8099

# Read or write plugin settings
docker compose exec girder sh -c 'cat > /tmp/s.py <<EOF
from girder.models.setting import Setting
import json; print(json.dumps(Setting().get("segqueue.policy"), indent=2))
EOF
girder shell /tmp/s.py'
```

Slicer can be driven headlessly, which is how the client was verified without a
human:

```sh
"…/Slicer.exe" --no-splash --no-main-window --ignore-slicerrc --python-script probe.py
```

Write results to a file from inside the script; stdout is not reliably attached
on Windows.

---

## 5. Repo map

| Path | What |
|---|---|
| `src/segqueue/` | Shared with the client: state machine, sampling policy, wire protocol, checksums, submission checks, dataset scanning. **stdlib-only, py3.9** |
| `src/segtrain/geometry.py` | Orthonormalising oblique volumes. Lives here, not in the plugin, because it is a property of the dataset |
| `server/girder_segqueue/models/` | `case.py` holds the atomic claim — read it before touching assignment |
| `server/girder_segqueue/rest/` | `queue.py` (annotator), `review.py`, `admin.py` |
| `server/girder_segqueue/ingest.py` | `segqueue-ingest` |
| `server/girder_segqueue/scoring.py` | `segqueue-score` — QA scoring *and* the hourly sweep |
| `server/girder_segqueue/maintenance.py` | `sweep()`, shared by the worker and the admin endpoint so they cannot drift |
| `slicer/` | The extension, plus `build-extension.py` |
| `tests/segqueue_e2e.py` | Acceptance test against a live server. Not collected by pytest |

---

## 6. Landmines

Each of these cost real time. None is obvious from the code.

### 6.1 Deployment

- **The assetstore must exist before anything can be uploaded.** Girder ships
  with no storage configured. Ingest refuses to start without one, but the web UI
  will let you get much further before failing confusingly.
- **On a brand-new database the plugin loads before any user exists**, so it
  cannot create its groups (Girder needs a creator). Handled — they appear on the
  next restart or first annotator creation. Do not "fix" it by raising.
- **`girder-segqueue` deliberately does not declare `segqueue` as a dependency.**
  The distribution providing it is named `segtrain`, and an unrelated project owns
  that name on PyPI. The Dockerfile installs the repo root first. If you see
  *"girder-segqueue needs the segqueue package"*, that ordering was skipped.

### 6.2 Windows

- **Git Bash rewrites container paths.** `docker exec … --root /tmp/x` becomes
  `C:/Users/…/tmp/x`. Prefix with `MSYS_NO_PATHCONV=1`, or use PowerShell.
- **MongoDB's storage engine is unreliable on a Windows bind mount.** Use a
  Docker-managed volume for local testing; Compose is fine on the Linux host.

### 6.3 Medical imaging

- **ITK rejects non-orthonormal direction cosines.** ~11% of TotalSegmentator is
  obliquely acquired and, as float32, falls outside tolerance. Training reads
  those with nibabel and never notices; **Slicer is ITK and cannot open them at
  all**. Corrected at ingest by polar decomposition — see `src/segtrain/geometry.py`.
  The error surfaces only through SimpleITK; Slicer just says "load failed".
- **Slicer picks its reader from the file extension, not the contents.** A
  gzipped NIfTI saved as `.nrrd` downloads, verifies its checksum, and then
  refuses to open. Assignments carry `volumeName` for this reason.
- **`os.path.splitext(".nii.gz")` gives `.gz`.** Use `segqueue.dataset.suffix_for`.

### 6.4 Girder and Mongo

- **Girder wraps `RestException` payloads under an `extra` key.** `protocol.parse_error`
  accepts both shapes; do not "simplify" it.
- **`File` has no `move`.** Files hang off Items — move the `Item`.
- **pymongo 4 removed `cursor.count()`.** Use `count_documents`.
- Every concurrency-sensitive operation is a single `find_one_and_update`. If you
  add one, keep it that way and add it to the race test.

### 6.5 Slicer, if you touch the client

- **`SetMaskSegmentID` before `SetMaskMode`.** The other order silently resets the
  mode to "everywhere" — the mask looks applied and confines nothing.
- **An empty segmentation exports to a zero-extent labelmap** that cannot be
  written by any method. Handled; the annotator gets "left_main is empty" rather
  than a file-write error.
- **`installExtension` will not overwrite an installed extension**, and
  `scheduleExtensionForUninstall` only takes effect on the next start. Reinstalling
  from a script needs two Slicer runs.

---

## 7. Definition of done

- T1–T5 complete, T6 done once.
- `pytest` green, `ruff` clean, `segqueue_e2e.py` green against the real host.
- A tree exported by T3 that `segtrain convert` accepts.
- `SERVER-SETUP.md` §12 (Known gaps) updated to say what is now true.
