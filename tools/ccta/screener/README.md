# Auto screener

The first note on every SegQueue14 case, by the author **auto screener** (project lead, 2026-10-17): an agent
looks at a rendering of the case's TotalSegmentator vessel seed and writes 1-3 sentences on what the annotator can
expect from it (usable / partial / poor, which systems look complete, breaks, stray pieces).

1. `render.py <dir>/png` -- one PNG per seed in `SegQueue/seeds-totalseg`: three depth-shaded projections in RAS
   (from the front, from the patient's right, from above), cropped to the seed, one colour per connected piece,
   plus `<case>.json` with volume, pieces and flag. Skips cases already rendered; retries janus 502s.
2. Agents, one per ~100 cases, each given `AGENT_BRIEF.md`, a case list and an output file
   `<dir>/notes/<batch>.jsonl` (`{"case", "note"}` per line). They read the PNGs; they post nothing.
3. `post.py <dir>` -- posts every note through `POST /segqueue14/notes/auto` (admin). Rerun-safe: a case that
   already has an auto screener note is skipped; cases not in SegQueue14 yet are listed in `pending.txt`.

The screener sees only the seed, not the CT, so its notes describe the mask and hedge on vessel identity.
Paths at the top of the scripts assume this session's layout (`/home/user/ccta/scripts` for `ccta_ingest`,
`GIRDER_TOKEN_FILE` for an admin token); nothing secret is stored here.
