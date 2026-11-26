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
- **Submitted classes** (D53, 0.25.6): decided at export, not by the toggle. With
  work in any extended class, a *Complete* tick, or a case flagged for extended
  mode, the read is submitted with all 21 channels in label order
  (`labels.ALL_NAMES`), the empty ones empty; otherwise (every extended class empty
  or an untouched seed copy), as the four. Turning the toggle off only hides the
  classes; it never removes one.
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

### Reviewers see the case's note thread (0.24.1)

- Opening a submission for review now shows, in **Case notes**, the case's full
  note thread, including other annotators' and the auto screener's notes: the
  comments annotators sent with **Post**, which 0.24.0 left out (a reviewer holds
  no case of their own, so the thread stayed empty), and the system notes. It is
  fetched by the case, never filtered by the submission's annotator. It is
  read-only and looks exactly as it does to the annotator; *Annotator's note: ...*
  stays above it. It refreshes on the usual notes timer while the review is open.
  As everywhere, a long thread shows its newest 50 notes (`NOTE_PAGE_SIZE`).
- The posting row stays greyed out while reviewing: reviewers do not post notes.
- A thread that cannot be fetched is left empty, quietly; it never stops the review.
- Approving, saving a revision, *Return to pool*, comparing, viewing a case, opening
  your own case or logging out empties the thread again.
- Needs plugin **0.7.1** for reviewer accounts that are not also annotators (the
  server used to refuse them with `not_an_annotator`); until it is deployed those
  accounts see an empty thread. Protocol stays 21.

### No VPN advice in the connection error (0.25.7)

"Could not reach the server" now says to check the internet connection and tell the project lead, instead of telling annotators to connect a VPN that does not exist. Protocol stays 21, no server change.

### The extended-classes toggle never deletes work (0.25.6, D53)

Protocol stays 21, no server change. Annotators reported that turning **Extended
classes** off deleted their work on the extra classes, and that a *"Kept D1, D2, OM2
because you have changed them ..."* box confused them.

- **Off only hides.** The extended classes, their rows in the Segment Editor's list
  (`setHideSegments`) and the group rows under the toggle are hidden; an extended
  class selected for editing is deselected. No segment is removed, emptied,
  refilled or re-seeded. `removeEmptyExtendedClasses` and the info box are gone;
  the toggle raises no dialog.
- **On shows them as they were**, each with the eye it had
  (`SegQueue14Lib/extendedview.py`): a class or group hidden before stays hidden,
  and a group's *Show* tick is no longer reset by the toggle. Only missing classes
  are added (empty, D52); an existing one is never touched.
- **The export decides 4 or 21, never the toggle.** All 21 are sent (untouched seed
  copies blanked, D51 d; the *Complete* ticks in the header, D47 Q3) when an
  extended class holds work, when any branch group is ticked *Complete* (a ticked
  group with no branches is information), or when the case is flagged for extended
  mode (D47 Q6), whatever was drawn. Otherwise the read is the four classes exactly
  as before; an empty class or an untouched seed copy is not work.
- **Opening a read with extended work** (a draft, a reopened read, a reviewer's
  submission) shows its extended classes, whatever the login's toggle says (not
  saved to it), so nobody opens their own work hidden.
- Root causes, reproduced in Slicer 5.8.1 and 5.12.4: the toggle off removed every
  branch still an untouched seed copy; turned on again it came back **empty**, and
  was never given its seed copy again (D52 records it as selected), so the branch an
  annotator was about to trim was gone. The toggle also reset the group *Show*
  ticks without showing their classes, so a hidden group looked deleted. **On a
  reviewer's panel the toggle off removed all 17**, the annotator's work included: a
  submission loaded from its file has no reference geometry, Slicer refuses to read
  a class without one, and `_segmentHasContent` took the refusal for "empty".
  0.25.6 gives the loaded read the CT's geometry and reads the stored labelmap when
  Slicer refuses; a class that cannot be read counts as content, never empty. The info
  box came only from the toggle (submit never raised it); annotators met it when
  turning the box off just before submitting, as the panel's tooltip and the guide
  described toggling off as tidying the read.

### A seeded case opens with a fraction of the memory (0.25.5)

Performance only: what the annotator sees is unchanged. Protocol stays 21, no
server change.

On the annotator's own seeded case, D26 fills LM, LAD, LCx and RCA with a copy of
the vessel seed. Each copy used to be written through `slicer.util` against the CT
(`updateSegmentBinaryLabelmapFromArray`), which put it in a labelmap layer the size
of the whole CT: four full-CT layers for a seed a few hundred thousand voxels big.
Each copy is now written in place from the seed's own labelmap (`copySegmentInto`,
`SetBinaryLabelmapToSegment`, as 0.25.4 already does for a branch's first
selection), so its layer is the seed's extent.

- Every class still starts as a hidden, whole copy of the seed, each in a layer of
  its own (trimming one leaves the others); a resumed draft is never refilled.
- The export still writes each class whole on the CT grid (D39); the
  untouched-seed-copy test (D51 c, d), overlap, selection and 3D surfaces are as in
  0.25.4.
- Measured on Slicer 5.8.1, a 512 x 512 x 300 CT and a 188k-voxel seed
  (`tests/slicer_bench_extended14.py`, three runs each): the four copies' layers
  went from 4 x 78.6M to 4 x 11.9M voxels (all five layers, seed included:
  326.5M -> 59.7M); the open from 1.7 s to 0.7 s (2.8 s to 1.5 s with the classes
  shown in 3D); memory added by the open from +300 MB to +69 MB resident, and the
  open no longer raises the process's peak (1477 MB before; after, the bench's own
  set-up peak of 1234 MB is never exceeded). Turning the extended classes on with
  the classes shown in 3D went from 1.7 s to 0.2 s as a side effect.

### Materials start empty; selecting a class shows it; overlap everywhere (0.25.4, D52)

D52 (2026-11-25, amends D51, and amended the same day after a lag report). Four
changes, all in the module; protocol stays 21, no server change.

**Materials start empty.** Stent, calcified and non-calcified plaque are always
added empty, also on a seeded case. 0.25.0-0.25.3 started them as a hidden copy of
the seed (D51), which made them useless: paint inside the lumen changed nothing and
the class was submitted empty (D51 d), and paint outside it was submitted as the
whole tree plus the stroke. The 14 branch classes keep D51's start as a seed copy,
made on demand (below). The branches are `labels.PARENT` (the extended classes with
a parent vessel), not a list of names in the module.

- The case line on a seeded case says *stent and plaque start empty* when the
  extended classes are on.
- Turning the toggle off removes the empty classes (now including untouched
  materials) and the untouched branch seed copies, as before.
- Submit still blanks an extended class left exactly as the seed (D51 d). Only
  branches start that way now; the test stays on the materials too, so a material
  left as the seed by a 0.25.0-0.25.3 draft is never submitted as the whole tree.
  The message after submitting says *branch class*.
- Plaque painted inside the LAD on a seeded case is submitted as plaque, in its own
  channel overlapping the LAD's.

**Seed copies are made on demand** (lag report). Since D51, turning the extended
classes on lagged badly on a seeded case: 0.25.0-0.25.3 wrote 17 copies of the seed
at once, each re-imported through `slicer.util` over the whole CT into a labelmap
layer of its own the size of the CT, and then rebuilt every 3D surface. Now:

- Turning the toggle on adds the 17 empty: no seed voxels, no surface rebuilt.
- A branch becomes its copy of the seed when it is **first selected for editing**,
  in the same handler that shows a selected class: one class at a time. The copy is
  written in place from the seed's own labelmap (`copySegmentInto`,
  `SetBinaryLabelmapToSegment`), so its layer is the seed's size, not the CT's,
  and only that class's 3D surface is built, only if surfaces are showing; every
  other class keeps its own.
- *First* means once per read: the class is recorded in `seedFirstSelected` (in the
  draft's manifest) whether it was filled or already had voxels, so a class emptied
  on purpose is never refilled, also after a resumed draft. A draft from before
  0.25.4, or a reopened read, counts every branch already in it as selected.
- Materials never get a copy; a reviewer's classes never do (D51 b). A branch never
  selected stays empty and is sent empty. Toggle-off and the export treat untouched
  seed copies as before (D51 c, d). After toggle off and on, a branch already
  selected in the read comes back empty.
- Measured on Slicer 5.8.1, 512 x 512 x 300 CT, a 188k-voxel seed
  (`tests/slicer_bench_extended14.py`): toggle on went from 8.0 s (14.5 s with the
  classes shown in 3D), 22 layers and 2.75 GB peak memory to 0.003 s (1.8 s), 5
  layers and no change in memory; a branch's first selection takes about 0.5 s and
  adds one layer the size of the seed's extent.

**Selecting a class shows it** (`SegQueue14Lib/selection.py`). The class selected
for editing in the panel's Segment Editor is made visible: when it is clicked in the
segment list, and when the editor picks one as a case or submission is bound. So
Slicer's *"The selected segment is hidden. Would you like to make it visible?"* no
longer appears and no longer drops the first stroke. Own case and a reviewer's
editing alike. Only the selected class changes: every other class keeps its
visibility, and a seeded case's classes still start hidden (D26, D51). A class the
annotator hides again by its eye while it stays selected stays hidden until another
class is selected.

**Overlap allowed everywhere** (D39, D44). Reported on 0.25.2: overlapping classes could not be submitted, which an extended
read needs. Stent, calcified and non-calcified plaque (D44) sit inside LM, LAD,
LCx, RCA and their branches, and D39 saves every class whole, overlaps included.

- **What it was not.** Nothing in submit, the export or the server refuses or
  trims overlap: the class stack has one 0/1 channel per class, and the server
  stores it as sent (D38). The module's own Segment Editor was not it either: in a
  real Slicer 5.8.1 and 5.12.4 its "Modify other segments" stays at **Allow
  overlap** through opening a case, the extended toggle, every effect and a
  reviewer's submission, and Paint, Draw, Scissors (fill inside), Threshold, Draw
  tube, Islands, Logical operators (copy, add) and Inverse cut all put a plaque
  inside the LAD with every LAD voxel kept.
- **Root cause.** Slicer's own **Segment Editor module** edits the same case through
  a parameter node of its own, made with Slicer's default, **Overwrite all**. A
  plaque painted there (or thresholded, filled, drawn) took its voxels out of the
  LAD, so the overlap was gone before it reached a submission. The same default
  applied to any Segment Editor node made after a scene clear, which is what
  opening a submission for review does; the panel's node was only corrected
  because the module set it again straight after. Reproduced on 5.8.1 and 5.12.4
  (Threshold over the tree in the Segment Editor module left the LAD empty).
- **Fix** (`SegQueue14Lib/overlap.py`). The module registers a scene *default node*
  for the Segment Editor with Allow overlap (`SetOverwriteMode(OverwriteNone)`, still
  the current call in 5.12, with the mode looked up by name as the fallback), so
  every Segment Editor node made from then on starts there, the Segment Editor
  module's included, also after a scene clear. Each case or submission opened (own
  case, resumed draft, reopened or recalled read, a reviewer's submission) sets the
  panel's node and the Segment Editor module's node to Allow overlap again.
- **Your choice is kept.** Nothing watches the setting afterwards: pick another mode
  in the Masking panel and it stays until the next case opens.

**Tested:** `tests/test_segqueue14_overlap.py`, `tests/test_segqueue14_selection.py`
and the D51/D52 tests in `tests/test_segqueue14_module.py`; in Slicer, `run_d51`,
`run_extended` and `run_overlap` in `tests/slicer_selftest14.py`. `run_overlap`
covers every effect above (own case and reviewer), the Segment Editor module, a
scene clear and the export as two overlapping channels, and for D52 the materials
at 0 voxels and branches as the seed on a seeded case, plaque inside the LAD
submitted as plaque, and selecting a hidden class showing it (own case and
reviewer) with the first paint stroke landing and no question asked; and for the
on-demand seed copies, that toggle-on adds no seed voxels, that a first selection
(through the panel and the logic) fills exactly that class, once, and that it keeps
every other class's 3D surface. The server test of an
extended read checks the stored stent and plaque channels overlap LAD and RCA, each
whole.

### A clear message when the server refuses the upload's chunk size (0.25.3)

- Submitting a read over 768 KiB (an extended read, usually) failed with Girder's
  *Chunk is smaller than the minimum size. (HTTP 400)*. Girder refuses every upload
  piece but the last under its `core.upload_minimum_chunk_size` (5 MiB by default),
  and the module's pieces stay under janus's 1 MiB proxy limit (0.23.1), so no
  piece size could work. The fix is on the server: the deploy step `upload-chunks`
  sets that minimum to 0 on janus (filesystem assetstore; see
  [DEPLOY.md](../../server/girder_segqueue14/DEPLOY.md)).
- The module now shows that refusal as *The server refused the upload's chunk size (a
  server setting). Nothing has been submitted, and your work is still saved on this
  computer. Please tell the project lead.* As before, a failed submit keeps the
  local copy. The piece size (768 KiB, halved on HTTP 413 down to 64 KiB) is
  unchanged.
- Module only: protocol stays 21, the plugin's queue is unchanged.

### Inverse cut keeps the 3D view (0.25.2, D51)

After an Inverse cut the cut class disappeared from the 3D view (with every other
class) until **Show in 3D** was pressed again, which read as "it removes the whole
segment".

- **Root cause.** The effect wrote its result with Slicer's
  `slicer.util.updateSegmentBinaryLabelmapFromArray`. That re-imports the segment
  from a label volume, and Slicer 5.8 then drops the closed-surface representation
  of *every* segment in the segmentation: the voxels were right, but nothing was
  left for the 3D view to draw. Show in 3D rebuilt the surfaces, which is why it
  came back.
- **Fix.** The cut is now written the way Slicer's own effects (Scissors, Paint,
  Islands) write: through the editor's `modifySelectedSegmentByLabelmap` (Set, on
  the CT's grid). The labelmap is changed in place, so the 3D view is rebuilt from
  it at once, the cut class as cut and the other classes untouched. It is still
  one Ctrl+Z, still changes only the selected class whatever the editor's overwrite
  setting, and still refuses an outline that holds none of the class. An empty
  class that takes the seed inside the outline shows in 3D the same way.
- **Turning the extended classes on** mid-case wrote the seed copies the same way
  and blanked the 3D view too. When the classes were showing in 3D, their surfaces
  are now rebuilt after the copies are written (`SegQueue14Lib/surfaces.py`).
  Turning the toggle off only removes segments, which never lost the surfaces.
- The Slicer self-test now shows the classes in 3D before cutting, and checks that
  after a cut (in a slice view, in the 3D view, and into an empty class) the cut
  class still has a closed surface the shape of the cut, without Show in 3D; and
  that toggling the extended classes keeps every class in 3D.
  Module only: protocol stays 21, server unchanged.

### Inverse cut fixes (0.25.1, D51)

Inverse cut (D51) could wipe the whole selected class instead of keeping what was
outlined, and showed no icon cursor over the 3D view.

- **The outline lands where it is drawn.** In a slice view the effect read the
  mouse's event position as slice XY. That is only true outside a lightbox: in a
  lightbox pane the outline was mapped to another place, held none of the class,
  and the cut emptied it. The outline is now converted as Slicer's own Scissors
  converts it (`ConvertDeviceToXYZ`, the pane under the mouse), then extruded
  through every slice as before. The ordinary slice views and the 3D view were
  already mapped correctly, which the new self-test checks on an oblique CT at 1x
  and 2x display scaling, against VTK's own projection for the 3D view.
- **Fail-safe:** an outline that holds none of the selected class's voxels (or,
  for an empty class, none of the seed's) changes nothing and says so in the
  status bar. A cut never empties the class.
- **Cursor:** the effect's icon is the cursor over the 3D view as well as the
  slice views, as for Scissors. The icon is now Slicer-sized (21 x 21,
  transparent) like the editor's own effects; the 64-pixel grey square made a
  cursor three times the size of Scissors'.
- The Slicer self-test now drives the effect through a real Red slice view and 3D
  view with mouse events (and a lightbox on Slicer 5.8), instead of calling the
  cut directly with a stand-in view, which is why 0.25.0's CI was green.
  Module only: protocol stays 21, server unchanged.

### Inverse cut, and extended classes start from the seed (0.25.0, D51)

- **Inverse cut**, a new Segment Editor effect with its own icon beside Scissors in
  the embedded editor (registered when the module loads). Hold the left button and
  draw an outline in a slice view or the 3D view. On release the **selected
  segment keeps only its voxels inside the outline**, extruded through the volume
  along the view direction as Scissors does by default. If the selected segment is
  empty and the case has a vessel seed, it becomes the seed's voxels inside the
  outline instead. Other segments are untouched, the seed and the heart region
  can never be cut, and it is one step in the editor's undo. A Python effect
  (`SegQueue14Lib/SegmentEditorInverseCutEffect.py`) with the voxel arithmetic in
  `SegQueue14Lib/inversecut.py`, numpy only and tested by pytest; the icon is
  `Resources/Icons/InverseCut.png`.
- **Extended classes start from the seed** on the annotator's own seeded case:
  each class the toggle (or a case flagged for extended mode) adds is a hidden full
  copy of the seed, as D26 does for the four. A resumed draft's classes are never
  refilled, a seedless case still gets them empty, and classes a reviewer's panel
  adds to a four-class read stay empty (D51 b).
- **Toggle off** removes extended classes that are empty *or* still an untouched
  copy of the seed, voxel for voxel; a class the annotator changed stays (D51 c).
- **Submit:** an extended class that is still an untouched copy of the seed is
  written as an empty channel, so a seed copy is never taken for a read (D51 d).
  The four classes are submitted as they are (D26, D38), and the per-group
  *Complete* ticks are unchanged (D47 Q3). The panel says how many classes went
  empty this way. Module only: protocol stays 21, server unchanged.

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
