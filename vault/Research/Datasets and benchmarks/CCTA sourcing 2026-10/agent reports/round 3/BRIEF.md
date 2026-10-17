# CCTA sourcing, round 3 (2026-10-13): keep finding AND ingesting, until you run out

Project lead: "continue the subagents searching for new CCTAs until they max out the usage". Ten agents run
in parallel, each with its own territory. Work exhaustively: when your territory is done, widen to adjacent
corners of it; stop only when you truly find nothing new.

## Scope (decided by the project lead)
- **Cardiac-focused only.** T1 ECG-gated CCTA, T2 other contrast cardiac CT with coronaries visible.
  NOT T3 (non-gated chest/aortic CTA, CTPA), NOT non-contrast, NOT MRI/X-ray/echo, NOT animal data.
- Quality bar is low ("don't be too strict on quality"). Low-res, cropped or 8-bit is fine — flag it.
- **Immediate download only.** No request, DUA, approval or account creation. Never create accounts, sign,
  or submit forms. If a source needs one, record it (name + URL + what is needed) and move on.
- Licence: open licences (CC*, CC0, ODbL, public domain, permissive code licences) → ingest.
  **No licence stated / unclear → do NOT ingest**; record it under "needs decision" (the lead decides).

## Already known — do not re-report or re-ingest
Read /home/user/ccta/vault/Research/Datasets and benchmarks/CCTA sourcing 2026-10/ (summary + agent
reports, incl. "agent reports/round 2/"). Also already ingested in Girder CCTA-Pool: IDC RIDER/NSCLC/
VAREPOP, Kaggle CAD-RandomSamples, HeartSR, VMR coronary, Figshare 1379059, Mendeley 9wv3fkxstx, HOCM,
ImageALCAPA, ImageCHD, TotalSegmentator v2 cardiac (130), Mendeley SDN (cy54ttk3fj, 7x9kb53262,
37nnfyh3x9, 4643nn2z44, spb25zt2c4), Figshare 17039813 epicardial CE, Figshare 23057000, Zenodo 21855641,
Zenodo 22127731 STOPSTORM, Slicer/SlicerHeart samples (TruncalValve_4DCT, CTACardio, PDA_CT, CTCardioSeq),
Taiwan AI CUP (HF benchang1110/cardiac_segmentation; being ingested now). ImageCAS and every derivative.

## Coordination (shared by all ten agents)
`/tmp/claude-0/-home-user-Asclepius/1b43aea1-ed14-5dd0-84ee-25f776047e09/scratchpad/sourcing/round3/CLAIMS.tsv`.
Before you work on a source, check it is not listed, then append one line
`<source_key>\t<YourName>\t<status>\t<note>` using an atomic append under a lock:
`flock CLAIMS.tsv.lock -c 'grep -q "^KEY\t" CLAIMS.tsv || printf "KEY\tName\tingesting\tnote\n" >> CLAIMS.tsv'`
(then re-read to confirm the line is yours). source_key = canonical URL or DOI, lower-case. Update status
when done (append a new line; last line wins).

## Ingesting (upload to Girder)
- Use the existing library: /home/user/ccta/tools/ccta/ccta_ingest.py (Pool) and helpers in
  /home/user/ccta/tools/ccta/ingest_open.py (HTTPFile range reader, kaggle helpers, dicom_extra,
  anatomy_check, retrying _open, Sink). Read them first. Write YOUR adapter code ONLY in
  /home/user/ccta/tools/ccta/round3/<yourname>_<source>.py (import from ../ via sys.path). Never edit other
  files. Never run git.
- Token: `export GIRDER_TOKEN_FILE=/tmp/claude-0/-home-user-Asclepius/1b43aea1-ed14-5dd0-84ee-25f776047e09/scratchpad/secrets/.girder_token`
  — never print it or copy it anywhere.
- Upload only into the collection CCTA-Pool via Pool.dataset/Pool.ingest (one dataset folder per source,
  with licence, tier, source_url, citation; each case: source ids + non-identifying acquisition metadata).
  Never touch any other Girder collection, never delete anything (the server cannot delete folders —
  create a dataset folder only when you are about to upload real cases).
- Check the first case of every source before the rest: save a preview PNG, view it, confirm contrast
  heart and orientation; fix spacing units / HU offsets / axis order if needed; non-HU sources: upload
  as released and set hu_calibrated=false (the orchestrator converts them later).
- Multi-phase series: one case per phase, patient_id in extra. Never store names, birth dates, exam dates,
  accession numbers, or contact details of dataset owners.
- **Disk:** local disk is small and shared by ten agents: never hold more than 600 MB at once; use your own
  work dir `round3/work_<YourName>/` and delete as you go. Re-runs must skip cases already uploaded.
- Be polite to servers: one download stream at a time.

## Deliverable
Keep `round3/<YourName>.md` up to date as you go: ingested (dataset folder, cases, GB), needs decision
(unclear licence), needs account/request (name, URL, what is needed), dead ends. When you finish, return a
short final report. Today is 2026-10-13.
