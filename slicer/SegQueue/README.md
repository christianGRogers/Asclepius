<p align="left">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="Resources/Icons/wordmark-dark.png">
    <img src="Resources/Icons/wordmark-light.png" width="190" alt="Bradensbay">
  </picture>
</p>

# SegQueue

A 3D Slicer module for distributed coronary artery segmentation.

An annotator opens Slicer, presses **Get next case**, and a CT volume arrives
with the project's segments already created, named and coloured. They trace the
vessels, press **Validate & submit**, and the local copy is deleted. There is no
file browser, no folder to pick, no naming convention to get wrong, and no
server URL to remember past the first login.

Three decisions shape everything below.

* **The server owns the protocol.** Segment names, label values and colours come
  from the server at login, not from anything shipped in the module. Adding a
  branch mid-project is a server-side settings change; nobody reinstalls
  anything.
* **Local data is a lease, not a library.** Every byte lives under one managed
  cache directory holding one case, purged the moment that case is submitted,
  released, or the annotator logs out.
* **Nothing the client says is trusted.** Validation runs here so the annotator
  gets an instant, specific complaint instead of a rejection three days later —
  and the identical checks run again on the server, because a client can be old
  or patched.

---

## Requirements

| | |
|---|---|
| 3D Slicer | **5.8** (extensions are packaged per minor version; a 5.8 build is not offered to 5.9) |
| SegmentEditorExtraEffects | **Optional.** Adds *Draw tube* and other effects to the Segment Editor. Nothing in the workflow needs it — trimming uses *Scissors*, which is core Slicer |
| Python packages | None. `requests` already ships with Slicer, and the shared `segqueue` package is stdlib-only and vendored into the archive |

SegmentEditorExtraEffects was required up to 0.7.x, when the panel drove *Draw
tube* itself. It no longer does: every effect is reached through the Segment
Editor, and the one the workflow is built around is *Scissors*, which ships with
Slicer. Install the extension if you want the extra effects, but a case can be
finished without it.

## Install

### From a release (what annotators do)

1. Download `SegQueue-<version>-Slicer-5.8.zip` from the
   [releases page](https://github.com/christianGRogers/Asclepius/releases).
2. Slicer → **Extensions Manager** → **Install from file** → pick the zip.
3. Restart Slicer.
4. The module appears under **Segmentation → SegQueue**, with the Bradensbay
   mark beside it in the module selector.

No build tools, no admin rights, nothing to compile.

### From a checkout (what developers do)

The module loads straight out of the repository — it finds the shared
`segqueue` package at `<repo>/src` when there is no vendored copy beside it.

Run this in Slicer's Python Console (**View → Python Console**, or `Ctrl+3`):

```python
exec(open(r"<repo>/slicer/install-segqueue.py").read())
```

That adds `slicer/SegQueue` to *Additional module paths* and offers to restart.
By hand it is the same three clicks: **Edit → Application Settings → Modules →**
drag `slicer/SegQueue` into *Additional module paths* → restart.

## Updating

The module checks for a newer published release when you open it, and offers to
install it in one press.

```
[ SegQueue 0.3.0 is available. You are running 0.2.0. ]
[ Update and restart ]  [ What changed ]  [ Not now ]
```

**Update and restart** downloads the release archive, checks it is a real
SegQueue package for this Slicer version, copies the current install aside, swaps
the files in, and offers to restart. Your draft is autosaved before anything is
touched, and the case you are on is still assigned to you when Slicer comes back
— so updating mid-case costs a restart, not your work.

It refuses rather than guesses in three cases, each with a message saying what
to do instead: the module is running from a **git checkout** (use `git pull`),
it is **not installed as an extension**, or Slicer's extension folder is **not
writable** by your account.

The backup it takes is a sibling directory named
`qt-scripted-modules.backup-<timestamp>`. Nothing deletes it; if an update ever
goes wrong, that is the previous version, intact.

Some details worth knowing:

- **The check is quiet.** Offline, behind a proxy, GitHub down, rate-limited —
  all of them mean "no update" and none of them shows you a dialog. It runs a
  second after the panel appears, never before, so it cannot delay you getting
  into a case.
- **It runs at most every 6 hours per machine.** Unauthenticated GitHub allows
  60 requests an hour *per address*, which a teaching lab shares. **Check for
  updates** in the Server section ignores that cache and always tells you what
  it found.
- **Only SegQueue releases count.** This repository also holds the training
  pipeline; the check only considers tags shaped `segqueue-v<version>` that
  carry an archive built for your Slicer version. Prereleases are ignored.
- **Nothing is deleted from your install.** Files are added and overwritten.
  A file from an older version that no longer ships is left in place — Slicer
  ignores it, and deleting the wrong file mid-swap is not recoverable.

## First run

| Field | |
|---|---|
| **Server** | Base URL of the SegQueue server. `/api/v1` is appended automatically. Remembered between sessions |
| **Username** | **Not saved.** Typed each session |
| **Password** | **Not saved.** One login per Slicer session |

Neither the username nor the password is remembered, and an upgrade deletes
any username an earlier version stored. This is what keeps a shared
annotation workstation honest: a pre-filled name means the next person tabs
past someone else's identity, and only the password stands between them and
that person's queue. Only the server URL and cache root persist.

**Log out and purge** ends the session *and* deletes every cached case, which is
what makes a shared teaching workstation safe to walk away from.

## The loop

1. **Get next case.** The server assigns one; it downloads, the segments are
   created already named and coloured, window/level is set for contrast-enhanced
   coronary CT (W 800 / L 300 — auto window/level on a whole-chest CT is useless
   for a 3 mm vessel), and the Segment Editor opens on it. If the case ships a
   coronary mask, it is standing centred in the 3D view by the time you look up.
2. **Divide the mask**, if the case has one. Every branch already holds a copy of
   the whole tree; show one, cut it back to that vessel, hide it, move on. See
   below.
3. **Validate & submit.** The submission is checked, uploaded in resumable
   chunks, and the local copy deleted.

If anything about the case is worth passing on — a stent, a motion artefact, an
ambiguous branch — put it in **Case notes** before you submit. See below.

Everything between step 1 and step 3 happens in the **Segment Editor**: which
segment you are editing, which effect you are using, what it is masked to, and
which segments are visible. The module deliberately puts nothing in front of it.

### The panel's own buttons

* **Get next case** — asks the server for an assignment.
* **Save draft now** — the segmentation autosaves every two minutes; this forces
  it.
* **Check without submitting** — runs the full validation and reports, without
  uploading.
* **Validate & submit** — checks, uploads, and deletes the local copy.
* **Give this case back** — releases the assignment (with a reason) and purges
  it locally. Use it instead of leaving a case parked.

## Dividing the coronary mask

Most cases arrive with the coronary tree **already drawn**, as one unlabelled
mask the source dataset shipped. On those cases the job is not to trace the
vessels — something already did — it is to say which part of that mask is the
LAD, which is the LCx, and which is the RCA.

So when a case with no work on it opens, **every branch already holds a copy of
the whole tree**, and all of them are **hidden**. The mask itself is visible, on
the slices and standing centred in the 3D view, and that is the only thing you
see. Then, for each vessel:

1. **Show it** — click its eye in the Segment Editor's segment list. It comes up
   as the entire tree.
2. **Cut it back** to just that vessel. **Scissors** with *Erase inside* and a
   free-form shape is the fast way: drag a loop round what is *not* this vessel,
   in the 3D view or on a slice, and it is gone from this segment. Every other
   effect works too — this is the ordinary Segment Editor.
3. **Hide it again** and move to the next.

The branches are independent copies, so they can be done in any order, and
nothing you cut from one affects another. There is no state to keep track of:
what a branch holds is what you left in it.

Some details worth knowing:

- **Two branches must not end up sharing a voxel.** A label volume holds one
  label per voxel, so an overlap cannot survive the export — one of the two would
  be silently overwritten. **Check without submitting** catches it and names the
  branch that would lose voxels, and submission is blocked until it is trimmed
  apart. This is the one thing the old one-vessel-at-a-time workflow made
  impossible and this one does not, so it is checked rather than trusted.
- **Set overwrite mode to *Overwrite none*** — the module already does, on every
  case. It is what stops editing one branch from carving into another.
- **The mask is never submitted.** It stays scaffolding: the export copies only
  the project's own segments, so it is structurally incapable of reaching the
  server however you cut it up. The same goes for the heart region mask.
- **A reopened draft resumes.** The copy-from-the-mask start happens only on a
  case with no work on it; coming back tomorrow gives you your own trimming
  back, untouched.
- **Ordinary undo works.** `Ctrl+Z` steps back through cuts like any other
  Segment Editor edit.

Client-side only. The mask has shipped with cases since 0.1.0.

## Case notes

The panel carries a **message thread on each case**. It replaced the project
instructions, which were the same text on every case and read once in week one;
this space is worth more as the thing that *differs* between cases.

Type a line, press Enter or **Post**, and it is on the server. Everyone who
works on that case sees it, with your name on it.

Notes follow the **case**, not the assignment. The annotator doing the rework,
the reviewer who rejected it, and whoever had the case before them all read the
same thread — which is the point, because "the RCA ostium is behind a stent, the
seed mask is wrong from slice 180" belongs to the case and would vanish with the
assignment.

- **Append-only.** Nothing can be edited or deleted. A shared editable field
  loses one person's text the moment two people have the case open, and loses
  attribution always — and a remark from a reviewer is not the same claim as the
  same words from a first-week annotator.
- **The author comes from your session**, never from the client. An identifier a
  client could set is a claim about identity, not a fact about it.
- **Rejections post themselves.** When a reviewer rejects an attempt, the server
  adds a note saying who, which attempt, and why. The rework is usually done by
  someone else, who would otherwise see the reviewer comment with no idea what
  was tried before.
- **Unposted text is saved with the case.** Your half-written note goes into the
  case's manifest on every autosave, on **Save draft now**, and when you leave
  the module or close Slicer — and comes back when you reopen the case. It is
  purged with the case on submit, like everything else local.
- **The thread refreshes every 90 seconds** while a case is open, and on
  **Refresh**. Slow on purpose: notes are left for the next person, not chatted
  in real time, and every poll is thirty machines against one small server.

Visibility is "anyone who has ever held this case, plus reviewers". An annotator
who has never seen a case cannot read remarks about it — the thread names
people, and thirty undergraduates share a queue.

Notes are capped at 2,000 characters and truncated rather than refused.

## Submissions

Reviewers get an extra **Submissions** section: every case in the project, what
has happened to it, and what to do about it. It replaced a review *queue*, which
listed only the sampled fraction awaiting a verdict and so could not answer the
question reviewers arrive with — *where is case s0042, and who has it*.

The list is **every case in the project**, paged through in full rather than
one page deep: a thousand-case pool that showed its first two hundred and looked
complete is the one mistake a reviewer cannot catch by eye.

The top table is one row per lease, so a case out with two annotators at once
shows twice, and a case nobody has been given still gets a row saying so. Filter
it by state, or by **Unassigned**. Selecting a row fills the lower table with
**every submission ever made against that case**, oldest first: submissions are
append-only, nothing is ever replaced, and a superseded attempt is still there
months later.

Then, with a submission selected:

* **Open selected submission** — downloads the segmentation and its source
  volume and loads both. Takes the highlighted history row, so you can open an
  older attempt and compare it against what replaced it; with no history row
  highlighted it opens the case's latest.
* **Approve** — accept it as it stands. Approval is the only state the training
  export selects.
* **Save my changes & approve** — upload whatever is now in the scene as *your*
  corrected version and approve that. Edit it in the Segment Editor first; this
  is the fast path for a submission that is nearly right.
* **Return to pool** — hand the case back so somebody else gets it.
* **Open case image** — loads the case's own volume and whatever masks ship with
  it. A case nobody has worked on has no submission to open, and the image is
  what says whether the scan is usable at all.
* **Take case & segment it** — assigns the case to *you* and opens it as an
  ordinary case, so you can segment and submit it yourself. It becomes genuinely
  yours: it shows in your queue, counts against your quota, and is submitted and
  reviewed like anyone else's.

  Deliberately an ordinary assignment rather than a reviewer-only way to submit.
  Everything that makes a submission correct hangs off having one — the project's
  segments with the right names and label values, the branches started from the
  coronary mask, the autosave, the elapsed-time record, the overlap check, and an
  upload the server will accept. A second path would have to reproduce all of
  that, and would drift from it.
* **Assign case** — hands the selected case to the chosen annotator straight
  away, without waiting for them to ask. The count beside each name is what they
  are already holding, which is the number that decides who should get the next
  one. Refused if the case is retired, already out, or has been theirs before.

Two things about that worth knowing.

**Your corrections are stored beside the annotator's, never over them.** Saving
writes another submission on the same assignment, credited to you, and the
annotator's upload is kept exactly as they sent it. That is not just for the
audit trail: per-annotator agreement numbers are computed from the author, and
quietly attributing a reviewer's fixes to the annotator would flatter precisely
the submissions that needed fixing.

**A returned case does not go back to the same annotator.** `assignedUserIds` is
a permanent record of everyone who has held a case and `Case.claim` excludes
them, so the case is offered to somebody else. That is the same list that keeps
a blind duplicate's two annotators independent, so it is not a per-case setting.

**Reject was retired in 0.9.0.** A reviewer who can open a submission and fix it
in Slicer has a shorter path to a correct label than a round trip through the
annotator, and where the work genuinely needs redoing, returning it to the pool
covers it. Assignments already sitting in `rejected` when this shipped still
transition normally — the states remain in the machine, nothing new enters them.

## What lands on disk


```
~/.segqueue/cases/case-<assignmentId>/
    <casename>.nrrd          the downloaded CT
    segmentation.seg.nrrd    the autosaved draft
    segqueue.json            manifest: elapsed time, paths, and your unposted note
```

One case at a time, purged on submit, release or logout.

The cache root is configurable in the panel. Slicer's own `QSettings` keeps the
server URL and the cache root — never the username, the token or the password.

## Branding

The module ships its own identity in two places, and Slicer's own logo in
neither:

```
Resources/Icons/SegQueue.png         module icon (256 px), shown in the module selector
Resources/Icons/wordmark-light.png   panel title-bar wordmark, light themes
Resources/Icons/wordmark-dark.png    panel title-bar wordmark, dark themes
Resources/Logo/*.svg                 vector sources: mark, wordmark, lockup, reversed, one-colour
```

**The module icon** is picked up by Slicer automatically from
`Resources/Icons/<ModuleName>.png`, and set explicitly in `SegQueue.__init__`
as well — the automatic lookup resolves against `parent.path`, which differs
between a checkout and an installed extension.

**The panel wordmark** replaces the 3D Slicer logo that sits above the module
panel. That logo is a `QLabel` named `LogoLabel`, installed by the application
as the panel dock's title-bar widget, and it is *shared application chrome* —
so the module borrows it in `enter()` and hands the original pixmap back in
`exit()` and `cleanup()`. Switch to Volumes and Slicer's logo is there again,
unmodified. The wordmark is scaled to the exact pixel height and device pixel
ratio of the logo it replaces, so the title bar never changes size as you move
between modules.

The wordmark carries the name only — no mark. The mark is already the module
icon in the selector directly below it, and stacking the two reads as two
pieces of branding rather than one.

Light and dark are chosen from the application palette. They are two drawings,
not one asset lightened: on a dark background the wordmark is white, and the
mark inverts outright — the bay turns white and the trace navy. Recolouring a
single PNG will look wrong.

To change either, edit the SVGs under `Resources/Logo/` and re-render:

```bash
python -c "import cairosvg; cairosvg.svg2png(url='Resources/Logo/bradensbay-mark.svg', \
    write_to='Resources/Icons/SegQueue.png', output_width=256, output_height=256)"
python -c "import cairosvg; cairosvg.svg2png(url='Resources/Logo/bradensbay-wordmark.svg', \
    write_to='Resources/Icons/wordmark-light.png', output_height=128)"
```

Missing or unreadable artwork is ignored rather than fatal: the panel keeps
Slicer's logo and the module loads normally.

Palette: deep navy `#0A2540`, clinical blue `#1466D8`, teal `#16BFB2`.

## Releases and CI

`.github/workflows/segqueue-release.yml` runs on every push to `main` that
touches `slicer/`, `src/segqueue/` or the client tests. It:

1. runs the client-side `segqueue` tests (not the server ones — they want a
   MongoDB, and say nothing about whether this archive is safe to install);
2. builds the archive;
3. checks the archive is installable — correctly named, not corrupt, carrying
   the module, the updater, the shared package and the icons, with a `.s4ext`
   descriptor — using the same check the updater runs on an annotator's machine;
4. uploads it as a run artifact regardless;
5. publishes a release **only if `segqueue-v<__version__>` does not already
   exist**.

So **bumping `__version__` in `SegQueue.py` is what ships a release.** A push
that does not bump it is built and tested but publishes nothing — otherwise a
README typo would prompt thirty annotators to restart Slicer.

The tag shape matters: the updater matches `segqueue-v*` and ignores every other
tag in the repository. `tests/test_segqueue_release.py` asserts the prefix, so
changing it in one place and not the other fails CI rather than silently
stranding every installed client.

### Checking it against a real Slicer

The pytest suite cannot import `SegQueue.py` — it needs Qt, VTK and Slicer — so
the module's dependencies on Slicer are checked by a script Slicer runs itself:

```bash
"C:\...\Slicer.exe" --no-splash --no-main-window --python-script tests\slicer_selftest.py --exit-after-startup
```

It exits non-zero on failure; set `SEGQUEUE_SELFTEST_OUT` to a path to also get
the report as a file. **Run it before a release.** `.github/workflows/slicer-selftest.yml`
also runs it weekly and on demand against the current Slicer release — which is
the early warning that a new Slicer broke the module — but deliberately not on
pull requests, where downloading 1.5 GB of Slicer under a virtual framebuffer
fails for reasons that have nothing to do with the change under review.

It checks the things whose failure mode is *silence*: that the effects the
workflow needs are in the build, that the 3D view still answers the calls that
frame it, that writing one mask into four segments leaves four segments each
holding that mask, and that the export then flattens overlapping segments the way
the overlap check assumes. A segmentation stores overlapping labelmaps across
*layers*, and a write that landed in the shared layer instead would erase the
segments beside it — three empty branches and no error anywhere. The 3D camera
calls are guarded against `AttributeError`, so a rename in Slicer would be silent
too. And a case that opens with the wrong thing in its branches is wrong in a way
every individual piece of it is right.

It loads the module **by path**, not by `import SegQueue`, because Slicer
pre-imports an installed copy of the extension if one exists — so a plain import
tests the installed build rather than the one being edited.

To build locally:

```bash
python slicer/build-extension.py            # -> dist/SegQueue-<version>-Slicer-5.8.zip
python slicer/build-extension.py --print-version
```

Plain Python — no CMake, no Slicer needed. The archive vendors `src/segqueue`
beside the module, **so rebuild after any change to `src/segqueue`** or
annotators run an old wire protocol against a new server.

## Troubleshooting

**"Could not import the segqueue package"** — the module is loaded from a
checkout with no `src/` beside `slicer/`, or from an archive built without the
vendored copy. Install the release zip, or load the module from a full checkout.

**"No extension description found in archive"** — the zip is missing its
`.s4ext` descriptor in `share/Slicer-5.8/`. Rebuild with `build-extension.py`;
do not hand-zip the module directory.

**Draw tube is missing** — SegmentEditorExtraEffects is not installed. Extensions
Manager → Install Extensions → SegmentEditorExtraEffects → restart. Optional since
0.8.0: trimming uses *Scissors*, which ships with Slicer.

**"… loses N of its M voxels on export"** — two branches cover the same voxels,
and a label volume can only give a voxel to one of them. Show both in the Segment
Editor and trim until they no longer overlap. Overwrite mode should be *Overwrite
none*, which the module sets on every case.

**The Slicer logo still shows above the panel** — `Resources/` did not make it
into the install. Check that `Resources/Icons/` sits beside `SegQueue.py` in
`.../Slicer 5.8.1/.../Extensions-<rev>/SegQueue/lib/Slicer-5.8/qt-scripted-modules/`,
and rebuild if not. The swap also happens on `enter()`, so it appears when you
open the module, not at startup.

**The update banner never appears** — the check is silent by design. Press
**Check for updates** in the Server section: it ignores the 6-hour cache and
reports what it found, including why it could not look.

**"GitHub is rate-limiting update checks from this network"** — 60
unauthenticated requests an hour are shared by everyone on your address. It
clears within the hour; installs from the releases page still work meanwhile.

**An upload died halfway** — uploads are chunked and resumable; retry the submit.
The client asks the server how much it already has and continues from there.

## Version history

**0.9.0** — **The review queue is now a submission viewer.** Reviewers get
every case in the project with what has happened to it, plus the full
append-only submission history of whichever case is selected, instead of a queue
holding only the sampled fraction awaiting a verdict.

**Fixes review not loading at all.** The old path wrote the downloaded volume to
`volume.nrrd` regardless of what it was. This project's volumes are `.nii.gz`,
Slicer picks its reader from the extension, and a gzipped NIfTI under a `.nrrd`
name downloads cleanly, verifies cleanly and then refuses to open with a message
that never mentions the name — so **Claim & open** appeared to do nothing. The
real filenames now travel with the submission row, and the bytes are sniffed
afterwards as a fallback, which is the protection the annotator path has had
since 0.2.0.

New reviewer actions: **Save my changes & approve**, which stores the reviewer's
corrected version as another submission credited to them and leaves the
annotator's exactly as sent, and **Return to pool**, which frees the case for a
different annotator. **Reject & send back is retired** — the `rejected` and
`rework` transitions stay in the state machine so assignments already in flight
can still finish, but no endpoint enters them.

**0.8.0** — **The Vessel tools panel is gone, and so is the workflow it existed
to sequence.** Every branch now simply starts as its own copy of the coronary
mask, hidden, and the annotator shows one, cuts it back to that vessel, and hides
it again — in the Segment Editor, which could already do all of it.

What that removes: the vessel buttons and their checklist, the tool buttons, the
tube radius and brush sliders, **Apply tube**, the masking checkboxes, **Start
this vessel over**, the view-helper buttons, and the panel's own keyboard
shortcuts. Also the remainder arithmetic underneath them — a vessel being handed
"everything no other vessel has claimed" was the source of both 0.7.3 bugs, and
of the ordering rule that made them possible: which branch you opened first
changed what the others started as.

What it costs: branches can now overlap, because they start identical. A label
volume holds one label per voxel, so an overlap cannot survive the export — one
branch would be silently overwritten. **Check without submitting** now measures
what is in the editor against what the export produces and blocks submission
naming the branch that would lose voxels. Window/level and centring still happen
automatically on case open; only the buttons that re-applied them are gone.

The 3D view is also **centred** when the mask goes into it, which it never was:
the surface built correctly and sat outside the camera's frame, so every case
started by reaching for the view controller's centre button. And
SegmentEditorExtraEffects is no longer required — trimming uses *Scissors*, from
core Slicer.

`tests/slicer_selftest.py` is rewritten around what only a real Slicer can
answer: that one mask written into four segments leaves four segments each
holding it (a segmentation splits overlapping labelmaps across *layers*, and a
write into the shared layer would erase its neighbours silently), that the export
then flattens them the way the overlap check assumes, and that a trimmed-apart
case is not falsely accused.

**0.7.3** — Unreleased; folded into 0.8.0.

**0.7.2** — Fixes the trim tool not drawing. Scissors is a C++ effect whose
`Shape` and `Operation` parameters are strings converted to enums by name, with
no validation: 0.7.0 set `FREE_FORM` where Slicer spells it `FreeForm`, which
converts to -1, builds no drawing pipeline, and leaves a tool that activates and
then ignores the mouse. `tests/slicer_selftest.py` is rewritten to run the module
inside Slicer and check exactly this class of thing — the parameter spellings
against the defaults Slicer itself writes, and the vessel-fill arithmetic against
known voxel counts.

**0.7.1** — Fixes a dead panel in 0.7.0: every vessel button raised on click,
because one call to a method deleted in that release survived the refactor. Adds
a static check over the module's own `self.x` calls, signal connections and key
bindings, which catches that class of mistake without a running Slicer — it is
invisible to `pyflakes` and shows up only as a control that silently does
nothing. A vessel is also now handed the remainder at most once per case;
**Start this vessel over** is the way to refill one.

**0.7.0** — Dividing by trimming. A vessel now starts as everything the mask
has left, and the annotator cuts away what is not it with **Trim** (`E`); the
next vessel starts as exactly what was cut off. Replaces the marker-and-divide
and circle-to-select workflows of 0.5.0 and 0.6.0, and the panel with them —
three controls and no prose. Nothing cut is lost, an untrimmed vessel starves
the ones after it so the workflow cannot be skipped, and trimming ignores the
brush masks so a cut cannot leave specks behind. Removes `segqueue.seedsplit`
and `segqueue.lasso`. Still client-side only.

**0.6.0** — Circling a branch in 3D. Drag a loop around an artery in the 3D
view and it fills in: **Circle branch in 3D** (`L`), one loop per press, with the
view rotating normally in between. What is behind another branch is left alone —
per-pixel nearest-surface, then a single connected piece of the tree — so
circling the LAD with the RCA behind it takes none of the RCA, and circling only
the visible length of a vessel still claims all of it. Adds `segqueue.lasso`
(the screen-space selection, unit-tested); loops and clicked markers are the same
thing to the partition and mix freely. Still client-side only.

**0.5.0** — Dividing the coronary mask. The pre-existing tree is now rendered in
the 3D view as the case opens, and **Mark branch** / **Divide** split it between
the project's vessels: every voxel goes to the branch whose markers are nearest
*measured along the vessel*, so the LAD and the LCx separate at the left main and
a separate RCA needs one marker. Re-dividing keeps hand-painted corrections;
unmarked pieces are reported rather than absorbed. Adds `segqueue.seedsplit`
(the partition, unit-tested). **Client-side only — no server change, and cases
already ship the mask.**

**0.4.0** — Case notes. The panel area that held the project instructions is now
a per-case message thread: append-only, attributed server-side, visible to
everyone who has worked on the case, with unposted text saved alongside the
segmentation draft. Reviewer verdicts post themselves into it. Adds
`GET`/`POST /segqueue/case/<id>/notes` — **the server must be redeployed for
this release to do anything.**

**0.3.0** — Self-update. The module checks GitHub for a newer release when it
is opened and installs it in one press, with a backup and a refusal to touch a
checkout. Releases are now built and published by GitHub Actions on every
version bump. Adds `segqueue.release` (release selection, unit-tested) and
`SegQueueLib/updater.py`.

**0.2.0** — Bradensbay identity: module icon, and the Bradensbay wordmark in
place of the Slicer logo above the panel while SegQueue is open (restored on
the way out). Light and dark variants, vector sources, and `iconurl` in the
extension descriptor. The username is no longer remembered between sessions,
and any username stored by an earlier version is deleted on upgrade. No
protocol changes.

**0.1.0** — Initial release.
