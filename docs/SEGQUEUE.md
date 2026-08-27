# SegQueue: labelling at scale

Moved out of the README, which now covers the training method only.

The bottleneck for Phase 1 is not the model, it is **per-segment coronary labels
that do not exist publicly**. SegQueue is the platform for producing them with a
class of undergraduate annotators: a self-hosted server that owns the case pool,
and a Slicer extension that hands one annotator one case at a time.

```
Slicer + SegQueue extension  ──TLS──▶  Caddy ──▶  Girder 5 + SegQueue plugin
   one case at a time                                │        │
   nothing left on disk                            Mongo   /data assetstore
                                                            │
                                                    worker: QA scoring + lease sweep
```

An annotator's whole workflow is: log in, press **Get next case**, segment, press
**Validate & submit**. They never choose a case, never name a file, never see a
server path, and never accumulate data — the local copy is deleted the moment the
server confirms the submission.

The structure list is fixed by the server and obeyed by the extension, so an
annotator cannot invent or rename a segment. **Which structures** is the class
schema — still open in [`docs/TRAINING-PLAN.md`](docs/TRAINING-PLAN.md).

### The data, and what the presegmentation buys

The default source is the TotalSegmentator release on Zenodo
([record 10047292](https://zenodo.org/records/10047292)) — about 1,200 whole-body
CT studies, each already segmented into 117 structures. Ingest reads those
filenames and never opens an image, which gives two things for free:

* **Only cases with a heart are loaded.** Most of a whole-body dataset is legs,
  heads and abdomens with no coronary anatomy in the field of view. Assigning
  those spends the one resource the project is short of. The eligible cases also
  ship their heart mask to the client, which uses it to centre the views.
* **A case that already carries a `coronary_arteries` mask hands it over.** That
  mask is a binary lumen, not per-branch labels — a head start, not an answer.
  The annotator splits an existing tree into four branches instead of drawing
  one, which is minutes instead of an hour. (The base Zenodo release does not
  include it; if your copy has it, from the licensed task or your own model,
  ingest picks it up with no extra flags.)

Helper masks are structurally incapable of being submitted: the export copies
only the project's own segments, and refuses outright if any other label value
appears in the exported volume.

**Oblique volumes are corrected at ingest.** The README's conversion-trap notes explain that notes that 11% of
TotalSegmentator is obliquely acquired and ITK rejects it. Training reads those
with nibabel; an annotator cannot, because Slicer *is* ITK. Ingest
orthonormalises the direction cosines — voxels, spacing and origin untouched,
axes moved by 0.007° — so the case opens, and the same corrected file is what
the training conversion later reads.

### What the extension does for the annotator

The Segment Editor can already do all of this. It is worth wrapping because it
cannot do it *for this task* — a first-year undergraduate should not have to
work out which of twenty effects segments a 3 mm vessel.

* **Four labelled buttons, keys 1–4**, to change branch — with a tick against
  each one that has voxels in it. Built from the server's segment list, so a
  fifth branch is a settings change.
* **Two tools, not twenty.** A coronary artery is a tube, so the main tool is
  *Draw tube* (**Q**): click a few points down the centreline, set the radius,
  **Apply** (**A**). Sections *accumulate* into the vessel, so an artery is drawn
  as several — wide proximally, narrower as it tapers — each with its own radius,
  and Apply leaves you armed for the next one. The radius slider is live: the
  preview follows it while you are still placing points. *Paint* (**W**) fixes
  what the tube missed, with a brush sized in millimetres so it survives zooming.
  Every other effect is still in the Segment Editor below; none earns a button.
* **Masking that makes fast painting safe.** Edits are confined to the existing
  coronary mask when the case has one, and to the opacified range (150–1000 HU)
  otherwise, so a sloppy stroke still leaves a clean lumen edge. Branches never
  overwrite each other.
* **The view set up on arrival**: CTA window/level, four-up layout, slices
  centred on the heart mask, and a surface view a click away.

### Why Girder rather than XNAT or something bespoke

Accounts, tokens, groups, a REST framework, chunked **resumable** uploads,
pluggable storage and an admin UI are all things this project needs and none of
them are things worth writing. Girder supplies them; the plugin under `server/`
adds only what is actually specific to running a workforce — an atomic case
claim, a lease that expires, a review queue, and the sampling that decides whose
work gets looked at. XNAT would have brought a heavier imaging-specific data
model that mostly gets in the way here; a bespoke server would have meant writing
resumable uploads, which is the one part you cannot afford to get subtly wrong.

### What the pieces are

| Path | What it is |
|---|---|
| `src/segqueue/` | State machine, sampling policy, wire protocol, checksums, submission checks. Stdlib-only and Python 3.9-clean, because **both** sides import it |
| `server/girder_segqueue/` | The Girder 5 plugin: models, REST, ingest CLI, QA worker |
| `slicer/SegQueue/` | The annotator's extension. `SegQueueLib/` is Slicer-free, so the network layer and the cache are unit-tested without Slicer |
| `slicer/build-extension.py` | Packages it for the Extension Manager. Plain Python, no CMake |
| `deploy/` | Compose stack, Caddyfile, backup script. See [deploy/README.md](deploy/README.md) |
| `docs/` | [Server runbook](docs/SERVER-SETUP.md) and the [setup &amp; testing guide](docs/SegQueue-Setup-Guide.pdf) |

The shared package is the load-bearing idea. A route name, a state name or a
validation rule cannot drift between client and server, because there is one
definition and both import it — and the submission checks that refuse an empty
segment client-side are the *same function* that refuses it again server-side.

### Quality, without reading every case

Reviewing 5,000 segmentations by hand is not a plan. Four mechanisms instead:

* **A training gate.** Every annotator's first five cases are reviewed by a
  human. Nobody accumulates a hundred cases of a misunderstanding.
* **Gold seeds** (~5%). Cases with an expert reference, indistinguishable from
  ordinary work. Scored automatically with the same Dice and HD95 the training
  pipeline reports — one implementation, so the numbers in the QA dashboard and
  the numbers in the paper cannot disagree.
* **Blind duplicates** (~5%). The same case to two annotators, scored
  symmetrically against each other, which is what inter-rater reliability
  actually means when there is no ground truth.
* **Sampled review** thereafter: 20% falling to 10% for consistently clean work,
  and back up after any rejection. A bad automatic score pulls a case back for a
  human even when the sampling roll had let it through.

Rejections go back to the **same** annotator with the reviewer's comment, which
is the only version of this loop that teaches anyone anything.

### Running it

```sh
cd deploy && cp .env.example .env   # edit DATA_ROOT, SEGQUEUE_DOMAIN
docker compose up -d --build
docker compose exec girder segqueue-ingest --root /incoming --dry-run
docker compose exec girder segqueue-ingest --root /incoming --target coronary
python ../tests/segqueue_e2e.py --url https://<domain>
```

Then build the extension package and hand it to annotators:

```sh
python slicer/build-extension.py     # -> dist/SegQueue-<version>-Slicer-5.8.zip
```

In Slicer: **Extensions Manager → Install from file →** pick that zip → restart.
No pip installs, no build tools and no admin rights — the module uses `requests`,
which Slicer already bundles, and the shared `segqueue` package is vendored into
the archive.

One dependency: **SegmentEditorExtraEffects**, which provides *Draw tube*.
Install it from the Extensions Manager on each annotator machine. The package
declares it, but a local *Install from file* does not resolve dependencies, so
the panel also checks at startup and says so if it is missing.

Two other routes work for development: add `slicer/SegQueue` to **Additional
module paths** (Edit → Application Settings → Modules), or paste
`exec(open(r"…/slicer/install-segqueue.py").read())` into the Python Console.
Both run the module straight out of the checkout, so a `git pull` updates it.

**Rebuild the package after any change to `src/segqueue`** — the copy inside the
archive is what annotators run, and a stale one speaks an old wire protocol to a
new server. (Not `girder-client`: version 5 requires Python
3.10 and Slicer 5.8 ships 3.9. That constraint is also why `src/segqueue` is
stdlib-only.)

Full deployment, ingest, backup and upgrade notes:
**[docs/SERVER-SETUP.md](docs/SERVER-SETUP.md)**. The annotator-facing setup and
a manual test walkthrough are in
**[docs/SegQueue-Setup-Guide.pdf](docs/SegQueue-Setup-Guide.pdf)**.

### Status

Verified end to end against the real Compose stack, by `tests/segqueue_e2e.py`:
register → assetstore → create annotator → ingest (heart filter, coronary seed) →
assign → download with checksum verification → fetch the heart and coronary masks
→ resumable chunked upload → submit → review → reject with comment → rework as
attempt 2 with the lease renewed → resubmit → approve. Empty segments, stray
marks, off-protocol segments, resampled geometry and mismatched checksums are all
refused with the message the annotator needs, and the 30-annotator concurrent
claim race is tested against real MongoDB.

The Slicer panel is verified against a real Slicer 5.8.1: the packaged extension
installs through the Extension Manager, the module loads from the installed
location, all six offered effects activate, editing is confined to the coronary
seed and to the opacified HU range, branches do not overwrite each other, and an
export with the seed present in the scene excludes it and lands on the source
grid. Two bugs came out of that pass — mask mode silently resetting when set
before the mask segment id, and an empty scene reporting a file-write failure
instead of naming the vessels still to draw.

The join has since been exercised too: against a running stack, the module logs
in, claims an oblique case, downloads it with its heart and coronary masks, loads
all three into the scene, and releases with a purge.

Not yet exercised: a human segmenting a case through to Submit, gold and
duplicate scoring on real label volumes, and anything at 5,000-case scale.

Not yet built: an export from approved submissions into the
case layout (README, “Data”) `segtrain convert` reads. Approved work sits
in the assetstore as label volumes on the source grid — the right *contents*, one
directory rename away from the right *shape* — but the step is manual today.
---
