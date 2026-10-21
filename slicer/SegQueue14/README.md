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

   \* required: the case cannot be submitted while LAD, LCx or RCA is empty. LM is
   optional (some patients have separate LAD and LCx ostia).
3. **Cut each class down** in the Segment Editor: show one class at a time (the eye
   in the segment list) and erase everything that is not that vessel. A case cannot
   be submitted while any voxel is in two classes, so an untrimmed copy is caught.
   Every side branch takes the class of the vessel it comes off (D1): diagonals and
   septals are LAD; obtuse marginals are LCx; a PDA or posterolateral branch is the
   class of the artery it arises from. A ramus intermedius is always LCx (D1b). Add
   vessel the seed missed, delete anything that is not a coronary artery, and trim or
   extend the outline to the contrast-filled lumen.
4. **Submit case.** What is in the four segments is what is submitted. The seed and
   the heart mask are helpers and never leave your machine.

## Install

**Running SegQueue 0.13 or older:** open SegQueue and press *Check for updates* →
**Update and restart**. It installs SegQueue14 over it; afterwards open
**Segmentation → SegQueue14** (opening "SegQueue" takes you there). Your server
address carries over. If you installed the separate SegQueue14 0.1.0 extension,
uninstall it first.

**First install:** download `SegQueue-<version>-Slicer-5.8.zip` from the newest
`segqueue-v…` release (or build it: `python slicer/build-extension14.py`), then
**Extensions Manager → Install from file** → restart. **On a Mac, use
`SegQueue-<version>-Slicer-5.8-macOS.zip`**: macOS Slicer only installs from the
`Slicer.app/Contents/Extensions-<revision>/` path inside a zip, so the plain zip
fails there with "Failed to copy directory" (#94). Slicer 5.8.0 and 5.8.1 are
covered; another revision needs adding to `MACOS_REVISIONS` in
`slicer/build-extension14.py`. From a checkout: add
`slicer/SegQueue14` to *Additional module paths*.

**Updating:** the module checks for a newer release when opened and offers
**Update and restart** (`SegQueue14Lib/updater.py`, which only installs archives
that carry SegQueue14). If the server's protocol has moved on, login is refused
with *"Update the SegQueue14 module"*.

## For developers

`SegQueue14Lib/` (client, cache) has no Slicer imports and is tested by
`tests/test_segqueue14_client.py`; the module itself is checked statically by
`tests/test_segqueue14_module.py`. `tests/segqueue14_e2e.py` runs the module's
network path against a live server.
