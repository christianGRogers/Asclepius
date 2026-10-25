# SegQueue14 queue snapshot, 2026-10-25

Pulled read-only from janus by the PM on 2026-10-25 ~20:40 UTC, for the queue-size audit (#126).
Case and file names only: no user names, ids, images or credentials.

| File | Source on janus | Rows |
|---|---|---|
| `segqueue14_queue_2026-10-25.csv` | `GET /api/v1/segqueue14/review/cases`, every page | 675 cases |
| `segqueue_cases_items_2026-10-25.txt` | item names in the Girder folder `SegQueue/cases` | 1304 |
| `segqueue_seeds_items_2026-10-25.txt` | item names in the Girder folder `SegQueue/seeds-totalseg` | 675 |

Server totals at the same time (`GET /api/v1/segqueue14/stats`): 675 cases pending, 0 in progress, 0 complete,
0 retired; reads wanted 1350, approved 0. All 675 cases want 2 reads; none retired; no blind duplicates.
