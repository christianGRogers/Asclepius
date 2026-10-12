# Deploying SegQueue14 beside the live SegQueue

SegQueue14 is a second Girder plugin. It runs in the **same** Girder as the live
SegQueue, on the same database, and shares nothing writable with it:

| | live SegQueue | SegQueue14 |
|---|---|---|
| Python distribution | `girder-segqueue` (`server/`) | `girder-segqueue14` (`server/girder_segqueue14/`) |
| Girder plugin name | `segqueue` | `segqueue14` |
| REST prefix | `/api/v1/segqueue` | `/api/v1/segqueue14` |
| Girder collection | `SegQueue` | `SegQueue14` (prelabels, submissions, incoming) |
| Mongo collections | `segqueue_case`, `segqueue_assignment`, ... | `segqueue14_case`, `segqueue14_assignment`, ... |
| Settings | `segqueue.policy`, `segqueue.project` | `segqueue14.policy`, `segqueue14.project`, `segqueue14.reference` |
| Groups | `segqueue-annotators`, `segqueue-reviewers` | `segqueue14-annotators`, `segqueue14-reviewers` |
| User quota field | `segqueueQuota` | `segqueue14Quota` |
| Worker | `segqueue-score` | `segqueue14-score` |
| Slicer module | SegQueue | SegQueue14 |

What SegQueue14 **reads** from the live project, and never writes, moves or
deletes: the `segqueue_case` documents (once, when populating), and the files in the
`SegQueue` collection -- the CT volumes and heart masks the live cases point at, and
the ImageCAS-X items in `SegQueue/imagecas-x`. SegQueue14 cases store those file ids;
the ~110 GB of CT is not copied.

A SegQueue14 load failure is logged, not raised, so a broken SegQueue14 install cannot
stop Girder (and with it SegQueue) from starting.

The commands below are for janus.bradensbay.com, which runs natively
(`~/Asclepius/.venv`, systemd units from `deploy/systemd/`, `GIRDER_MONGO_URI` =
`mongodb://127.0.0.1:27017/girder`). Every command is run on the server as the user
that owns the checkout.

---

## 0. Before anything: a backup

```sh
mongodump --uri mongodb://127.0.0.1:27017/girder --archive=$HOME/segqueue-data/pre-sq14.archive.gz --gzip
```

(Or `deploy/backup.sh` if restic is set up.) SegQueue14 does not touch live data, but
this is the one moment where a restore point costs nothing.

## 1. Install the code

The code is on the branch `claude/segqueue14`. It only adds files, plus one line in
`server/pyproject.toml` that makes the live distribution's package list exact (so it
cannot sweep up `girder_segqueue14`; the live wheel's contents are unchanged). Merge
it into `main` after review, then:

```sh
cd ~/Asclepius && git fetch origin && git checkout main && git pull
.venv/bin/python -m pip install .                                   # segqueue + segqueue14 (src/)
.venv/bin/python -m pip install "./server[scoring]"                 # the live plugin, as before
.venv/bin/python -m pip install "./server/girder_segqueue14[scoring]" # the new plugin
.venv/bin/python -c "import girder_segqueue14, segqueue14; print('segqueue14 protocol', segqueue14.PROTOCOL_VERSION)"
```

Girder 5 loads every installed plugin; there is no enable step. To install now but
keep `/segqueue14` switched off until you are ready, add
`Environment=SEGQUEUE14_DISABLE=1` to the girder unit
(`sudo systemctl edit segqueue-girder`) before restarting.

Restart Girder and check both plugins loaded:

```sh
sudo systemctl restart segqueue-girder          # or: bash ~/segqueue-data/segqueue.sh restart
journalctl -u segqueue-girder --since -2min | grep 'Loaded plugin'
#   Loaded plugin "segqueue"
#   Loaded plugin "segqueue14"
curl -s -o /dev/null -w '%{http_code}\n' localhost:8080/api/v1/segqueue14/project   # 401 (needs login), not 404
curl -s -o /dev/null -w '%{http_code}\n' localhost:8080/api/v1/segqueue/project     # 401, as before
```

## 2. Groups and people

The two groups are created when the plugin loads (an admin account must exist, which
it does). Check in the Girder web UI under **Groups**: `segqueue14-annotators`,
`segqueue14-reviewers`. Being in the live groups grants nothing here.

* Existing accounts: **Groups → segqueue14-annotators → Add member** (and
  `segqueue14-reviewers` for reviewers), or as an admin:
  `PATCH /api/v1/segqueue14/users/{userId}?annotator=true&reviewer=true`.
* New accounts: `POST /api/v1/segqueue14/users` (login, email, names, password,
  optional `reviewer`, `quota`), which creates the user and adds them to the group.
* Start with **one test account** in both groups for VALIDATION.md, nobody else.

## 3. Populate the cases

```sh
export GIRDER_MONGO_URI=mongodb://127.0.0.1:27017/girder
cd ~/Asclepius
.venv/bin/segqueue14-populate --dry-run
```

Read the summary before going on. It should say about:

```
ImageCAS-X references: 800; splits: 1000 ids from <source>
would create 1000, ... blind duplicates 80.
  icx-trainval           p400  640 cases, 704 reads
  imagecas-unlabelled    p300  200 cases, 400 reads
  icx-test               p100  160 cases, 176 reads
```

* `splits: none found` -> the ImageCAS-X file lists are not in Girder in a form the
  tool recognises (file-list items `train.txt`/`val.txt`/`test.txt`/`exclude.txt`
  anywhere under `SegQueue/imagecas-x`, `splits` metadata on that folder, or a `split`
  key on each segmentation item). Point it at a local copy instead:
  `--splits-dir /path/to/ImageCAS-X/filelist`. It refuses to populate without splits,
  because the test cases would not then be last (D16).
* `- imagecas_NNNN: ...skipped` lines name every case left out and why (no reference
  for a listed case, a reference without a split, retired in the live SegQueue).
* Options: `--duplicate-fraction 0.10` (D11), `--priority-trainval 400`,
  `--priority-unlabelled 300`, `--priority-new 200`, `--priority-test 100`,
  `--icx-folder <id>` if ImageCAS-X is not at `SegQueue/imagecas-x`.

Then for real (idempotent; a re-run creates only what is missing):

```sh
.venv/bin/segqueue14-populate
```

## 4. Attach the prelabels

Copy the 14-class model's predictions to the server (`trillium/icx14`: they are
`$SCRATCH/icx14/predictions/c0000.nii.gz ... c0999.nii.gz`, uint8 on each CT's grid),
e.g. into `~/segqueue-data/prelabels/icx14-v1/`. `cNNNN` names map to `imagecas_{N+1}`
automatically; files named `imagecas_NNNN.nii.gz` work too.

```sh
.venv/bin/segqueue14-prelabels attach --dir ~/segqueue-data/prelabels/icx14-v1 \
    --model-version icx14-v1 --verify-grid --dry-run
.venv/bin/segqueue14-prelabels attach --dir ~/segqueue-data/prelabels/icx14-v1 \
    --model-version icx14-v1 --verify-grid
.venv/bin/segqueue14-prelabels status
```

`--verify-grid` compares each prelabel's header with its CT's (a few KB read per CT).
Files go to `SegQueue14/prelabels/icx14-v1/<case>.prelabel.nii.gz`; the version is
recorded on the case and copied onto each assignment and submission. A single case
can also be attached over REST (`POST /api/v1/segqueue14/prelabels/attach`, admin).

**The D15 refresh, later** (after ~300 corrected cases and a fine-tune): the same
command with the new directory and a new `--model-version`. It refreshes only cases
nobody has submitted or has open in Slicer, and never the 160 ImageCAS-X test cases
(D16) unless `--include-test` is given. Run it with `--dry-run` first; every case it
leaves alone is listed with the reason. Old prelabels are kept (`prelabelHistory`).

## 5. Start the SegQueue14 worker

```sh
sudo cp server/girder_segqueue14/segqueue14-worker.service /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now segqueue14-worker
journalctl -u segqueue14-worker -f
```

Without systemd: `setsid nohup .venv/bin/segqueue14-score --poll 30 --sweep 3600 >>
~/segqueue-data/logs/worker14.log 2>&1 < /dev/null &`. (`segqueue.sh`'s
`pkill -f segqueue-score` does not match `segqueue14-score`, and vice versa.)

The worker scores every read of an ImageCAS-X case against ImageCAS-X (Dice, HD95 and
presence for each of the 14 classes) and every two-read pair against each other, and
sends a read to review when it falls below `segqueue14.reference`:

```json
{"mean_dice_flag": 0.60, "required_dice_flag": 0.70, "class_dice_flags": {}, "duplicate_mean_dice_flag": 0.60}
```

Change it as an admin with
`PUT /api/v1/system/setting?key=segqueue14.reference&value=<json>`
(the same way for `segqueue14.policy`: review sampling, lease, concurrency).

## 6. The Slicer module

```sh
python slicer/build-extension14.py      # -> dist/SegQueue14-0.1.0-Slicer-5.8.zip
```

Give the zip to the test account only. Slicer -> Extensions Manager -> Install from
file -> restart; the module is **Segmentation -> SegQueue14**, beside SegQueue.

Now follow `VALIDATION.md`. Nobody else is added to `segqueue14-annotators` until it
passes.

## Adding another dataset (D17)

Upload the new CTs into a Girder folder (one item per volume, NIfTI/NRRD; oblique
volumes should be geometry-corrected first, as `segqueue-ingest` does for the live
project, or Slicer cannot open them), then:

```sh
.venv/bin/segqueue14-populate --skip-imagecas --extra-folder <folderId> --dataset <tag> --dry-run
.venv/bin/segqueue14-populate --skip-imagecas --extra-folder <folderId> --dataset <tag>
```

Each item becomes `<tag>_<item>`, two reads, priority 200 (after the 200 unlabelled
ImageCAS cases, before the held-out test cases), its CT referenced in place and hashed
once. Prelabels for them are attached with `segqueue14-prelabels`, named
`<tag>_<item>.nii.gz`.

---

## Rollback

Nothing below touches the live SegQueue: SegQueue14 never wrote to `segqueue_*`, the
`SegQueue` collection, the live groups or `segqueue.*` settings.

**Switch it off (seconds, reversible):**

```sh
sudo systemctl stop segqueue14-worker
sudo systemctl edit segqueue-girder     # add: [Service]  Environment=SEGQUEUE14_DISABLE=1
sudo systemctl restart segqueue-girder
```

`/segqueue14` returns 404; all SegQueue14 data stays where it is.

**Uninstall:**

```sh
sudo systemctl disable --now segqueue14-worker && sudo rm /etc/systemd/system/segqueue14-worker.service
~/Asclepius/.venv/bin/python -m pip uninstall -y girder-segqueue14
sudo systemctl daemon-reload && sudo systemctl restart segqueue-girder
journalctl -u segqueue-girder --since -2min | grep 'Loaded plugin'   # only "segqueue"
```

The `segqueue14` package left inside the root install is inert (nothing imports it);
reinstall the root package from the previous commit to remove it too.

**Purge the data (irreversible, optional):** only after an uninstall, and only if the
project lead decides SegQueue14's reads are not wanted. The CT volumes are in the
`SegQueue` collection and are **not** affected -- never delete that collection.

```sh
mongosh mongodb://127.0.0.1:27017/girder --eval '
  ["segqueue14_case","segqueue14_assignment","segqueue14_submission","segqueue14_review","segqueue14_note"]
    .forEach(c => db.getCollection(c).drop());
  db.setting.deleteMany({key: /^segqueue14\./});
  db.user.updateMany({}, {$unset: {segqueue14Quota: ""}});'
```

then delete the `SegQueue14` collection and the two `segqueue14-*` groups in the
Girder web UI (Collections / Groups). That removes prelabels and SegQueue14
submissions from the assetstore; nothing else.

## Things to know

* If a live CT is ever deleted or re-ingested under a new file id, the SegQueue14 case
  that points at it fails to download (`case_file_missing`). Re-run
  `segqueue14-populate --update` after a live re-ingest.
* Packaged (Docker) deployments: the stock image installs only `./server[scoring]`.
  Going live there means adding `&& pip install "./server/girder_segqueue14[scoring]"`
  to `deploy/Dockerfile` and a `worker14` service running `segqueue14-score`; neither
  is done on this branch, so the live image is unchanged.
