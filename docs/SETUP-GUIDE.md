# SegQueue setup guide (full reference)

This is the complete reference for installing and running SegQueue. New annotators
should start with the shorter [annotator setup guide](ANNOTATOR-SETUP.md), which gives
one recommended path per operating system. This page covers every route and the
reasons behind them.

It takes you from a blank computer to submitting your first case. It covers
Windows and Mac. Allow about 30 minutes, most of it waiting for downloads.

If anything here does not match what you see on screen, tell the project lead.
Include your operating system, your Slicer version and a screenshot of the problem.

## 1. What you need

- A Windows or Mac computer with about 10 GB of free disk space and an internet
  connection. A mouse with a scroll wheel makes segmentation much easier.
- Your SegQueue username and password from the project lead. Your account must be
  in the `segqueue14-annotators` group; the lead sets that up.
- The server address: `https://janus.bradensbay.com`

You do not need admin rights, Python, or any build tools.

## 2. Install 3D Slicer

SegQueue runs inside 3D Slicer, a free medical imaging program.

**Which version:** install **Slicer 5.8.1**. It is the version the team tests
against. Newer versions also work (see the note in step 4), but 5.8.1 is the one
to pick if you have no reason to choose another.

Go to https://download.slicer.org, open the **older releases** page, and download
5.8.1 for your operating system.

### Windows

1. Run the downloaded installer and accept the defaults.
2. If Windows shows a blue "Windows protected your PC" box, click **More info**,
   then **Run anyway**. That message appears for any program Microsoft has not seen
   many times before.
3. Start Slicer once from the Start menu to confirm it opens. The first start takes
   a minute.

### Mac

1. Open the downloaded `.dmg` file and drag **Slicer** into **Applications**.
2. Start Slicer from Applications. If macOS says the app cannot be opened because
   it is from an unidentified developer, right-click the app, choose **Open**, and
   confirm. You only need to do that once.
3. On a Mac with an Apple chip (M1, M2, M3 and so on), macOS may offer to install
   **Rosetta** the first time. Accept it. Slicer then runs through Rosetta, which is
   fine for annotation work.

## 3. Install the Draw tube tool

SegQueue needs one extra Slicer extension, **SegmentEditorExtraEffects**, which
provides the Draw tube tool.

1. In Slicer, open **View > Extensions Manager**.
2. Search for **SegmentEditorExtraEffects** and click **Install**.
3. Restart Slicer when asked.

Do this before installing SegQueue. SegQueue checks for it at startup and tells you
if it is missing.

## 4. Install SegQueue

Download the newest release from
https://github.com/christianGRogers/Asclepius/releases. The release page lists the
files you need. Then follow one of the two routes below.

### Route A: the module folder (works on any Slicer version, Windows and Mac)

This is the route to use unless you are on Slicer 5.8.0 or 5.8.1 and prefer the
Extensions Manager.

1. Download `SegQueue-<version>-Slicer-5.8.zip` (the one **without** `-macOS` in
   the name) and unzip it. On a Mac, Safari usually unzips it for you. You get a
   folder named `SegQueue`.
2. Move that folder somewhere you will keep it, for example your home folder or
   Documents. Do not leave it in Downloads.
3. In Slicer, open **Edit > Application Settings**, then the **Modules** section.
4. Next to **Additional module paths**, click **Add** and pick this folder inside
   the one you unzipped:
   `SegQueue/lib/Slicer-5.8/qt-scripted-modules`
5. Click **OK** and restart Slicer.
6. SegQueue is now under **Segmentation > SegQueue** in the module list.

If you later install a different Slicer version, repeat steps 3 to 5 in it. Each
Slicer keeps its own settings.

### Route B: Install from file (Slicer 5.8.0 and 5.8.1 only)

1. Download the zip for your system from the release page:
   - **Windows:** `SegQueue-<version>-Slicer-5.8.zip`
   - **Mac:** `SegQueue-<version>-Slicer-5.8-macOS.zip`
2. Keep it as a zip. On a Mac, Safari may unzip it on its own. If you end up with a
   folder instead of a zip, either use Route A with that folder, or download the
   file again by right-clicking the link and choosing **Download Linked File**.
3. In Slicer, open **View > Extensions Manager**, click **Install from file**, pick
   the zip, and restart Slicer.

This route only works on Slicer 5.8.0 and 5.8.1. On any other version it fails with
"Failed to copy directory". If you see that message, use Route A.

Use one route, not both. Two copies of the module in one Slicer cause confusing
errors.

## 5. Log in

1. In Slicer, open **Segmentation > SegQueue**.
2. In the **Server** box, make sure the address is exactly
   `https://janus.bradensbay.com`. Older versions of the module show a placeholder
   address ending in `example.edu`; replace it. Slicer remembers the address after
   that.
3. Type your username and password and click **Log in**.

If login fails with "Update the SegQueue14 module", click **Check for updates**
and then **Update and restart**. If it fails with "Could not reach the server",
check your internet connection and the server address.

## 6. Annotate a case

1. Click **Get next case**. The CT loads together with a yellow **vessel seed**, an
   automatic rough outline of the coronary tree.
2. There are four classes to fill in:

   | Class | Vessel | Required |
   |---|---|---|
   | 1 LM | Left main | Optional |
   | 2 LAD | Left anterior descending | Yes |
   | 3 LCx | Left circumflex | Yes |
   | 4 RCA | Right coronary artery | Yes |

   Each class starts as a full, hidden copy of the seed. Your job is to cut each
   copy down to its own vessel.
3. In the Segment Editor, show one class at a time with the eye icon in the segment
   list, and erase everything that is not that vessel. Add vessel the seed missed,
   delete anything that is not a coronary artery, and trim the outline to the
   contrast-filled lumen.
4. Side branches take the class of the vessel they come off. Diagonals and septals
   are LAD. Obtuse marginals are LCx. A ramus intermedius is always LCx. A PDA or
   posterolateral branch belongs to whichever artery it arises from.
5. Click **Submit case**. Nothing checks what you drew before it is sent (project
   lead, 2026-11-02): an empty LAD, LCx or RCA no longer blocks the
   submit, so check each class yourself first.
6. Optional: the **Extended classes** below add named branches and plaque/stent
   classes on top of the four.

Other buttons you will see:

- **Save draft** keeps your work on this computer so you can continue later.
- **Give this case back** returns the case to the pool if you cannot finish it.
- **Check for updates** fetches a newer version of the module.

The seed and the heart mask are helpers. They never leave your computer, and the
local copy of a case is deleted once the server confirms your submission.

### Extended classes (optional, 0.18.0)

The **Extended classes (optional)** box above the Segment Editor is off by default
and remembered per login. With it off, a case is the four classes above and
nothing else changes. Turned on, it adds 17 empty classes, grouped under their
parent vessel in the segment list:

| Group | Classes | Counts towards |
|---|---|---|
| LAD branches | D1, D2, D3 (diagonals); S1, S2, S3 (septals) | LAD |
| LCx branches | OM1, OM2 (obtuse marginals) | LCx |
| Other | Ramus (ramus intermedius) | LCx |
| RCA branches | Conus, RMA (right marginal) | RCA |
| RCA branches | SN (sinus node), PDA, PLB | the vessel each leaves: RCA or LCx (D47) |
| Materials | Stent, Calcified plaque, Non-calcified plaque | none (scored on its own) |

Any of them may stay empty. To use a branch class, move that branch out of
whichever vessel it leaves into its class (SN, PDA and PLB out of the RCA or the
LCx). Trace septals, SN, conus and RMA as far as they are visible, even where the
seed stops. The **Complete** ticks, one per branch group, say "I looked for every
branch here, so an empty class means absent"; they are optional. A case flagged
for extended mode opens with the box on and a note asking you to use it. Paint stent and plaque where you see them; overlapping a
vessel is fine, and every class is saved whole. The tooltip on each group says
what goes in each class, and the **Show** ticks hide or show a group. Turning the
box off removes only the extended classes that are empty. When a read is scored,
each branch is counted as part of the vessel it leaves, so a read that uses the
branch classes is compared like a four-class read.

## 7. Updating

The module checks for a newer version each time you open it and offers **Update
and restart**. One click does the whole update; you never need to download a file
again. This works for both install routes from version 0.16.4 onward.

## 8. Troubleshooting

| What you see | What it means | What to do |
|---|---|---|
| "Failed to copy directory" when installing | Install from file only works on Slicer 5.8.0 and 5.8.1 | Use Route A, or install Slicer 5.8.1 |
| The Server box shows an address ending in `example.edu` | An older module version with a placeholder default | Replace it with `https://janus.bradensbay.com` |
| Safari turned the zip into a folder | Safari unzips downloads by default | Use Route A with that folder, or right-click the link and choose Download Linked File |
| "Update the SegQueue14 module" at login | Your module is older than the server expects | Click Check for updates, then Update and restart |
| "Could not reach the server" | No connection, or a typo in the address | Check your internet and the Server box |
| SegQueue says Draw tube is missing | SegmentEditorExtraEffects is not installed | Install it from the Extensions Manager (step 3) |
| SegQueue is not in the module list after Route A | The wrong folder was added, or Slicer was not restarted | Check that the path ends in `qt-scripted-modules`, then restart |

## 9. Getting help

Tell the project lead. Include:

- your operating system and whether your Mac has an Apple chip or an Intel chip,
- your Slicer version (**Help > About 3D Slicer**),
- your SegQueue version (shown at the top of the SegQueue panel),
- a screenshot of the error, and the text from **View > Python Console** if there is
  any.
