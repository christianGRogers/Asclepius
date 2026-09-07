<p align="left">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="Resources/Icons/banner-dark.png">
    <img src="Resources/Icons/banner-light.png" width="182" alt="Bradensbay">
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

## First run

| Field | |
|---|---|
| **Server** | Base URL of the SegQueue server. `/api/v1` is appended automatically. Remembered between sessions |
| **Username** | Remembered between sessions |
| **Password** | **Never saved.** One login per Slicer session — on a shared machine a remembered password means every submission is attributed to whoever logged in last |

**Log out and purge** ends the session *and* deletes every cached case, which is
what makes a shared teaching workstation safe to walk away from.

## The loop

1. **Get next case.** The server assigns one; it downloads, the segments are
   created already named and coloured, window/level is set for contrast-enhanced
   coronary CT (W 800 / L 300 — auto window/level on a whole-chest CT is useless
   for a 3 mm vessel), and the Segment Editor opens on it.
2. **Pick a vessel** — number keys `1`–`4` (and up to `9`), or the buttons. The
   button shows a ✓ once that vessel has content, and `(optional)` where the
   project does not require it.
3. **Draw tube (`Q`)** — click points down the centreline of the artery, then
   **Apply (`A`)**. Sections *accumulate*: draw a wide one proximally and
   narrower ones as the vessel tapers, all adding into the same segment. Radius
   defaults to 1.25 mm (a left main lumen is ~2 mm, a distal LAD under 1).
4. **Paint (`W`)** to fix what the tube missed. Sphere brush, 1.5 mm, restricted
   to 150–1000 HU so a slightly sloppy stroke still gives a clean lumen edge.
5. **Validate & submit.** The submission is checked, uploaded in resumable
   chunks, and the local copy deleted.

Everything else in the Segment Editor is still one click away — the four buttons
are the fast path, not a cage.

### Keys

| Key | |
|---|---|
| `1`–`9` | Select vessel *n* |
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

## Review

Reviewers get an extra section: refresh the queue, **Claim & open selected**,
then **Approve** or **Reject & send back** with a comment. A claimed submission
downloads the reviewer's copy alongside the source volume.

## What lands on disk

```
~/.segqueue/cases/          one case at a time, purged on submit, release or logout
```

The cache root is configurable in the panel. Slicer's own `QSettings` keeps the
server URL, username, tube radius and brush diameter — never the token or the
password.

## Branding

The module ships its own identity rather than Slicer's generic module logo:

```
Resources/Icons/SegQueue.png        module icon (256 px), what Slicer shows in the module selector
Resources/Icons/banner-light.png    panel wordmark, light themes
Resources/Icons/banner-dark.png     panel wordmark, dark themes
Resources/Logo/*.svg                vector sources: mark, lockup, reversed, one-colour
```

The panel picks light or dark at startup from the application palette. The mark
*inverts* on dark backgrounds — the bay turns white, the trace navy — so the two
banners are different drawings, not one asset lightened; recolouring a single
PNG will look wrong. To change the mark, edit the SVGs under `Resources/Logo/`
and re-render:

```bash
python -c "import cairosvg; cairosvg.svg2png(url='Resources/Logo/bradensbay-mark.svg', \
    write_to='Resources/Icons/SegQueue.png', output_width=256, output_height=256)"
```

Banners are rendered at 364×80 and displayed at a 2× device pixel ratio, i.e. a
182×40 logical strip, so they stay sharp on HiDPI laptops. Missing or unreadable
artwork degrades to a text wordmark — it never stops the module loading.

Palette: deep navy `#0A2540`, clinical blue `#1466D8`, teal `#16BFB2`.

## Building the package

```bash
python slicer/build-extension.py
```

Writes `dist/SegQueue-<version>-Slicer-5.8.zip`. Plain Python — no CMake, no
Slicer needed to build it. The archive vendors `src/segqueue` beside the module,
**so rebuild after any change to `src/segqueue`** or annotators run an old wire
protocol against a new server.

## Troubleshooting

**"Could not import the segqueue package"** — the module is loaded from a
checkout with no `src/` beside `slicer/`, or from an archive built without the
vendored copy. Install the release zip, or load the module from a full checkout.

**"No extension description found in archive"** — the zip is missing its
`.s4ext` descriptor in `share/Slicer-5.8/`. Rebuild with `build-extension.py`;
do not hand-zip the module directory.

**Draw tube is missing** — SegmentEditorExtraEffects is not installed. Extensions
Manager → Install Extensions → SegmentEditorExtraEffects → restart.

**The generic Slicer logo still shows** — `Resources/` did not make it into the
install. Check that `Resources/Icons/SegQueue.png` sits beside `SegQueue.py` in
`.../Slicer 5.8.1/.../Extensions-<rev>/SegQueue/lib/Slicer-5.8/qt-scripted-modules/`,
and rebuild if not.

**An upload died halfway** — uploads are chunked and resumable; retry the submit.
The client asks the server how much it already has and continues from there.

## Version history

**0.2.0** — Bradensbay identity: module icon, panel wordmark with light/dark
variants, vector sources, and `iconurl` in the extension descriptor. `Resources/`
is now packaged by `build-extension.py`. No protocol or workflow changes.

**0.1.0** — Initial release.
