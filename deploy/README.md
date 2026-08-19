# Deploying SegQueue

One Linux box, four containers, no cloud account. Start to finish this is about
an hour, most of which is waiting for the CT volumes to copy.

## What you need first

* A machine with Docker and the Compose plugin, 16–32 GB RAM, and a data disk
  with room for roughly **300 MB per case** — about 1.5 TB for 5,000 CTs plus
  their segmentations. Put that disk on RAID1 or a ZFS mirror; a single disk
  failure part-way through a 5,000-case project is a year of undergraduate
  labour, not an inconvenience.
* A DNS name pointing at it, **or** a VPN. Off-campus annotators are the norm,
  and exposing Girder directly to the internet is a decision to make
  deliberately rather than by default — Tailscale or WireGuard is the easier and
  safer answer.
* The de-identified volumes, converted to NRRD or NIfTI. DICOM directories are
  not ingested: converting once, centrally, is one decision made properly
  instead of thirty students each meeting Slicer's DICOM import dialogue.

## Bring it up

```sh
cd deploy
cp .env.example .env      # edit DATA_ROOT and SEGQUEUE_DOMAIN
docker compose up -d --build
docker compose logs -f girder
```

Then, once:

1. Open `https://<your domain>/` and create the first account. Girder makes the
   first user a site administrator.
2. **Admin console → Assetstores → Create new filesystem assetstore**, root
   `/data/assetstore`. Nothing can be uploaded until this exists, and the ingest
   CLI refuses to run without it rather than failing halfway.
3. Confirm the plugin loaded: `https://<domain>/api/v1` should list a `segqueue`
   section. The `segqueue-annotators` and `segqueue-reviewers` groups are created
   automatically on load.

## Load the cases

```sh
docker compose exec girder segqueue-ingest --root /incoming --dry-run
docker compose exec girder segqueue-ingest --root /incoming --target coronary
```

Idempotent by case name, so an interrupted 1.5 TB import is resumed by running
it again. Gold-standard cases go in a **separate** directory passed as
`--gold-root`:

```sh
docker compose exec girder segqueue-ingest \
    --root /incoming/pool --gold-root /incoming/gold --target coronary
```

They live apart on purpose. A mis-scoped `--root` that swept the expert
references into the case pool would hand annotators the answers to the very
cases used to measure them, and the failure would be invisible in the metrics.

## Add annotators

Either through Girder's own admin UI (create the user, add them to
`segqueue-annotators`) or:

```sh
curl -u admin -X POST "https://<domain>/api/v1/segqueue/users" \
     -d login=student01 -d email=student01@example.edu \
     -d firstName=Ada -d lastName=Lovelace -d quota=200
```

Reviewers are the same, plus membership of `segqueue-reviewers`.

## The labelling protocol

Segment names, label values, colours and the instruction text are **server
settings**, not something shipped in the extension:

```sh
docker compose exec girder girder-shell
>>> from girder.models.setting import Setting
>>> Setting().get('segqueue.project')
```

Changing them changes what every annotator draws, at their next login, with
nobody reinstalling anything. The sampling policy — review rates, gold and
duplicate rates, lease length, concurrency — lives beside it under
`segqueue.policy`.

## Day-to-day

| Question | Answer |
|---|---|
| How is the project going? | `GET /api/v1/segqueue/stats` — burn-down, velocity, projected finish |
| Who is doing what, how fast? | `GET /api/v1/segqueue/stats/annotators` |
| Anything stuck? | `POST /api/v1/segqueue/sweep?dryRun=true` |
| Is scoring keeping up? | `docker compose logs worker` |

The worker container scores gold and duplicate submissions every 30 seconds and
sweeps lapsed leases every hour. There is no cron job to forget: a case whose
annotator dropped the course is back in the pool within the hour, and the
`sweep` endpoint exists only for when an admin does not want to wait.

## Backups

`backup.sh` dumps MongoDB and hands both the dump and the assetstore to restic.
Cron it nightly on the host:

```sh
0 2 * * * RESTIC_REPOSITORY=/mnt/backup/segqueue \
          RESTIC_PASSWORD_FILE=/root/.restic-pass \
          /srv/segqueue/deploy/backup.sh >> /var/log/segqueue-backup.log 2>&1
```

Restore is `mongorestore --archive --gzip` plus a restic restore of the
assetstore, in that order. Test it once, on purpose, before you need it — an
untested backup is a hypothesis.

## Upgrading

```sh
git pull && docker compose up -d --build
```

The wire protocol between the extension and the server is versioned. If a
release changes it incompatibly, bump `PROTOCOL_VERSION` and
`MIN_CLIENT_PROTOCOL` in `src/segqueue/protocol.py`; old extensions then get a
refusal telling the student to update, instead of writing subtly wrong data for
a month before anyone notices.
