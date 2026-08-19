# SegQueue server setup

Everything needed to stand up the annotation server, load it with data, and hand
logins to a class. Start to finish this is about an hour of attention plus
however long the dataset takes to copy.

The annotator side — installing the Slicer extension, what the panel does — is in
[`SegQueue-Setup-Guide.pdf`](SegQueue-Setup-Guide.pdf). This document is the
server runbook.

To hand annotators the client, build the extension package once per release:

```sh
python slicer/build-extension.py     # -> dist/SegQueue-<version>-Slicer-5.8.zip
```

They install it with **Extensions Manager -> Install from file**. Rebuild it
after any change to `src/segqueue`, or their copy speaks an older wire protocol
than this server.

---

## 1. What you are installing

Four containers on one Linux box. No cloud account, nothing phones home.

| Container | Job | If it dies |
|---|---|---|
| `caddy` | TLS and reverse proxy. Gets and renews its own certificate. | Nobody can connect. |
| `girder` | The API: accounts, tokens, resumable uploads, storage, and the SegQueue plugin. | Everything stops; no data lost. |
| `mongo` | All metadata — cases, assignments, submissions, reviews. | Girder refuses to start. Restore from the nightly dump. |
| `worker` | Scores gold and duplicate work every 30 s; reclaims lapsed leases hourly. | **Silent.** Scores stop appearing and stranded cases stay stranded. Check the log weekly. |

The task is fixed at four structures, which the server owns and the extension
obeys:

| Segment | Label | Required |
|---|---|---|
| `left_main` | 1 | yes |
| `left_anterior_descending` | 2 | yes |
| `left_circumflex` | 3 | yes |
| `right_coronary_artery` | 4 | no — may be small or absent in a left-dominant system |

These label values must stay in step with `configs/labels/coronary.yaml`. If they
drift, `segtrain convert` will build a training set with the wrong structures
under the right names — the worst possible outcome, and completely silent.

---

## 2. Requirements

| | |
|---|---|
| Host | Linux with Docker and Compose v2 (`docker compose`, not `docker-compose`) |
| RAM | 16 GB works, 32 GB is comfortable |
| Disk | **~300 MB per case.** The source dataset is ~1,200 CT studies; budget accordingly, plus room for submissions. Put it on RAID1 or a ZFS mirror — a disk failure mid-project is a term of undergraduate labour, not an inconvenience. |
| Network | A DNS name pointing at the box, **or** a VPN (Tailscale/WireGuard). See §7. |
| Power | A UPS. MongoDB survives power loss far better with one. |

---

## 3. Get the data

The default source is the **TotalSegmentator** release on Zenodo:

> <https://zenodo.org/records/10047292>

Roughly 1,200 whole-body CT studies, each already segmented into 117 structures.
That presegmentation is what makes it usable here without opening a single image:

```
<root>/s0011/ct.nii.gz
<root>/s0011/segmentations/heart.nii.gz              → this case has a heart
<root>/s0011/segmentations/liver.nii.gz
<root>/s0011/segmentations/femur_left.nii.gz
...
```

```sh
mkdir -p /srv/incoming && cd /srv/incoming
# download the archive from the record page, then
unzip Totalsegmentator_dataset_v201.zip
```

Two things the ingest does with those filenames:

**Only cases with a heart are loaded.** TotalSegmentator is whole-body, so much
of it is legs, heads and abdomens with no coronary anatomy in the field of view
at all. Assigning those spends the one resource the project is short of —
annotator hours — on scans that cannot be annotated. A case is eligible if it has
any of `heart`, `heart_myocardium`, `heart_atrium_left`, `heart_atrium_right`,
`heart_ventricle_left`, `heart_ventricle_right` (v2 ships the first, v1 the
rest). The eligible ones also ship their heart mask to the annotator, which the
extension uses to centre the view and to keep edits inside the heart.

**A case that already has a coronary mask hands it to the annotator.** If
`segmentations/coronary_arteries.nii.gz` exists, it is uploaded with the case and
loaded in Slicer as a helper segment. It is a *binary lumen*, not per-branch
labels, so it is a head start rather than an answer: the annotator splits an
existing tree into LM / LAD / LCx / RCA instead of drawing one from scratch —
minutes instead of an hour.

> **Note.** The base Zenodo release does **not** include coronary masks;
> TotalSegmentator's `coronary_arteries` task is licensed separately. If your
> copy has them — from that task, or from your own earlier model — ingest picks
> them up with no extra flags. If not, everything still works; annotators simply
> draw from scratch.

Helper masks are never submitted. The extension exports only the project's own
four segments, and refuses to submit at all if any other label value appears in
the exported volume.

---

## 4. Install

```sh
git clone https://github.com/christianGRogers/Asclepius.git /srv/segqueue
cd /srv/segqueue/deploy
cp .env.example .env
$EDITOR .env
```

| Setting | What to put |
|---|---|
| `SEGQUEUE_DOMAIN` | Public name, e.g. `segqueue.example.edu`. A hostname gets a real Let's Encrypt certificate; an `https://10.0.0.5` gets a self-signed one — read §7 first. |
| `SEGQUEUE_TLS_EMAIL` | Where Let's Encrypt sends expiry warnings. |
| `DATA_ROOT` | The mirrored data disk, e.g. `/srv/segqueue-data`. Mongo's files and the assetstore both live under it. **Not the system disk.** |
| `CASE_SOURCE_ROOT` | `/srv/incoming` from §3. Mounted read-only at `/incoming` in the container. |
| `MONGO_CACHE_GB` | About a quarter of system RAM. |

```sh
docker compose up -d --build
docker compose logs -f girder
```

Wait for these three lines, in this order:

```
INFO:girder.models:Connecting to MongoDB: mongodb://mongo:27017/girder
INFO:girder.plugin:Loaded plugin "segqueue"
INFO:girder.asgi:Girder server running
```

If the plugin line is missing, the API answers but every `/segqueue/…` route
404s. See §11.

### 4.1 First account

Open `https://<domain>/` and register. **The first user Girder sees becomes a
site administrator** — do this before telling anyone the address.

On a brand-new database the plugin loads before any account exists, so it cannot
yet create the `segqueue-annotators` and `segqueue-reviewers` groups (Girder
needs an owner for a group). That is handled: they are created on the next
restart, or the first time you create an annotator. Nothing for you to do.

### 4.2 Assetstore

**Nothing can be uploaded until this exists**, and the failure is confusing if
you skip it.

Admin console → **Assetstores** → **Create new filesystem assetstore**:

- Name: `store`
- Root directory: `/data/assetstore` — the path *inside the container*. Compose
  maps it to `$DATA_ROOT/assetstore` on the host.

The ingest CLI checks for this and refuses to start without it, rather than
failing partway through a large import.

### 4.3 Verify the plugin

Open `https://<domain>/api/v1` — the generated docs should show a **segqueue**
section with `project`, `next`, `mine`, `review/queue`, `stats` and `sweep`.

---

## 5. Load the cases

Always dry-run first. It changes nothing and tells you what the filter did:

```sh
docker compose exec girder segqueue-ingest --root /incoming --dry-run
```

It prints a scan summary before it lists anything — this is a real run against a
five-case test tree, and your numbers will be larger:

```
Scanned /incoming
  5 case(s) with a CT
  3 with a heart segmentation, 2 without
  1 with a pre-existing coronary mask
  0 with an expert reference

  + s0001  [coronary seed, heart]
  + s0002  [heart]
  + s0003  [heart]
```

The rejected count is printed on purpose. A scan that quietly returns 12 of 1,200
looks exactly like a correct one until somebody asks why the project finished
early.

```sh
docker compose exec girder segqueue-ingest --root /incoming --target coronary
```

| Flag | Meaning |
|---|---|
| `--root` | Directory holding one subdirectory per case. |
| `--layout` | `totalsegmentator` (default) or `flat` for a plain directory of volume files. |
| `--all-cases` | Ingest cases with no heart segmentation too. Off by default. |
| `--no-seed` | Do not ship pre-existing coronary masks. Use this to measure unaided annotation time. |
| `--no-region` | Do not ship heart masks. The extension then cannot centre the view. |
| `--gold-root` | Directory of expert per-branch references — see §5.1. |
| `--target` | Recorded on each case. Defaults to `coronary`. |
| `--priority` | Higher is served first. Useful for a pilot batch. |
| `--limit` | Stop after N new cases. Good for a first run. |
| `--admin` | Login owning the uploads. Defaults to the first site admin. |
| `--dry-run` | Report and change nothing. |

**Ingest is idempotent by case name.** An interrupted import resumes by running
the same command again — which matters, because that is exactly the kind of job
that gets interrupted.

The SHA-256 of every CT is computed here, once, and every later transfer is
verified against it. A file corrupt on arrival is therefore caught by the first
annotator instead of being blamed on their connection.

### 5.1 Gold-standard cases

```sh
docker compose exec girder segqueue-ingest \
    --root /incoming --gold-root /incoming-gold --target coronary
```

Expert references live in a **separate directory**, never beside the volumes. A
mis-scoped `--root` that swept them into the pool would hand annotators the
answers to the very cases used to measure them, and nothing downstream would
notice. Aim for about 5% of the pool.

---

## 6. People

```sh
curl -u admin1 -X POST "https://<domain>/api/v1/segqueue/users" \
     -d login=student01 -d email=student01@example.edu \
     -d firstName=Ada -d lastName=Lovelace \
     -d password=... -d quota=200
```

Or through Girder's admin UI: create the user, add them to
`segqueue-annotators`. Reviewers also join `segqueue-reviewers`; site admins
review by right.

| Operation | Call |
|---|---|
| Change a quota | `PATCH /segqueue/users/<id>?quota=300` (`-1` removes the cap) |
| Grant reviewer | `PATCH /segqueue/users/<id>?reviewer=true` |
| Student left the course | `PATCH /segqueue/users/<id>?disabled=true` — also releases every case they hold |

---

## 7. The certificate decision

In descending order of how much trouble it saves you:

1. **A real DNS name.** Caddy gets a Let's Encrypt certificate and renews it
   forever. Nothing to install on annotator machines. Needs ports 80 and 443
   reachable from the internet when the certificate is issued.
2. **A VPN with a real name.** Tailscale or WireGuard, with the box having a
   proper hostname inside it. Same as above and the server is never exposed.
   Recommended for a campus machine.
3. **Self-signed.** Caddy issues its own. The Slicer extension will then refuse
   to connect until Caddy's local CA root — inside the caddy container at
   `/data/caddy/pki/authorities/local/root.crt` — is installed on every annotator
   machine. Fine for a few lab machines, painful for thirty students.

---

## 8. Configuration

Two settings hold everything tunable. Both are validated on write, so a bad value
is rejected immediately rather than failing when the fiftieth annotator asks for
a case.

```sh
# read
docker compose exec girder sh -c 'cat > /tmp/s.py <<EOF
from girder.models.setting import Setting
import json
print(json.dumps(Setting().get("segqueue.policy"), indent=2))
EOF
girder shell /tmp/s.py'
```

```sh
# write
docker compose exec girder sh -c 'cat > /tmp/s.py <<EOF
from girder.models.setting import Setting
policy = Setting().get("segqueue.policy")
policy["base_review_rate"] = 0.30
Setting().set("segqueue.policy", policy)
EOF
girder shell /tmp/s.py'
```

### `segqueue.policy`

| Key | Default | Controls |
|---|---|---|
| `training_gate_cases` | 5 | Every annotator's first N cases are reviewed by a human, whatever the sampling says. |
| `base_review_rate` | 0.20 | Fraction of ordinary work reviewed once past the gate. |
| `trusted_review_rate` | 0.10 | Rate for annotators with a long clean streak. |
| `trusted_after_clean` | 20 | Consecutive approvals needed to earn it. |
| `probation_cases` | 3 | Reviewed at 100% immediately after any rejection. |
| `gold_rate` | 0.05 | Share of assignments that are gold-seeded. |
| `duplicate_rate` | 0.05 | Share that are blind duplicates of approved cases. |
| `gold_first_case` | true | Make each annotator's first case a gold one, for a day-one baseline. |
| `lease_days` | 7.0 | How long a case may be held before the sweeper reclaims it. |
| `stale_heartbeat_hours` | 72.0 | Silence after which a case is reclaimable even inside its lease. |
| `max_concurrent` | 1 | Cases one annotator may hold. Raising it also raises the extension's local cache cap. |
| `gold_dice_flag` | 0.70 | Mean Dice against the expert reference below which a submission is pulled back for a human. |
| `duplicate_dice_flag` | 0.70 | Same, for agreement within a duplicate pair. |

Gold and duplicate rates are drawn from **one** random number partitioned across
the two, so they can never overlap and a case is never both.

### `segqueue.project`

`name`, `instructions` (Markdown, shown above the segment list in Slicer), and
`segments` — each with `name`, `label`, `color`, `required` and `hint`. Duplicate
names *and* duplicate label values are both rejected on save.

Changing this changes what every annotator draws at their next login. Nobody
reinstalls anything.

---

## 9. Verify

```sh
python tests/segqueue_e2e.py --url https://<domain>
```

Drives the real API with the same client the Slicer extension uses, so a pass
means the extension will work. Needs at least one unclaimed case (two to also
check the concurrency guard) and is idempotent.

It covers: login, the labelling protocol, case assignment, checksum-verified
download, the heart and coronary masks that ship with a case, five submission
refusals (empty / stray / off-protocol / resampled / corrupted), the training
gate, rejection with a comment, rework as attempt 2 with the lease renewed,
approval, and the atomic claim.

```
================================================================
34 passed, 0 failed
================================================================
```

The unit suites need no server:

```sh
pytest                    # 366 tests

# The concurrency tests need a real MongoDB -- the point of them is that the
# atomic claim survives thirty annotators starting at once, which no fake shows.
docker run -d --rm -p 27099:27017 mongo:7
SEGQUEUE_TEST_MONGO=mongodb://localhost:27099 pytest tests/test_segqueue_server.py
```

---

## 10. Running it

| Question | Call |
|---|---|
| How is the project going? | `GET /api/v1/segqueue/stats` — burn-down, 14-day velocity, projected finish |
| Who is doing what, how fast? | `GET /api/v1/segqueue/stats/annotators` — throughput, median time per case, QA pass rate |
| Anything stranded? | `POST /api/v1/segqueue/sweep?dryRun=true` |
| Is QA keeping up? | `docker compose logs --tail=50 worker` |

The worker sweeps hourly on its own; the endpoint exists for when you do not want
to wait. There is no cron job to forget.

### Backups

```
0 2 * * * RESTIC_REPOSITORY=/mnt/backup/segqueue \
          RESTIC_PASSWORD_FILE=/root/.restic-pass \
          /srv/segqueue/deploy/backup.sh >> /var/log/segqueue-backup.log 2>&1
```

The script dumps MongoDB *first*, into the tree restic then reads, so the
metadata snapshot is never newer than the files it describes. The other order
produces a backup referencing submissions it does not contain — which looks fine
until the day you restore it.

Restore is `mongorestore --archive --gzip`, then a restic restore of the
assetstore, in that order. **Test it once, on purpose, before you need it.**

### Upgrading

```sh
cd /srv/segqueue && git pull
cd deploy && docker compose up -d --build
python ../tests/segqueue_e2e.py --url https://<domain>
```

The extension–server protocol is versioned. If a release changes it
incompatibly, old extensions get a refusal telling the student to update, rather
than writing subtly wrong data for a month before anyone notices.

---

## 11. Troubleshooting

| Symptom | Cause and fix |
|---|---|
| Every `/segqueue/…` route 404s | The plugin did not load. `docker compose logs girder \| grep plugin`. Usually the image was built without the repository root — see the next row. |
| `ImportError: girder-segqueue needs the segqueue package` | The plugin is installed but the shared package is not. It deliberately does not declare it as a dependency: the distribution providing it is named `segtrain`, and an unrelated project owns that name on PyPI. Install the repo root first (`pip install /repo`, then `pip install /repo/server`). The supplied Dockerfile already does. |
| `Girder has no assetstore configured` from ingest | §4.2 was skipped. |
| Ingest finds 0 eligible cases | The tree is not in TotalSegmentator layout (no `<case>/segmentations/`), or genuinely has no cardiac scans. Try `--layout flat`, or `--all-cases` to bypass the heart filter. |
| Uploads fail with a permission error | The annotator is not in `segqueue-annotators`. That group is the only place they get write access, and only to the drop-box folder. |
| Extension: *"Could not reach the server… check that the VPN is connected."* | Exactly that — or a self-signed certificate whose CA root is not installed. See §7. |
| Extension: *"the server returned something that is not JSON"* | A captive portal or proxy is intercepting. Common on campus guest wifi. |
| Extension: *"Could not import the segqueue package"* | The module was loaded from a copy outside the repository. It imports `segqueue` from the sibling `src/`; both must travel together. |
| Annotator gets "no cases available" while cases remain | Normal near the end: every remaining case has already been shown to them, and nobody is offered the same case twice. Check `GET /segqueue/stats`. |
| Submissions accepted but never scored | The worker is down or lacks the scoring extras. `docker compose logs worker`. |
| Git Bash on Windows: `--root C:/Users/… is not a directory` | MSYS is rewriting container paths. Prefix with `MSYS_NO_PATHCONV=1`, or use PowerShell. |
| Mongo crashes on Windows | Its data directory is on a bind mount. Use a Docker-managed volume — laptop testing only; see the PDF guide §4. |

---

## 12. Known gaps

- **No export to the training layout.** Approved submissions sit in the
  assetstore as label volumes on the source grid — the right contents — but
  reshaping them into the `<case>/segmentations/` layout `segtrain convert` reads
  is manual today.
- **The Slicer panel is verified, but not against a live server.** The packaged
  extension installs and loads in a real Slicer 5.8.1, the effects, masking and
  export were checked there, and the network layer is tested against a stub. What
  has not been done is one annotator driving the panel through a real case from
  *Get next case* to *Submit*.
- **Gold and duplicate scoring has not run on real label volumes.** The metric
  code is the training pipeline's own and is unit-tested, but the path from a
  real `.seg.nrrd` to a Dice number has not been through a live case.
- **Nothing has been run at full scale.** The 30-annotator claim race is tested
  against real MongoDB; sustained load over a term is not.
- **No admin web UI.** Admin operations are REST calls plus Girder's stock
  console. Deliberate — a dashboard is a lot of code for one grad student to
  maintain, and `stats` answers the questions that matter.
