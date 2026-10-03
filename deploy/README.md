# Deploying SegQueue

> **janus.bradensbay.com does not run Docker.** It runs the same four parts
> natively -- mongod, girder and the score worker -- started by
> `~/segqueue-data/segqueue.sh {start|stop|restart|status}`, with the checkout at
> `~/Asclepius` and its own `.venv`. The compose instructions below describe the
> packaged deployment; for that box, read "Upgrading" at the end instead.
>
> This is worth knowing before you tidy anything: deleting the checkout does not
> stop the running server -- Linux keeps deleted files open -- so the API goes on
> answering while every route that reads a file from disk starts failing. That is
> what took the web UI down on 2026-09-30 and left it 404ing until 2026-10-02.

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

## Moving a native deployment into containers

janus was set up natively and can be moved onto the compose stack without moving
its data: `DATA_ROOT` is expected to hold `mongo/` and `assetstore/`, which is
exactly what `segqueue-data/` already is, so the same directories are
bind-mounted in.

```sh
sudo bash deploy/containerize.sh --check      # read-only; says what it would do
sudo bash deploy/containerize.sh              # does it
sudo bash deploy/containerize.sh --rollback   # back to the native stack
```

Three things change, and each is the sort that loses a dataset quietly if it is
skipped. The script does all three and refuses to start if any precondition
fails.

**The assetstore path lives in the database.** Girder stores the absolute root of
its filesystem assetstore in Mongo. Natively that is `<DATA_ROOT>/assetstore`;
inside the container the same bytes are at `/data/assetstore`. Without the
rewrite Girder starts perfectly and reports every file as missing — 86 GB of
annotation work, apparently gone, with nothing in any log.

**Mongo data files are version-specific.** The `mongo:7` image refuses data
written by a newer server, and data from an older one needs its
featureCompatibilityVersion raised one major version at a time. Checked, not
assumed.

**The files are owned by a host user.** The image runs as uid 1000. If the data
belongs to anybody else the containers fail on write, which surfaces as failed
uploads rather than as a startup failure.

Caddy stays off unless you ask for it: `docker compose --profile tls up -d`.
Where TLS already terminates somewhere else — a tunnel, a front proxy, another
host — starting Caddy fights for 80 and 443 with whatever already serves the
name. janus is that case, so girder publishes `${GIRDER_PORT:-8080}` and the
existing front end keeps working untouched.

Nothing is deleted by any of this. The native launcher stays where it is, which
is what makes `--rollback` possible.

## Keeping it running

The native deployment on janus started as `nohup` from somebody's shell, which
means two things were true until the units below existed: it did not come back
after a reboot, and nothing restarted it if it died. The box had been up since
February, so neither had ever been tested.

`deploy/systemd/` holds three units -- mongod, girder, the worker -- with
`Restart=always` and the right ordering. Install them once:

```sh
sudo cp deploy/systemd/segqueue-*.service /etc/systemd/system/
sudo systemctl daemon-reload
bash ~/segqueue-data/segqueue.sh stop            # stop the hand-started stack
sudo systemctl enable --now segqueue-mongod segqueue-girder segqueue-worker
systemctl is-active segqueue-mongod segqueue-girder segqueue-worker
curl -fsS localhost:8080/api/v1/system/version
```

After that `segqueue.sh` is only a fallback; `systemctl restart segqueue-girder`
is the normal verb, and `journalctl -u segqueue-girder -f` the normal log.

One line in `segqueue-girder.service` is load-bearing beyond supervision:

```
WorkingDirectory=/home/christian/Asclepius
```

systemd refuses to start a unit whose working directory does not exist. Deleting
the checkout therefore fails *loudly* rather than leaving a server running out of
deleted files, which is what happened on 2026-09-30: the API went on answering
from memory while every route that reads a file returned 404 or 500, and it took
three days to notice.

`deploy/segqueue.sh` is the launcher, tracked here so it is reproducible. The
deployed copy deliberately lives *outside* the checkout, at
`~/segqueue-data/segqueue.sh` -- which is the only reason it survived that
deletion and the stack could be restarted at all.

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

Packaged (Docker) deployments:

```sh
git pull && docker compose up -d --build
```

janus.bradensbay.com, which is native:

```sh
cd ~/Asclepius && git fetch origin && git checkout main && git pull
.venv/bin/python -m pip install .            # provides `segqueue`
.venv/bin/python -m pip install "./server[scoring]"
bash ~/segqueue-data/segqueue.sh restart
bash ~/segqueue-data/segqueue.sh status
```

The root package first, then the plugin: `girder-segqueue` deliberately does not
declare `segqueue` as a dependency, because the distribution carrying it is named
`segtrain` and an unrelated project owns that name on PyPI.

`.github/workflows/server-ssh.yml` does exactly this over SSH -- run it with
`mode: deploy` rather than doing it by hand.

The wire protocol between the extension and the server is versioned. If a
release changes it incompatibly, bump `PROTOCOL_VERSION` and
`MIN_CLIENT_PROTOCOL` in `src/segqueue/protocol.py`; old extensions then get a
refusal telling the student to update, instead of writing subtly wrong data for
a month before anyone notices.
