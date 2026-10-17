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
- [ ] In Girder's web UI the `SegQueue` collection has no new items (SegQueue14 only
      reads `SegQueue/cases` and `SegQueue/seeds-totalseg`); there is a new
      `SegQueue14` collection.

## B. Population and order

The queue is the 675 pooled volumes only (D23): no ImageCAS case of any kind.

- [ ] `segqueue14-populate --pool-list configs/segqueue14/pool-2026-10.txt --dry-run`
      (run again) reports `would create 0` and `not found 0`; every case it lists
      is a `<Source>__<Case>` name from the pool list.
- [ ] `GET /api/v1/segqueue14/stats` (admin) -> one tier, `new-dataset`, with as many
      cases as were created and two reads each; no `imagecas_NNNN` case exists.
- [ ] Spot-check three cases (`GET /api/v1/segqueue14/review/cases`): `fileId` is the
      item's file in `SegQueue/cases`, `seedFileId` the matching
      `__totalseg-coronary` file in `SegQueue/seeds-totalseg`, `dataset` its source.

## C. The module (test account, Slicer 5.8)

- [ ] From SegQueue 0.13, *Check for updates* offers 0.14.0 and **Update and
      restart** installs it; after the restart *Segmentation -> SegQueue14* opens,
      and opening "SegQueue" forwards to it.
- [ ] Log in. The panel shows the instructions text and the 14 classes with colours
      and hints; LAD, LCx and RCA are marked required.
- [ ] **Get next case** gives the first volume of the pool list
      (`Figshare-23057000__PA0` unless it was left out).
- [ ] The case opens with the yellow `~ vessel seed (not submitted)` segment over the
      vessels (faint in 3D) and the 14 class segments empty; the case line says
      `vessel seed: divide it into the classes`.
- [ ] Divide part of it: Segment Editor -> *Islands* -> *Keep selected island* on a copy,
      or *Logical operators* -> *Add* the seed into a class and erase what is not
      that class. It is quick enough to be the way annotators work (if not, say so
      before go-live).
- [ ] *Save draft*, close Slicer, reopen and log in: the draft and the seed come back.
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
- [ ] The seed segment is not in the submission (the reviewer sees 14 classes only).
- [ ] Two test accounts each take the same (two-read) case: the first read waits, and
      is decided with the second; both carry a pair Dice. There is no ImageCAS-X
      reference score on pool cases -- the pair Dice and review are the check.
- [ ] A reviewer opening the case sees the seed too (`case_seed`), for comparison.
- [ ] The thresholds feel right on these reads; if not, set `segqueue14.reference`
      (DEPLOY.md step 5) before go-live.

## E. Export round trip

- [ ] `segqueue14-export --out /tmp/sq14-export` writes, per approved case,
      `ct.nii.gz` and 14 masks named `LM.nii.gz ... Other.nii.gz`, and a manifest;
      each case folder is named after its `<Source>__<Case>`.
- [ ] `segtrain convert` with the `coronary_icx14` label set converts it, and the
      label volume has values 0-14 where the read had them
      (`tests/test_segqueue14_convert.py` does exactly this on synthetic reads; a
      14-class *training task* config is a training decision and not on this branch).

## F. Rollback rehearsal (optional, recommended)

- [ ] Set `SEGQUEUE14_DISABLE=1`, restart: `/api/v1/segqueue14/project` is 404 and
      SegQueue works. Remove it, restart: SegQueue14 is back with its data.

## Decisions to confirm while doing this

- [ ] The pair threshold (`duplicate_mean_dice_flag` 0.60) -- a placeholder until real
      reads are seen.
- [ ] Two reads per pool case (D11 for unlabelled cases) or one, to get through the
      675 faster (`--pool-replicas 1 --update`).
- [ ] Whether the first five reads of every annotator should be reviewed (the live
      training gate, kept by default) -- with no reference score on pool cases this
      is the main early check.
