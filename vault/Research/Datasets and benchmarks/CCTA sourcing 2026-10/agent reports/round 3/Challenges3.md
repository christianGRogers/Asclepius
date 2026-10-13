# Round 3, agent Challenges3: challenge platforms (2026-10-13)

Status: in progress.

## Ingested
- **MVAA2026-MitralCT** (CCTA-Pool). MVAA 2026 challenge (MICCAI 2026 MWM workshop, Codabench 15662), Task 1 cardiac CT.
  1,040 unlabeled + 27 labeled training + 30 validation = 1,097 volumes, ~6.4 GB. Licence CC BY-NC (stated on the
  challenge page). Public Google Drive zip, no account. Adapter: `scripts/round3/challenges3_mvaa.py`.
  - Flags: **cropped mitral-valve ROI** (most ~5 cm cube, 0.32-0.36 mm in-plane, 0.5 mm slices; a few larger 1 mm
    crops); coronaries mostly outside the ROI; HU; Guangdong hospitals incl. GDPH (possible ImageCAS patient overlap).
  - 27 labeled cases carry label.nii.gz (mitral valve mask).
  - Upload status: running (~7 cases/min, one stream; re-runs skip uploaded cases).
  - The automatic spine check is meaningless on these crops (bone inside a 5 cm valve ROI is calcium); some cases
    carry orientation_check.spine_posterior=false for that reason. Affines (LAS/RAS) come from the release.

## Needs decision (unclear licence)
- none yet

## Needs account / request
- ASOCA: Microsoft Forms request (https://asoca.grand-challenge.org/access/) - already known.

## Dead ends (checked this round)
- grand-challenge.org API: all 264 hosted challenges, 10 public archives, 16 reader studies. Cardiac CT only
  orCaScore and ASOCA (known, gated); MultiCenterAorta / AortaSeg24 are T3.
- Codabench (all 1,534 public competitions): only MVAA 2026 has cardiac CT.
- EvalAI (1,057 challenges), CodaLab classic, AIcrowd, DrivenData: no cardiac CT.
- MICCAI registered challenges 2020-2026 (miccai.org list): cardiac CT only ASOCA, MVAA, CARE (known); SEG.A and
  Aorta-CTA are T3.
- ISBI challenge pages 2019-2026: no cardiac CT (SegTHOR 2019 is T3).
- Synapse search: no cardiac CT image projects (HeLP 2018/2019 = Korean closed cloud challenges).
- SLAWT 2016 (10 gated CCTA, figshare private links on doc.ic.ac.uk/~rkarim): claimed and ingested by Modelling.
- CVPR 2025 BiomedSegFM (HF junma/CVPR-BiomedSegFM): only repackaged known sets (TotalSeg cardiac, AVT, ImageTBAD),
  uint8.
- MWM 2026 workshop: no other CT challenge.
- Codabench: all 234 medical-looking competitions fetched in full (pages included) and grepped for cardiac CT /
  coronary / TAVI / LAA / congenital: only MVAA.
- grand-challenge algorithms (206): none cardiac CT.
- MM-WHS: maintenance ended, signed agreement + MEGA (known). SIFA/cross-modality 2D MM-WHS slices on GitHub are
  redistributions of MM-WHS (not used). HF AI-CVM/Cardiac-CT (claims MM-WHS test set) is gated (accept conditions).
- ASOCA: now a Microsoft Forms request (asoca.grand-challenge.org/access) - needs request.
- LASC'13 CT: figshare has MRI only; CT was on cardiacatlas.org (Modelling's territory).
- Tianchi, AIcrowd, DrivenData, Zindi: no cardiac imaging competitions found.
- AAPM grand challenges: none cardiac.
- STACOM 2015-2025: CT challenges only SLAWT 2016 (Modelling) and the DTU LAA 2025 labels (ImageCAS duplicate).
