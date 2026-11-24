# SegQueue14

The 3D Slicer module for coronary annotation in **four classes** (D25), shown in Slicer
as **SegQueue**. The name SegQueue14 is historical: it was built for 14 ImageCAS-X
classes (D9), which D25 reversed. From **0.14.0 it replaces the old SegQueue module**
and continues its version numbers (D24): same server, its own routes
(`/api/v1/segqueue14`), its own settings, its own cache (`~/.segqueue14`).

## What you do

1. **Segmentation → SegQueue**, log in with your usual account (you must be in the
   `segqueue14-annotators` group).
2. **Get next case.** The CT arrives with a yellow **vessel seed** (an automatic,
   uncorrected one-colour mask of the coronary tree, D23), and each of the four
   class segments starts as a **full copy of the seed, hidden** (D26):

   | 1 LM | 2 LAD\* | 3 LCx\* | 4 RCA\* |
   |---|---|---|---|

   \* expected in every case (D13). LM is optional (some patients have separate LAD
   and LCx ostia). Since the project lead's instruction of 2026-11-02 (#270)
   nothing about the segmentation is checked at submit: an empty class, classes
   sharing voxels and an empty scene all go through, and the reviewer sees them.
3. **Cut each class down** in the Segment Editor: show one class at a time (the eye
   in the segment list) and erase everything that is not that vessel.
   Every side branch takes the class of the vessel it comes off (D1): diagonals and
   septals are LAD; obtuse marginals are LCx; a PDA or posterolateral branch is the
   class of the artery it arises from. A ramus intermedius is always LCx (D1b). Add
   vessel the seed missed, delete anything that is not a coronary artery, and trim or
   extend the outline to the contrast-filled lumen.
4. **Submit case.** What is in the four segments is what is submitted, **every class
   whole** (D39, 0.17.0): where two classes share voxels, both keep them. The seed
   and the heart mask are helpers and never leave your machine.

### Extended classes (0.18.0, protocol 18, D44)

An optional **Extended classes** toggle above the Segment Editor, **off by default**
and remembered per login (`SegQueue14/extendedClasses/<login>`), adds 17 classes,
empty, grouped under their parent in the segment list, with show/hide per group:

| Group | Classes (label values) | Folded into, when scored |
|---|---|---|
| Materials | Stent (5), Calcified plaque (6), Non-calcified plaque (7) | nothing |
| LAD branches | D1-D3 (8-10), S1-S3 (11-13) | LAD |
| LCx branches | OM1, OM2 (14, 15) | LCx |
| RCA branches | Conus (17), RMA (18) | RCA |
| RCA branches | SN (16), PDA (19), PLB (20) | the vessel each component leaves, RCA or LCx (D47); RCA if neither |
| Other | Ramus (21) | LCx (D1b) |

- **Off:** nothing changes. A case is the four classes, submitted as a four-class
  stack exactly as 0.17.x submits it.
- **On:** the 17 are added empty to the open case or draft. The seed still fills
  only LM, LAD, LCx and RCA (D26); the annotator moves a branch out of its parent
  into its class, and paints the materials. Overlaps are fine (D39).
- **Submitted classes:** while any extended class is in the scene, the read is
  submitted with all 21 channels in label order (`labels.ALL_NAMES`), the empty ones
  empty. Turning the toggle off removes only the empty extended classes; a class
  with voxels is kept, so the read stays extended.
- **Label values** 5-21 are fixed (`src/segqueue14/labels.py`) and set once when a
  segment is created. An existing segment is never re-pinned (#270's root cause), so
  a 0.17.x draft opened in 0.18.0 keeps its four classes untouched, plus the 17
  empty ones if the toggle is on.
- **Reviewers:** an extended read opens with all its classes whatever the toggle
  says, and a revision keeps all 21. A 0.17.x module is refused an extended read at
  claim, download and revise with *"Update SegQueue14 to review this read"*;
  four-class reads open in either version.

### D47 (0.20.0, #322)

- **Branch parents:** when a read is scored, paired or exported `--four-class`, each
  SN, PDA and PLB component is counted with the vessel it leaves (most face contact
  with RCA or LCx); one touching neither, or both equally, goes to RCA and is
  counted. Server-side: every module version gets it.
- **Complete** tick-boxes under the extended classes, one per branch group (LAD
  branches; LCx branches, ramus included; RCA branches): "I looked for every branch
  of this group, so an empty class here means absent". Unticked by default, never
  required. Saved with the draft and written into the class-stack header
  (`SegQueue14_CompleteGroups`) of an extended read; a reviewer sees the annotator's
  ticks and a revision keeps them.
- **Extended-mode cases:** a case the server flags `extendedMode` opens with the
  extended classes on (whatever the toggle) and a one-line note asking the
  annotator to use them. Turning the toggle off is still allowed.
- The extended instructions say to move a branch out of whichever vessel it leaves,
  and to trace septals, SN, conus and RMA beyond the seed where visible.
- Older modules: 0.18.x/0.19.x ignore the flag and the ticks; a revision from them
  keeps the annotator's ticks (the server carries them forward).

### Compare reads (0.21.0, #335, reviewers)

- **Compare reads** under *Submissions* loads every annotator read of the selected
  case onto its CT, read-only, each in its own colour (A red, B blue, C yellow, ...):
  surfaces in 3D, outlines in the slices, a show box and an opacity slider per read.
  Enabled when the case has two or more annotator reads. Reopened reads (#315) and
  attempts a resubmission replaced are left out unless *Include reopened* is ticked.
- **Agreement map:** pick any two reads; per class (or all) the voxels in both
  (white), in the first only and in the second only (each read's colour), with the
  per-class Dice and voxel counts beside it. A four-class read against an extended
  one is compared after the collapse to the four (D47's PDA/PLB/SN rule); two
  extended reads class by class, with the four-class mean (the server's pair score)
  shown too. Computed by `segqueue14.compare`, as the server scores pairs.
- **Nothing is written:** no claim, verdict, draft or upload. *Open A for revision*
  opens that read through the ordinary review flow.
- Module only: the protocol stays 19 and the server is unchanged.

### My submissions (0.22.0, protocol 20)

- A folded **My submissions** line at the foot of the *Case* section. Opened, it
  lists your submitted cases that are not approved yet, newest first: the case, when
  you submitted it (US Eastern time) and one **Revise**.
- **Revise** takes the case back and opens it straight away from what you submitted,
  every class whole, as a reopened case does (#315). Submit it again and it goes to
  review like any read. While a revised case is open and not yet resubmitted, the
  *Give this case back* button reads **Discard changes and close** (0.22.1): it
  puts your submission back for review exactly as you submitted it, and the case
  does not go back to the pool.
- A row you can't revise now is greyed out; hover for why (a reviewer is looking at
  it now, you hold another case, it's the benchmark). The server's own sentence is
  shown if a Revise is refused.
- Hidden when the server is older than protocol 20.

### Search and defect cases (0.23.0, protocol 21)

- A **Search cases by name** box under the state filter in *Submissions*: it narrows
  the case list as you type to the cases whose name contains the text (any case), over
  every case, not one page. The order does not change; the count under the list says
  how many cases are shown. Works against any server.
- A case marked defect shows a red **Defect** badge in its *State* cell; hover for who
  marked it, when (US Eastern time) and why. **Defect only** beside the search box
  shows only those.
- **Mark defect…** under the list (for the selected case) asks first, says how many
  annotators hold the case now (they keep it and can finish) and takes an optional
  short reason. A defect case keeps all its data and is not given to any annotator,
  by *Get next case* or by *Assign*, until **Unmark defect** (which also asks). The
  benchmark case can't be marked. Reviewers and admins only.
- *Defect only* and *Mark defect* are hidden when the server is older than
  protocol 21.

### Uploads behind a 1 MiB proxy limit (0.23.1)

- Submissions and reviewer revisions upload in 768 KiB pieces instead of 8 MiB, so
  a file over 1 MiB (an extended read, for one) no longer fails with *HTTP 413*
  behind a proxy that keeps nginx's default 1 MiB request-body limit.
- If the proxy still refuses a piece as too large, the module halves the piece size
  (down to 64 KiB), carries on from what the server has, and keeps the smaller size
  for the rest of the session. If even 64 KiB is refused, it says the server's proxy
  refused the upload size and to tell the project lead; nothing is submitted and the
  local copy is kept.
- Module only: the protocol stays 21 and the server is unchanged.

### Reviewers see the annotator's note; a shorter extended-classes row (0.24.0)

- Opening a submission for review shows the note its annotator sent with it (the
  text in *Case notes* when they pressed *Submit*) at the top of **Case notes**, as
  *Annotator's note: ...*, above the case's thread, which is unchanged. Nothing
  extra is shown when the read was submitted without a note. It is shown as plain
  text, whatever it contains. The posting row stays greyed out while reviewing.
- The long paragraph of instructions under **Extended classes** is gone, and the
  toggle reads *Extended classes* (no longer *Extended classes (optional)*; the
  classes are still optional, as its tooltip says). The toggle, its tooltip, the *Show:* and *Complete:* tick-boxes and their tooltips
  are unchanged; how to use the classes is in the annotator guide
  ([docs/ANNOTATOR-SETUP.md](../../docs/ANNOTATOR-SETUP.md)).
- Module only: the server already sends `annotatorNote` in every reviewer row
  (`GET /segqueue14/review/case/{id}/submissions`, the queue, the submission and the
  claim), so the protocol stays 21 and the server is unchanged.

**The reviewer's case list** (0.18.0, #280) is sorted by submission time, newest
first; rows with nothing submitted yet come last. The *Submitted (ET)* column shows
that time in US Eastern time (America/Toronto, daylight saving included), e.g.
`2026-11-10 14:32 ET`. It uses the `submittedAt` the server already sends, so the
server is unchanged for this.

## Install

The short guide for new annotators is [docs/ANNOTATOR-SETUP.md](../../docs/ANNOTATOR-SETUP.md);
the full reference (every route, Windows and Mac) is [docs/SETUP-GUIDE.md](../../docs/SETUP-GUIDE.md). The notes below
are the reference.

**Running SegQueue 0.13 or older:** open SegQueue and press *Check for updates* →
**Update and restart**. It installs SegQueue14 over it; afterwards open
**Segmentation → SegQueue14** (opening "SegQueue" takes you there). Your server
address carries over. If you installed the separate SegQueue14 0.1.0 extension,
uninstall it first.

**Supported Slicer versions:** **5.8.1** is the version annotators are asked to
install. The newest stable Slicer (5.12.4 as of 2026-10-23) and the current
preview (5.13.0) are supported through the module-path route below: CI installs
SegQueue that way into all three on macOS (Apple Silicon and Intel) and Linux,
restarts, and runs the module's self-test from the install (`install-anywhere`
in `.github/workflows/slicer-selftest.yml`, weekly and on every pull request
that touches the module). A preview is a daily build, so a preview that breaks
SegQueue is caught by the weekly run, not promised in advance.

**First install, any Slicer version, any OS:**

1. Download `SegQueue-<version>-Slicer-5.8.zip` (not the `-macOS` one) from the
   newest `segqueue-v…` release, and unzip it (double-click it). You get a
   folder named `SegQueue`. Put it somewhere you keep, e.g. your home folder.
2. In Slicer: **Edit → Application Settings → Modules**. Under *Additional
   module paths* press **Add** and choose the folder
   `SegQueue/lib/Slicer-5.8/qt-scripted-modules` (e.g.
   `~/SegQueue/lib/Slicer-5.8/qt-scripted-modules`). Press OK, then restart
   Slicer.
3. Install **SegmentEditorExtraEffects** (Draw tube) from the Extensions Manager
   if you have not already.
4. The module is under **Segmentation → SegQueue**.

This route does not depend on Slicer's version or revision, which the Extensions
Manager does (below). Each Slicer build, and every new preview, keeps its own
settings: after installing a new Slicer, add the same folder again (step 2).

**First install through the Extensions Manager (Slicer 5.8.0/5.8.1 only):**
download `SegQueue-<version>-Slicer-5.8.zip`, then **Extensions Manager →
Install from file** → restart. On a Mac use
`SegQueue-<version>-Slicer-5.8-macOS.zip`. This route only works on Slicer 5.8:
macOS Slicer installs only from the `Slicer.app/Contents/Extensions-<revision>/`
path inside a zip, so a Mac on any revision not listed in `MACOS_REVISIONS`
(`slicer/build-extension14.py`) fails with "Failed to copy directory" (#94,
#97), and on every OS Slicer 5.10 and later look for `lib/Slicer-<their
version>`, not the zip's `lib/Slicer-5.8`. Use the module-path route on any other
Slicer. Do not use both routes in one Slicer (two copies of the module). From a
checkout: add `slicer/SegQueue14` to *Additional module paths*.

**Updating:** the module checks for a newer release when opened and offers
**Update and restart** (`SegQueue14Lib/updater.py`, which only installs archives
that carry SegQueue14). It works the same for both install routes: it updates
from the archive for the Slicer version the install was built for
(`lib/Slicer-5.8`), whatever Slicer is running. If the server's protocol has
moved on, login is refused with *"Update the SegQueue14 module"*. The server
accepts protocols 17 (0.17.x) and 18 (0.18.0): 0.17.x keeps working for
four-class work (D44).

## For developers

**The submission file** (0.17.0, protocol 17, D39, #275) is a *class stack*
(`src/segqueue14/labelfile.py`): one gzip NRRD on the CT grid, voxel for voxel, with
one uint8 0/1 channel per class in project order (LM, LAD, LCx, RCA) and
`SegQueue14_Format:=class-stack-nrrd/1` in its header. Its header also carries
Slicer's segmentation keys (one layer per class), so Slicer opens it as four named,
overlapping segments; the scoring worker, `segqueue14-export` and anything else read
it with numpy alone (`labelfile.read_class_stack`). Up to 0.16.x a submission was one
label volume, which keeps one class per voxel: an untouched seeded case came out as
all RCA. Those files stay readable everywhere; the submission row's `labelFormat`
(read from the stored file's header) says which a file is. From 0.18.0 an
extended read has 21 channels (`labels.ALL_NAMES`); the header's
`SegQueue14_Classes` names them, and the server records them as the row's `classes`
and `extended`.

`SegQueue14Lib/` (client, cache) has no Slicer imports and is tested by
`tests/test_segqueue14_client.py`; the module itself is checked statically by
`tests/test_segqueue14_module.py`. `tests/segqueue14_e2e.py` runs the module's
network path against a live server.
