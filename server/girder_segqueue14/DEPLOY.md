# Deploying SegQueue14 beside the live SegQueue

> **Since D36 (2026-10-25, issue #124) SegQueue14 is the only queue on janus.** The old
> 4-class plugin (`girder-segqueue`) is uninstalled, its groups are deleted, and
> SegQueue14 writes into the `SegQueue` collection (the old queue's `gold`, `incoming`
> and `submissions` are in `SegQueue/_archive-4class/`). The old queue's Mongo
> collections (`segqueue_case`, ...) are kept, unused. `CCTA-Pool` (D22's archive) and
> `ImageCAS-X` are unchanged. See
> [D36 on janus](#d36-on-janus-one-of-each) below; the rest of this page describes the
> two-plugin setup it started from.

SegQueue14 is a second Girder plugin. It runs in the **same** Girder as the live
SegQueue, on the same database, and shares nothing writable with it:

| | live SegQueue | SegQueue14 |
|---|---|---|
| Python distribution | `girder-segqueue` (`server/`) | `girder-segqueue14` (`server/girder_segqueue14/`) |
| Girder plugin name | `segqueue` | `segqueue14` |
| REST prefix | `/api/v1/segqueue` | `/api/v1/segqueue14` |
| Girder collection | `SegQueue` | `SegQueue` since D36 (`prelabels/`, `submissions/`, `incoming/`); was `SegQueue14` |
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
`SegQueue/seeds-totalseg` as a guide the annotator divides into the four classes (D25); it is
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

Not needed to start: the pool cases begin from the seed. When the 4-class model
(`trillium/icx4`) has predicted the pool volumes, attach its predictions as prelabels --
files named `<Source>__<Case>.nii.gz`, uint8 (0-4) on each CT's grid:

```sh
.venv/bin/segqueue14-prelabels attach --dir ~/segqueue-data/prelabels/icx4-v1 \
    --model-version icx4-v1 --verify-grid --dry-run
```

A case with a prelabel opens with it in the four classes and the seed still shown beside
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
each of the four classes) -- pool cases have no ImageCAS-X reference -- and sends a read
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

## D36 on janus: one of each

Run through *SegQueue14 on janus*, in this order, with `status` before and after each
step. Every destructive step is a dry run unless it says `--apply`, and refuses on its
preconditions.

| Step | What it does | Refuses when |
|---|---|---|
| `backup` | `status` (item counts per collection, for the before/after check), then `mongodump` of `girder` (`~/segqueue-data/pre-d36-<time>.archive.gz`, or `.tar.gz` from the pymongo fallback) | the dump fails |
| `retire-live` | stops `segqueue-score`, uninstalls `girder-segqueue`, restarts Girder; checks `/segqueue/stats` is 404 and `/segqueue14/project` 401 | no `pre-d36` backup from the last 24 h |
| `restore-live` | rollback of `retire-live`: reinstalls `~/Asclepius/server`, restarts | |
| `retire-groups [--apply]` | deletes `segqueue-annotators` and `segqueue-reviewers` (Girder removes them from users and access lists) | the old plugin is installed (its `ensureGroups()` would recreate them) |
| `consolidate [--apply]` | moves `SegQueue/{gold,incoming,submissions}` into `SegQueue/_archive-4class/`, installs `main` (SegQueue14 now writes into `SegQueue`), removes the empty `SegQueue14` collection | the old plugin is installed; SegQueue14 has any submission or prelabel; `SegQueue14` holds any item; `main` does not have the new `COLLECTION_NAME` |
No step writes to `CCTA-Pool` or `ImageCAS-X`; compare their item counts in
`status` before and after.

**Rollback.** `restore-live` brings the old plugin back (and with it its two groups,
recreated empty); the archived folders can be moved back in the Girder web UI. For
anything else, restore the `pre-d36` dump (`mongorestore --drop --gzip --archive=...`);
no step deletes assetstore files except the removal of the empty `SegQueue14`
collection.

## D42 on janus: hourly backup to the backup server

Every hour, the Girder database and every submission and reviewer revision file
go to a restic repository on the lead's backup server (same LAN as janus), over
SFTP. CT volumes are **not** backed up: they are kept in CCTA-Pool. Code:
`deploy/backup/` and `deploy/systemd/segqueue-backup*`. Issue #283.

**The repository is not encrypted and has no password** (the lead's decision on
#283: the data is not sensitive and is to be published). restic runs with
`--insecure-no-password`, which needs restic 0.17 or newer. Access to the backups is
the backup server's SFTP login and nothing else.

**What is in each snapshot**

* The whole `girder` database, as uncompressed BSON in mongodump's layout. Each
  collection is written in `_id` order, so restic stores only what changed.
* Every assetstore file a `segqueue14_submission` row points at, found through the
  database (`fileId` -> `file` -> assetstore root + path). That covers annotators'
  submissions and reviewers' revisions. Old-queue `segqueue_submission` files are
  included too.
* Seeds, prelabels (current and earlier) and reference labels up to 50 MB each
  (`BACKUP_MAX_EXTRA_MB`).
* Never included: a case's `fileId` or `regionFileId` (the CT), even when something
  else points at it, or anything filed under `CCTA-Pool` or `ImageCAS-X`.
* `manifest.json` lists every file, its kind and checksum, plus any file the
  database names that was not found on disk.

**How it stays out of the annotators' way**

* It only reads: no Girder or Mongo restart, no fsync lock, no write.
* The unit runs at `Nice=19` with `IOSchedulingClass=idle` (ionice -c3), and restic
  is capped at 20 MiB/s.
* A `flock` stops overlaps: a run that would overlap is skipped and logged.
* It refuses to start if `/var/lib/segqueue-backup` or `~/segqueue-data` has less
  than 5 GB free (`BACKUP_MIN_FREE_MB`).
* The local dump is written to a temp name, renamed when complete, and deleted once
  the snapshot is saved.
* Retention: 48 hourly, 14 daily, 8 weekly and 12 monthly snapshots. A daily timer
  (03:40) prunes and runs `restic check --read-data-subset=1%`.

**Steps** (Actions -> *SegQueue14 on janus*; all idempotent):

| Step | What it does |
|---|---|
| `backup-install` | On janus: installs the pinned restic 0.17.3 at `/usr/local/bin/restic` (the official release, its SHA-256 checked; the distro's restic is not used) and creates an SSH key at `/etc/segqueue-backup/id_ed25519` (once). On the backup server: authorises that key, limited to `sftp-server` where the binary is found, `restrict` in any case. Back on janus: tries each route to the backup server, pins its host key, opens or creates the (unencrypted) repository, installs and starts the timers, and takes the first backup. It refuses an existing repository that is encrypted. |
| `backup-status` | Read-only. Shows the timers, the last run's result, the snapshot count, the newest snapshot's age and size, the repository size and the last log lines. **Fails if the newest snapshot is older than 2 hours.** |
| `backup-restore-test` | Restores the newest snapshot into `/var/lib/segqueue-backup/restore-test`. Loads the database into a scratch `mongod` on 127.0.0.1:27199 (it refuses the live server). Checks every submission's file is present and its SHA-256 matches the one Girder recorded, then deletes the scratch copy. Live data is not touched. Run it once before calling the job live, then monthly. |
| `backup-off` | Stops and disables both timers. Keeps the repository, every snapshot and the key. `backup-install` turns it back on. |

**Secrets** (repository settings -> Secrets and variables -> Actions):

| Secret | Needed for | What |
|---|---|---|
| `SSH_PORT_SFTP_SERVER` | every backup step | The backup server's SSH port. Its host and login are the same as janus's (`SSH_HOST`, `SSH_USERNAME`, `SSH_PASSWORD`). |
| `BACKUP_SFTP_LAN_ADDRESS` | optional | `host:port` of the backup server **as seen from janus**. It is tried first if set. Otherwise janus tries `SSH_HOST:SSH_PORT_SFTP_SERVER`. Install says which route worked, or what to set if none did. |
| `SSH_KNOWN_HOSTS_SFTP_SERVER` | optional | The backup server's `known_hosts` lines. Without it the runner trusts the key offered on first contact. Janus pins only a key matching what the runner saw. |

The SSH password is used only by the runner. It is never stored on janus: janus
reaches the backup server with its own key.

**Restoring for real** (the lead's call; the drill above does not need this):

```sh
# Anywhere with restic >= 0.17 and SFTP access to the backup server; on janus:
sudo -i
set -a; . /etc/segqueue-backup/backup.env; set +a
R=(restic --insecure-no-password -o "sftp.command=$BACKUP_SFTP_COMMAND")
# Elsewhere: R=(restic --insecure-no-password -r sftp:<user>@<backup server>:segqueue-backup)
"${R[@]}" snapshots --tag segqueue14          # pick one; or use `latest`
"${R[@]}" restore <id> --target /var/tmp/sq-restore
# The database (mongodump layout; mongorestore from the MongoDB database tools):
mongorestore --drop --nsInclude 'girder.*' /var/tmp/sq-restore/var/lib/segqueue-backup/dump
# The files are under the target at their original absolute paths. Put back only what is missing:
rsync -a --ignore-existing /var/tmp/sq-restore/home/christian/segqueue-data/ /home/christian/segqueue-data/
```

Stop Girder and the workers before a database restore. The CT volumes are not in
the backup: re-import them from CCTA-Pool if the assetstore itself was lost.

**Logs:** `journalctl -u segqueue-backup` (hourly) and `journalctl -u segqueue-backup-check` (daily).

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

* **`segqueue14-export` leaves the D27 sealed pool cases out** (150 patients + 20
  ImageCHD report-only, `configs/segqueue14/sealed-pool-2026-10.json`) and prints how
  many. It needs the seal file: run it from the `~/Asclepius-sq14` checkout, or pass
  `--seal-file ~/Asclepius-sq14/configs/segqueue14/sealed-pool-2026-10.json` (or set
  `SEGTRAIN_POOL_SEAL`). A missing or altered file stops the export. `--acceptance-scoring`
  includes them, for acceptance scoring only. Annotators see no difference.
* If a live CT is ever deleted or re-ingested under a new file id, the SegQueue14 case
  that points at it fails to download (`case_file_missing`). Re-run
  `segqueue14-populate --update` after a live re-ingest.
* Packaged (Docker) deployments: the stock image installs only `./server[scoring]`.
  Going live there means adding `&& pip install "./server/girder_segqueue14[scoring]"`
  to `deploy/Dockerfile` and a `worker14` service running `segqueue14-score`; neither
  is done yet, so the live image is unchanged.
