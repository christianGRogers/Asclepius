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

What SegQueue14 **reads**, and never writes, moves or deletes: the files in the
`SegQueue` collection -- the pooled CT volumes in `SegQueue/cases` and their seeds in
`SegQueue/seeds-totalseg` (D22, D23). SegQueue14 cases store those file ids; no CT is
copied. (The ImageCAS mode of `segqueue14-populate` would also read the live
`segqueue_case` documents; the D23 plan does not use it.)

A SegQueue14 load failure is logged, not raised, so a broken SegQueue14 install cannot
stop Girder (and with it SegQueue) from starting.

The commands below are for janus.bradensbay.com, which runs natively
(`~/Asclepius/.venv`, systemd units from `deploy/systemd/`, `GIRDER_MONGO_URI` =
`mongodb://127.0.0.1:27017/girder`). Every command is run on the server as the user
that owns the checkout.

---

## Quick path: `deploy/segqueue14-deploy.sh`

Steps 0, 1, 3 and 5 below as one script. **From GitHub:** Actions -> *SegQueue14 on
janus* -> *Run workflow*, pick the step; it SSHes in with the `SSH_*` secrets, updates
`~/Asclepius-sq14` to `main` and runs the step as root for the deploy user (output in
the run summary). **On the server by hand**, from any directory:

```sh
git clone -q --branch main "$(git -C ~/Asclepius remote get-url origin)" ~/Asclepius-sq14
D=~/Asclepius-sq14/deploy/segqueue14-deploy.sh
bash $D install            # backup, install, restart Girder, check both plugins
bash $D populate           # dry run of the pool
bash $D populate --apply   # create the pool cases that have a seed
bash $D worker             # SegQueue14 scoring worker
bash $D status             # counts; `off` is the rollback switch
```

It never checks anything out in `~/Asclepius` and never reinstalls the live plugin:
`main` is cloned into `~/Asclepius-sq14`, and only the repository root (the shared
`segqueue`/`segqueue14` packages, `--no-deps`) and `girder-segqueue14` are installed
into the live venv. The steps below are what it does, for doing it by hand.

## 0. Before anything: a backup

```sh
mongodump --uri mongodb://127.0.0.1:27017/girder --archive=$HOME/segqueue-data/pre-sq14.archive.gz --gzip
```

(Or `deploy/backup.sh` if restic is set up.) SegQueue14 does not touch live data, but
this is the one moment where a restore point costs nothing.

## 1. Install the code

From a separate clone of `main`, so the live checkout and the live plugin stay as they
are (reinstalling `./server` is the live plugin's own release step, not this one's):

```sh
git clone --branch main "$(git -C ~/Asclepius remote get-url origin)" ~/Asclepius-sq14
~/Asclepius/.venv/bin/python -m pip install --no-deps ~/Asclepius-sq14                       # segqueue + segqueue14 (src/)
~/Asclepius/.venv/bin/python -m pip install "$HOME/Asclepius-sq14/server/girder_segqueue14[scoring]" # the new plugin
~/Asclepius/.venv/bin/python -c "import girder_segqueue14, segqueue14; print('segqueue14 protocol', segqueue14.PROTOCOL_VERSION)"
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

## 3. Populate the cases: the 675 pooled volumes (D23)

The queue is **only** the 2026-10 pool: the 675 new volumes in `SegQueue/cases` listed
in `configs/segqueue14/pool-2026-10.txt` (QC "annotatable" first, then "limited", then
the three sets with suspect header spacing). None of the ImageCAS cases are queued --
the 800 ImageCAS-X cases are already labelled and live in their own `ImageCAS-X`
collection (D22). Each case ships its binary TotalSegmentator vessel mask from
`SegQueue/seeds-totalseg` as a guide the annotator divides into the 14 classes; it is
a helper segment and is never submitted. Two reads per case (D11, unlabelled).

```sh
export GIRDER_MONGO_URI=mongodb://127.0.0.1:27017/girder
cd ~/Asclepius
.venv/bin/segqueue14-populate --pool-list ~/Asclepius-sq14/configs/segqueue14/pool-2026-10.txt --require-seed --dry-run
```

It should say `pool: 675 listed, ... items in cases, N seeds in seeds-totalseg`, then
`would create N` with `not found 0` and one line per dataset. `--require-seed` leaves
out the volumes whose seed is not uploaded yet (the CPU batch is still producing them,
in the same order as the list), so nobody is served a case without one. Then for real
(it hashes each CT once, so it takes a while):

```sh
.venv/bin/segqueue14-populate --pool-list ~/Asclepius-sq14/configs/segqueue14/pool-2026-10.txt --require-seed
```

**Re-run the same command** whenever more seeds have landed (e.g. daily until the batch
is done): it adds the newly seeded volumes in their list positions and changes nothing
else. Without `--require-seed` every volume is created at once and a seed that appears
later is attached by the next run.

Options: `--pool-replicas 1` (one read instead of two; `--update` applies it to existing
cases), `--priority-new 200`, `--pool-folder <id>` / `--seed-folder <id>` if the
folders are not `SegQueue/cases` and `SegQueue/seeds-totalseg`, `--no-hash`.

## 4. Prelabels (later, optional)

Not needed to start: the pool cases begin from the seed. When a 14-class model
(icx14) has predicted the pool volumes, attach its predictions as prelabels -- files
named `<Source>__<Case>.nii.gz`, uint8 on each CT's grid:

```sh
.venv/bin/segqueue14-prelabels attach --dir ~/segqueue-data/prelabels/icx14-v1 \
    --model-version icx14-v1 --verify-grid --dry-run
```

A case with a prelabel opens with it in the 14 classes and the seed still shown beside
it. Only cases nobody has submitted or has open are given one (see the rules in
`segqueue14-prelabels --help`).

## 5. Start the SegQueue14 worker

```sh
sudo cp server/girder_segqueue14/segqueue14-worker.service /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now segqueue14-worker
journalctl -u segqueue14-worker -f
```

Without systemd: `setsid nohup .venv/bin/segqueue14-score --poll 30 --sweep 3600 >>
~/segqueue-data/logs/worker14.log 2>&1 < /dev/null &`. (`segqueue.sh`'s
`pkill -f segqueue-score` does not match `segqueue14-score`, and vice versa.)

The worker scores every two-read pair against each other (Dice, HD95 and presence for
each of the 14 classes) -- pool cases have no ImageCAS-X reference -- and sends a read
to review when it falls below `segqueue14.reference`:

```json
{"mean_dice_flag": 0.60, "required_dice_flag": 0.70, "class_dice_flags": {}, "duplicate_mean_dice_flag": 0.60}
```

Change it as an admin with
`PUT /api/v1/system/setting?key=segqueue14.reference&value=<json>`
(the same way for `segqueue14.policy`: review sampling, lease, concurrency).

## 6. The Slicer module

```sh
python slicer/build-extension14.py      # -> dist/SegQueue-0.14.0-Slicer-5.8.zip
```

From 0.14.0 the module is published as the SegQueue release (D24): SegQueue 0.13's
*Check for updates* -> **Update and restart** installs it, or Extensions Manager ->
Install from file -> restart. The module is **Segmentation -> SegQueue14**; opening
"SegQueue" forwards there.

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

* **janus runs Girder from `~/segqueue-data/segqueue.sh`, not systemd** (2026-10-17).
  `segqueue-girder.service` / `segqueue-mongod.service` are installed but must stay
  stopped: started beside the launcher they crash-loop on the occupied port and
  dbpath (one did for ~20 min on 2026-10-16). The deploy script detects which one
  serves and restarts that way. The launcher does not start `segqueue14-score`;
  after a reboot run the `worker` step.

* If a live CT is ever deleted or re-ingested under a new file id, the SegQueue14 case
  that points at it fails to download (`case_file_missing`). Re-run
  `segqueue14-populate --update` after a live re-ingest.
* Packaged (Docker) deployments: the stock image installs only `./server[scoring]`.
  Going live there means adding `&& pip install "./server/girder_segqueue14[scoring]"`
  to `deploy/Dockerfile` and a `worker14` service running `segqueue14-score`; neither
  is done yet, so the live image is unchanged.
