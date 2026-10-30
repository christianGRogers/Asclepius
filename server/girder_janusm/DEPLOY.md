# Deploying the Janus-M read queue (JA7)

> **Not deployed.** Deploying to janus needs the lead's go-ahead, and the PM asks for
> it. These notes say what a deploy would be, so it can be reviewed beforehand.

The Janus-M read queue is its own Girder plugin, beside SegQueue14 in the same Girder. It shares nothing writable with SegQueue14 and reads nothing of it:

| | SegQueue14 | Janus-M reads |
|---|---|---|
| Python distribution | `girder-segqueue14` | `girder-janusm` (`server/girder_janusm/`) |
| Girder plugin name | `segqueue14` | `janusm` |
| REST prefix | `/api/v1/segqueue14` | `/api/v1/janusm` |
| Girder collection | `SegQueue` | `JanusM` (`seeds/`, `incoming/`, `reads/`) |
| Mongo collections | `segqueue14_*` | `janusm_case`, `janusm_read` |
| Settings | `segqueue14.*` | `janusm.sealOpen`, `janusm.maxOpen` |
| Groups | `segqueue14-annotators`, `segqueue14-reviewers` | `janusm-readers`, `janusm-admins` |
| Wire protocol | SegQueue14 (16) | `janusm-read` 1 |
| Worker | `segqueue14-score` | `janusm-check` |

What it **reads** and never writes: the CT files in `ImageCAS-X/cases` (D22), by
file id. Seal and decision cases are ImageCAS-X *train* cases only (JA5, JA6).

## What a deploy would be (after the lead says yes)

1. Back up the database, as for any plugin change.
2. Install from a `main` checkout, root first:

   ```sh
   pip install /path/to/Asclepius                       # provides janusm, janusm_reads
   pip install "/path/to/Asclepius/server/girder_janusm[check]"
   ```
   and restart Girder. `/api/v1/janusm` appears; SegQueue14 is unchanged.
3. Copy the seed job's output from Fir (`$SCRATCH/janusm/seeds`, protocol §5.3) to the
   server, then:

   ```sh
   janusm-populate --seeds-dir /path/to/seeds --dry-run   # 100 cases, 10 blank, 0 problems
   janusm-populate --seeds-dir /path/to/seeds
   ```
   It refuses the whole run on any JA12 guard hit, a CT it cannot match uniquely, or a
   seeded case with no seed. Check the dry run's CT names (`c0001` is ImageCAS 2).
4. Run the check worker beside Girder: `janusm-check --every 30`.
5. Add readers to `janusm-readers` (Girder's group page). Being a SegQueue14
   annotator does not make anyone a reader.
6. Seal cases stay closed (`janusm.sealOpen` false) until the seal is re-powered on
   the first 20 double-read decision cases (JA6); then an admin calls
   `POST /api/v1/janusm/admin/seal/open`.

Per wave, for the anchoring report (protocol §7):

```sh
janusm-export --out /tmp/wave1 --seeds-dir /path/to/seeds --wave 1
python -m janusm_reads.anchoring /tmp/wave1/manifest.json --out wave1-anchoring.json
```

## Rollback

Set `JANUSM_DISABLE=1` and restart Girder: `/janusm` is gone, everything else is as it
was. To remove it entirely, `pip uninstall girder-janusm`; the `JanusM` collection and
the `janusm_*` Mongo collections stay until someone deletes them on purpose.
