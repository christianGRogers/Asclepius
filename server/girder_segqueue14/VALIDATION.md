# SegQueue14 validation checklist (before go-live)

For the project lead, on one **test account** that is in `segqueue14-annotators` and
`segqueue14-reviewers` and nothing else new. Do DEPLOY.md steps 0-6 first. Nobody
else is added to the SegQueue14 groups until every box is ticked. Anything that
fails: switch SegQueue14 off (DEPLOY.md, *Rollback*), which leaves SegQueue as it was.

Note the case each step uses; the test reads can be discarded later (a reviewer
returns them to the pool, or the data is purged before go-live).

## A. The live SegQueue is unaffected

- [ ] Girder's log shows both `Loaded plugin "segqueue"` and `Loaded plugin "segqueue14"`.
- [ ] An ordinary annotator logs into the **SegQueue** module, gets a case, and sees
      the usual four segments; the live review panel and `GET /api/v1/segqueue/stats`
      show the same numbers as before the install.
- [ ] `segqueue-worker` is still running (`systemctl is-active segqueue-worker`).
- [ ] In Girder's web UI the `SegQueue` collection has no new items; there is a new
      `SegQueue14` collection with `prelabels/<version>/`.

## B. Population and order

- [ ] `segqueue14-populate --dry-run` (run again) reports `create 0`, `unchanged 1000`.
- [ ] `GET /api/v1/segqueue14/stats` (admin) -> `tiers`: `icx-trainval` 640 cases /
      704 reads wanted, `imagecas-unlabelled` 200 / 400, `icx-test` 160 / 176.
- [ ] Spot-check three cases in Mongo or `GET /api/v1/segqueue14/review/cases`: an
      ImageCAS-X train case has 1 read, an unlabelled case 2, and one blind duplicate
      has 2. A SegQueue14 case's `fileId` equals the live case's `fileId`.
- [ ] `segqueue14-prelabels status` -> `icx14-v1: 1000 case(s)`, `without a prelabel: 0`
      (or the expected few, each listed with a reason by the attach run).

## C. The module (test account, Slicer 5.8)

- [ ] SegQueue14 installs from the zip next to SegQueue; both appear under
      Segmentation and both open.
- [ ] Log in. The panel shows the instructions text and the 14 classes with colours
      and hints; LAD, LCx and RCA are marked required.
- [ ] **Get next case** gives an ImageCAS-X train/val case first (an `imagecas_NNNN`
      whose id is in ImageCAS-X's train or val list).
- [ ] The case opens with the prediction already in the 14 segments -- names and
      colours match the panel, the 3D view shows the tree, the case line says
      `prelabel icx14-v1 (N classes)`. The heart helper is there; there is no
      `~ coronary seed` segment.
- [ ] Edit something (rename a branch, erase a vein, paint a missed segment): the
      Segment Editor behaves as in SegQueue; *Save draft*, close Slicer, reopen and
      log in: the draft (not a fresh prelabel) comes back.
- [ ] Erase all of LCx and press **Submit case**: refused before upload, naming LCx.
      Undo, submit: accepted, local copy deleted.
- [ ] Old module: with a SegQueue14 zip built from an older protocol (or by running
      `python tests/segqueue14_e2e.py --url <server> --user <test account>`), login is
      refused with *"Update the SegQueue14 module"*.
- [ ] `python tests/segqueue14_e2e.py --url <server> --user <test account>` passes
      (it gives its case back; it submits nothing).

## D. Scoring and review

- [ ] Within a minute of the submit, the worker log shows it scored; as a reviewer in
      the SegQueue14 panel the case's history row has a Dice, and its tooltip lists
      the 14 per-class Dice values and the prelabel version.
- [ ] Submit one deliberately poor read (e.g. RCA relabelled as R-PDA): it lands in
      the review queue flagged `RCA Dice ... against ImageCAS-X`.
      **Show ImageCAS-X reference** loads the reference as outlines for comparison.
- [ ] A good read with the sampling roll not selecting it is approved without a
      reviewer (after the annotator's first five, which are always reviewed).
- [ ] Two test accounts each take the same unlabelled (two-read) case: the first read
      waits, and is decided with the second; both carry a pair Dice.
- [ ] The thresholds feel right on these reads; if not, set `segqueue14.reference`
      (DEPLOY.md step 5) before go-live.

## E. Export round trip

- [ ] `segqueue14-export --out /tmp/sq14-export` writes, per approved case,
      `ct.nii.gz` and 14 masks named `LM.nii.gz ... Other.nii.gz`, and a manifest
      whose `source.prelabel_versions` names icx14-v1.
- [ ] `segtrain convert` with the `coronary_icx14` label set converts it, and the
      label volume has values 0-14 where the read had them
      (`tests/test_segqueue14_convert.py` does exactly this on synthetic reads; a
      14-class *training task* config is a training decision and not on this branch).

## F. Rollback rehearsal (optional, recommended)

- [ ] Set `SEGQUEUE14_DISABLE=1`, restart: `/api/v1/segqueue14/project` is 404 and
      SegQueue works. Remove it, restart: SegQueue14 is back with its data.

## Decisions to confirm while doing this

- [ ] The reference thresholds (`mean_dice_flag` 0.60, `required_dice_flag` 0.70,
      `duplicate_mean_dice_flag` 0.60) -- placeholders until real reads are seen.
- [ ] Where new datasets sit in the order (default: after the 200 unlabelled
      ImageCAS cases, before the 160 test cases).
- [ ] Whether the first five reads of every annotator should be reviewed (the live
      training gate, kept by default) now that every ImageCAS-X read is scored.
