# CodeRepos (round 3, 2026-10-13): code hosting that ships CT data

Territory: GitHub (repo search, file listings, release assets, LFS), GitLab.com, Bitbucket, Gitee,
SourceForge, Codeberg, plus the cloud-drive and university-server links that repo READMEs point to.

**Status: done (territory exhausted, 2026-10-13).** Nothing was ingested. Every real cardiac CT volume I found
that a code repository bundles or links carries no licence, so I have listed each under "Needs decision" (3 repos, 6 patients).
The licensed hits were derivatives, MRI, T3 or known duplicates.

## Method and access notes
- `gh api` only works for this session's own repository, and GitHub HTML pages, codeload and the
  REST API return 403 from this sandbox. Search goes through the GitHub MCP server instead
  (`search_repositories` and `search_code` work globally; `get_file_contents` and `list_releases` work
  only for the session repo).
- File listings come from jsDelivr: `https://data.jsdelivr.com/v1/packages/gh/<owner>/<repo>@<branch>?structure=flat`.
  It refuses repos over 50 MB (58 of about 490 scanned). For those I checked `.gitattributes` for LFS
  patterns by raw fetch.
- READMEs come via `raw.githubusercontent.com`. Release-asset downloads (`github.com/.../releases/download/...`) work.
- Public Google Drive works without login. To list a folder: `https://drive.google.com/embeddedfolderview?id=<id>`.
  To download a file: `https://drive.usercontent.google.com/download?id=<id>&export=download&confirm=t`
  (supports Range, so zip members can be read remotely).
- About 490 GitHub repos were scanned: coronary/cardiac CT, centreline, plaque, CAD-RADS, FFR/CFD, TAVI,
  LAA, epicardial fat, congenital, 3D printing, motion, viewers and Chinese-language queries. For each,
  the scan recorded volume-like files, README data links and keywords. Code search was also run for README
  drive/sample-data links and `releases/download` URLs.
- Other hosts:
  - GitLab API project search (about 600 hits): nothing but meshes.
  - Codeberg: nothing.
  - Gitee: connection reset; round 1 already found it a dead end.
  - SourceForge: directory blocked (403); web search found nothing.
  - data.kitware.com (Kitware's public Girder used by VolView, Glance and Slicer; read-only): see dead ends.

## Ingested
None yet.

## Needs decision (licence unclear: real CCTA, not ingested)
1. **BloomingStone/generate_4d_heart** (GitHub, no LICENSE file; Chinese group, RXCA/DSA simulation).
   - The README's test_data is a Google Drive folder, `1vPh2uCSvOnzwjB3b1B62WKwqlZF-wvde`. It holds 2 distinct CCTA volumes
     with cavity and coronary labels:
     - `chest_data/image.nii.gz` (identical to `cta_single/image.nii.gz`): 512x512x305, 0.39x0.39x0.5 mm, HU,
       LA/LV about 540 HU, spine posterior. True CCTA.
     - `chest_data/cta_from_chest/image.nii.gz`: 266x246x328, 0.648x0.648x0.5 mm, a heart crop of a contrast
       chest/cardiac CTA, about 313 HU.
   - Provenance is unstated. It could be from a public set (MM-WHS-like spacing); it is not obviously ImageCAS,
     whose z-size is 206-275.
   - File ids: 1X30Q5FoHtQreNQWA5Bc1HqFBJQWMnb5k, 16zrSeRYPCNBTW_9kQIZV0QUbhEk5T_90.
2. **LzVv123456/Deep-Reinforced-Tree-Traversal** (GitHub, no LICENSE; MICCAI 2021 coronary centreline RL, Rutgers).
   - The README's example_data is a Google Drive file, `1yeJIoBALUGasHyFHAijkNILTtjhwfGXx` (`example_data.zip`, 88 MB).
   - `dataset/toy_data/image_resample.nrrd` holds 1 real CCTA: 500x500x269 at 0.5 mm isotropic (resampled), HU
     (padding -3024), blood pool about 490 HU, plus centreline tree text files. Provenance is unstated.

3. **zhennongchen/Cardiac4DCT_Synth_Diffusion** (GitHub, no LICENSE; Zhennong Chen, UCSD/XJTLU; repo >50 MB).
   - `example_data/nii-images/example_data/example_{1,2}/img-nii-resampled-1.5mm/{0..19}.nii.gz` holds 2 patients x 20
     frames of real ECG-gated cardiac 4DCT. The frames are heart-cropped (111x111x73), resampled to 1.5 mm, in HU, blood pool about 410 HU,
     with the aorta and coronary ostia visible.
   - It is low-resolution T1-style data.
   - Raw URL: `https://raw.githubusercontent.com/zhennongchen/Cardiac4DCT_Synth_Diffusion/main/example_data/nii-images/example_data/example_1/img-nii-resampled-1.5mm/0.nii.gz`.

## Needs account / request
- Baidu-pan-only data links (a Baidu login is needed to download), e.g. Ariel97-star/FFNet-CoronaryArtery-Segmentation
  `pan.baidu.com/s/1M7xL2nylw32livLw_0Ni2g` (contents unknown).
- SimTK sv_tests "Clinical Case: Coronary Normal" (https://simtk.org/projects/sv_tests): SimVascular case with
  image data. A SimTK login is needed to download. It is probably the same case as the VMR coronary models already ingested.

## Dead ends (checked)
- **Other zhennongchen / ucsd-fcrl repos** (13 + 11 scanned):
  - Diffusion_for_CT_motion and CTDenoising example data are head CT.
  - ucsd-fcrl repos hold derived strain/work data and meshes only.
- **brdav/tavr**: its sample is the official MSD Drive mirror (T3).
- **TCIA 4D-Lung** in alexprotom/rust-dicom-station: IDC territory, non-cardiac.
- **Large repos (64 over the jsDelivr 50 MB limit)**: I checked their `.gitattributes` and README example-data mentions. Only
  zeko121, TorontoHeartAtlas and the zhennongchen repos had leads, all covered above.
- **ZihengD/MARVEL_CardiacCT** (Apache-2.0). Its Drive zip `sample_data/058.mat` is a 224x224x96 contrast
  cardiac reconstruction. It is probably an ImageCAS derivative: the same author's TT-U-Net trains on
  motion-simulated ImageCAS, and the case number is 058. Not ingested.
- **MM-DHM/nnUNet-Coronary-CTA-Segmentation** (Apache-2.0). Its "Sample_Dataset" on Drive holds stretched-CPR
  per-vessel volumes, not whole-heart CT.
- **YaoleiQi/PCCAC**: PC-CAC (HF Ryan710/PC-CAC, CC BY 4.0) is point clouds only.
- **SIAT-CT-LAB/Subject-Specific-Deep-Motion-Matching**: only 2D npy slices.
- **Slicer test-data hashes found in code**:
  - 998cb522… (HEaRTmap "RTWorkflow1") is MRI.
  - 1a64f3f4… (FourDimFlow "Angiogram2") is a 4D-flow MRI angiogram.
  - ITK `CTCardioCropped.seq.nrrd` and monai-physio's `TruncalValve_4DCT` are copies of known Slicer samples.
- **data.kitware.com**:
  - Glance `CTACardio.vti` is the known Slicer CTACardio.
  - VolView `CTA-Chest.mha` (512x512x511, 0.86/0.6 mm) is non-gated chest CTA (T3) of unknown origin.
  - "Sample Medical Images/Thorasic CT" is from TCIA.
  - "Trame GWC/heart.nii.gz" is an ex-vivo heart.
- **No cardiac CT volumes** (models, meshes, reports or synthetic data only):
  - sukjulian/coronary-mesh-convolution (surfdrive meshes)
  - Chr1sC0de WSS (SharePoint meshes)
  - TorontoHeartAtlas (STL)
  - multimoda-rs
  - albertozingaro/cfd-mesh (GitLab)
  - Xtaltec/DL-surrogate-CFD-LAA
  - Ziemnono coronary-cfd (synthetic)
  - RvMe/coronary-annotation-studio (synthetic)
  - windrise/3DGR-CAR and Dyna3DGR (toy data)
  - zeko121 stenosis app (LFS `*.nii.gz` pattern but no licence; trained on ImageCAS)
- **Known or duplicate**: Bjonze/Public-Cardiac-CT-Dataset (ImageCAS labels, DTU server), RasmusRPaulsen/CardiacCTExplorer,
  AAOCA, TT-U-Net (ImageCAS), and the gfahrni catalogue (all CT rows known).
