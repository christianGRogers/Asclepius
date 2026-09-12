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
| SegmentEditorExtraEffects | **Required.** Provides *Draw tube*, the tool this module is built around |
| Python packages | None. `requests` already ships with Slicer, and the shared `segqueue` package is stdlib-only and vendored into the archive |

Install **SegmentEditorExtraEffects first**, from Extensions Manager → Install
Extensions. "Install from file" does not resolve dependencies, so installing
SegQueue will not pull it in — the panel checks at runtime and says so, but it
is one less restart if you do it up front.

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
that person's queue. Only the server URL, cache root and tool sizes persist.

**Log out and purge** ends the session *and* deletes every cached case, which is
what makes a shared teaching workstation safe to walk away from.

## The loop

1. **Get next case.** The server assigns one; it downloads, the segments are
   created already named and coloured, window/level is set for contrast-enhanced
   coronary CT (W 800 / L 300 — auto window/level on a whole-chest CT is useless
   for a 3 mm vessel), and the Segment Editor opens on it. If the case ships a
   coronary mask, it is standing in the 3D view by the time you look up.
2. **Divide the mask**, if the case has one — mark each branch, press `D`, and
   the tree is split into the project's vessels. See below. What is left is
   touch-up rather than tracing.
3. **Pick a vessel** — number keys `1`–`4` (and up to `9`), or the buttons. The
   button shows a ✓ once that vessel has content, and `(optional)` where the
   project does not require it.
4. **Draw tube (`Q`)** — click points down the centreline of the artery, then
   **Apply (`A`)**. Sections *accumulate*: draw a wide one proximally and
   narrower ones as the vessel tapers, all adding into the same segment. Radius
   defaults to 1.25 mm (a left main lumen is ~2 mm, a distal LAD under 1).
5. **Paint (`W`)** to fix what the tube missed. Sphere brush, 1.5 mm, restricted
   to 150–1000 HU so a slightly sloppy stroke still gives a clean lumen edge.
6. **Validate & submit.** The submission is checked, uploaded in resumable
   chunks, and the local copy deleted.

If anything about the case is worth passing on — a stent, a motion artefact, an ambiguous branch — put it in **Case notes** before you submit. See below.

Everything else in the Segment Editor is still one click away — the four buttons
are the fast path, not a cage.

### Keys

| Key | |
|---|---|
| `1`–`9` | Select vessel *n* |
| `M` | Mark the selected branch on the coronary mask |
| `D` | Divide the mask between the branches you have marked |
| `Q` | Draw tube |
| `W` | Paint |
| `A` | Apply the tube section you just placed, and start the next |

### The other buttons

* **Save draft now** — the segmentation autosaves every two minutes; this forces
  it.
* **Check without submitting** — runs the full validation and reports, without
  uploading.
* **Give this case back** — releases the assignment (with a reason) and purges
  it locally. Use it instead of leaving a case parked.
* **Centre on heart**, **CTA window/level**, **Show in 3D** — view helpers.

## Dividing the coronary mask

Most cases arrive with the coronary tree **already drawn**, as one unlabelled
mask the source dataset shipped. On those cases the job is not to trace the
vessels — something already did — it is to say which part of that mask is the
LAD, which is the LCx, and which is the RCA.

So the mask is **rendered in the 3D view as the case opens**, and there is a tool
that splits it:

1. **Pick a vessel** (`1`–`4`).
2. **Mark branch (`M`)** — click a few points down that artery, in the 3D view or
   on the slices. Placement stays armed, so it is a run of clicks, not a
   click-and-return-to-the-button.
3. Pick the next vessel and mark it. The number keys move the marking with you
   mid-run; you do not press `M` again.
4. **Divide (`D`).** Every voxel of the mask is given to the branch whose markers
   are nearest, and the vessels fill in.

Nearest **along the vessel**, not through the air. That is the entire reason this
works:

- The **LAD and the LCx are joined** at the left main, so no straight-line rule
  separates them — but measured along the lumen, a voxel in the mid-LAD is far
  from an LCx marker even where the two vessels sit millimetres apart in space.
- The **RCA is usually a separate piece** of the mask, so one marker anywhere on
  it claims all of it, and a marker on the left tree cannot reach it at any
  distance.
- Where the boundary between two branches lands is **what the markers are for**.
  With one marker at the end of each arm it falls halfway along the left main;
  marking further down one arm pulls it the other way. That is how you say "the
  left main belongs to the LAD" without painting a voxel.

Then **paint (`W`) and draw tube (`Q`) as usual** — to extend a branch the mask
stopped short of, or to fix a boundary you disagree with. The division is a head
start, not a verdict.

Some details worth knowing:

- **Dividing again is safe.** Divide, look at it in 3D, drop two more points on
  the branch that came out wrong, divide again. The previous division is taken
  back out of each vessel before the new one goes in, so **anything you painted
  by hand survives**. *Clear markers* forgets the division as well as the points,
  which is the one thing that ends that guarantee — after it, a fresh divide adds
  to what is already there.
- **What it cannot place, it hands back.** A piece of the mask with no marker on
  it — an aortic root fragment, a vein the model caught — is left out and
  reported, rather than being glued to whichever branch happens to be nearest. If
  that is most of the mask, you are told a branch is probably unmarked.
- **A marker that misses snaps onto the mask**, but only by a few voxels. Beyond
  that the click was meant for something else, and dragging it onto the nearest
  vessel would hand a whole branch to a label you never pointed at — which looks
  like work rather than like a mistake. A branch marked and still empty is called
  out by name.
- **The markers are saved with the case**, beside the draft and the unposted
  note, and come back when you reopen it. Purged with everything else on submit.
- **The mask is never submitted.** It stays scaffolding — the export copies only
  the project's own segments, so it is structurally unable to reach the server no
  matter what the division does. *Only let me paint inside that mask* and *Add
  the whole mask to this vessel* are both still there.
- **Show the mask in the 3D view** can be turned off, and is remembered. The
  heart mask is never in the 3D view: a solid chamber wall would hide the tree.

This is client-side only. The mask already shipped with the case (`hasSeed` and
`GET /segqueue/case/<id>/asset/seed`, both since 0.1.0) — 0.5.0 is the first
version to do anything with it beyond masking the brush.

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

## Review

Reviewers get an extra section: refresh the queue, **Claim & open selected**,
then **Approve** or **Reject & send back** with a comment. A claimed submission
downloads the reviewer's copy alongside the source volume.

## What lands on disk

```
~/.segqueue/cases/case-<assignmentId>/
    <casename>.nrrd          the downloaded CT
    segmentation.seg.nrrd    the autosaved draft
    segqueue.json            manifest: elapsed time, paths, and your unposted note
```

One case at a time, purged on submit, release or logout.

The cache root is configurable in the panel. Slicer's own `QSettings` keeps the
server URL, username, tube radius and brush diameter — never the token or the
password.

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
Manager → Install Extensions → SegmentEditorExtraEffects → restart.

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
