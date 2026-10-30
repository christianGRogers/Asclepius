# Kilo v1: citation check (2026-10-30)

Each reference was opened on PubMed, arXiv, Zenodo, Kaggle or the dataset's own page. The publisher full text
(AHA, NEJM, Elsevier) returned 403 for several, so those numbers come from the PubMed abstract, as marked.
**V** = number seen; **P** = paper found, number not confirmed (not used as a number in Kilo v1).

| # | Reference | DOI / id | Used for | Check |
|---|---|---|---|---|
| 1 | Zhuang X et al. MM-WHS challenge. Med Image Anal 2019;58:101537 | 10.1016/j.media.2019.101537 | 60 CT (20 train labelled, 40 test), 0.78 mm in-plane, coronary CTA protocol (Sec 2.1); CT whole-heart Dice best 0.908, mean 0.872 (Table 3). **No per-structure myocardium CT number in the text** (only Fig. 4 boxplots), so none is cited. MRI myocardium inter-observer Dice 0.811 (Table 6). DUA, no redistribution; maintenance ended | V |
| 2 | Wasserthal J et al. TotalSegmentator. Radiol Artif Intell 2023;5:e230024; arXiv 2208.05868 | 10.1148/ryai.230024 | v1 heart classes; heart labels made by an in-house nnU-Net, "inaccurate for native images" (suppl. S3, limitations); 1.5 mm isotropic; 1082/57/65 split. Dataset Zenodo 6802614 (concept 10.5281/zenodo.6802613), CC BY 4.0. `heartchambers_highres` needs a licence (free non-commercial), 7 classes incl. myocardium, 1559 training images, 0.73×0.72×1.0 mm, val Dice 0.950 (README / task page) | V |
| 3 | Xu X et al. ImageCHD. MICCAI 2020, LNCS 12264:77–87; arXiv 2101.10799 | 10.1007/978-3-030-59719-1_8 | 110 CT, ages 1 month–40 y (mostly < 2 y), 0.25×0.25×0.5 mm; 7 labels incl. myocardium; Kaggle CC BY-NC 4.0 | V |
| 4 | Zreik M et al. Med Image Anal 2018;44:72–85 | 10.1016/j.media.2017.11.008 | Rest CCTA LV myocardium analysis for FFR-significant stenosis: 166 patients; myocardium Dice 0.91, MAD 0.7 mm (20 images); AUC 0.74 ± 0.02 (126 patients) (abstract) | V |
| 5 | van Hamersvelt RW et al. Eur Radiol 2019;29:2350–2359 | 10.1007/s00330-018-5822-3 | Same approach in intermediate stenosis: AUC 0.76 vs 0.68 (abstract) | V |
| 6 | Baskaran L et al. JACC Cardiovasc Imaging 2020;13:1163–1171 | 10.1016/j.jcmg.2019.08.025 | CCTA LV myocardium median Dice 0.920 (IQR 0.811–0.944), 166 patients (abstract) | V |
| 7 | Cerqueira MD et al. AHA 17-segment statement. Circulation 2002;105:539–542 | 10.1161/hc0402.102975 | The 17-segment model and its standard territory assignment (cited as the standard only) | P |
| 8 | Ortiz-Pérez JT et al. JACC Cardiovasc Imaging 2008;1:282–293 | 10.1016/j.jcmg.2008.01.014 | 93 post-MI patients: 23 % of hyperenhanced segments discordant with the standard assignment; no segment 100 % specific for RCA or LCx (abstract) | V |
| 9 | Javadi MS et al. J Nucl Med 2010;51:198–203 | 10.2967/jnumed.109.067488 | Hybrid PET/CT: 72 % of patients (51/71) differ in ≥ 1 segment; 112/1207 segments reassigned (abstract) | V |
| 10 | George RT et al. Circ Cardiovasc Imaging 2009;2:174–182 | 10.1161/CIRCIMAGING.108.813766 | TPR = subendocardial / subepicardial attenuation; CTA+CTP per patient sens 86 %, spec 92 % (40 patients) (abstract). TPR cut-off not confirmed, not used | V |
| 11 | Rochitte CE et al. CORE320. Eur Heart J 2014;35:1120–1130 | 10.1093/eurheartj/eht488 | 381 patients, CTA+CTP AUC 0.87 (0.84–0.91) (abstract) | V |
| 12 | Takx RAP et al. Circ Cardiovasc Imaging 2015;8:e002666 | 10.1161/CIRCIMAGING.114.002666 | CTP vs FFR: vessel sens 0.78 / spec 0.86 (Table 2), patient 0.88 / 0.80 (Table 3) | V |
| 13 | Gerber BL et al. Circulation 2006;113:823–833 | 10.1161/CIRCULATIONAHA.104.529511 | Late-enhancement CT vs CE-MR: segmental concordance 82 % (κ 0.61), size r 0.89 (abstract) | V |
| 14 | Gatti M et al. Eur Radiol 2025;35:3054–3067 | 10.1007/s00330-024-11283-5 | LIE-CT vs LGE-CMR meta-analysis, 14 studies, 526 patients: segment sens 0.86, spec 0.98; patient 0.96 / 0.95; dual-energy segment sens 0.93 (abstract) | V |
| 15 | Nacif MS et al. Radiology 2012;264:876–883 | 10.1148/radiol.12112458 | CT ECV vs MRI ECV r = 0.82, 24 subjects (abstract) | V |
| 16 | Kim RJ et al. N Engl J Med 2000;343:1445–1453 | 10.1056/NEJM200011163432003 | Recovery falls with transmural extent: 78 % with none vs 1/58 with > 75 % (abstract). The quartile bins are used as the common convention; the intermediate bins were not confirmed from the full text | V (bins P) |
| 17 | Shah DJ et al. JAMA 2013;309:909–918 | 10.1001/jama.2013.1381 | Thinning = end-diastolic wall ≤ 5.5 mm; 18 % of thinned regions have limited scar (abstract) | V |
| 18 | Ichikawa Y et al. JACC Cardiovasc Imaging 2009;2:548–555 | 10.1016/j.jcmg.2009.01.010 | LV fat on CT in 62 % of post-MI patients vs 3 % of controls; subendocardial in 94 % (abstract). HU threshold not confirmed, not used | V |
| 19 | Ahn SS et al. AJR 2009;192:532–537 | 10.2214/AJR.08.1608 | Subendocardial fat in 22.4 % of 161 MI patients; mean −29.6 HU on unenhanced CT (abstract) | V |
| 20 | Reimer KA et al. Circulation 1977;56:786–794 | 10.1161/01.cir.56.5.786 | Wavefront: necrosis starts subendocardially and moves outward (abstract) | V |
| 21 | Jones SE et al. Hum Brain Mapp 2000;11:12–32 | 10.1002/1097-0193(200009)11:1<12::AID-HBM20>3.0.CO;2-K | Laplace's equation for thickness / depth between two surfaces | V |
| 22 | Isensee F et al. nnU-Net. Nat Methods 2021;18:203–211 | 10.1038/s41592-020-01008-z | The recipe | V |
| 23 | Kawel N et al. MESA. Circ Cardiovasc Imaging 2012;5:500–508 | 10.1161/CIRCIMAGING.112.973560 | Normal end-diastolic LV wall (CMR), mid-cavity mean 5.3 mm (women) / 6.3 mm (men) (abstract) | V |
| 24 | O'Brien H et al. Front Cardiovasc Med 2021;8:655252 | 10.3389/fcvm.2021.655252 | CT scar detection from shape only, 25 CTA patients with LGE reference: slice AUC 0.901 (abstract) | V |
| 25 | Penso M et al. Front Cardiovasc Med 2023;10:1151705 | 10.3389/fcvm.2023.1151705 | Early-phase CT scar, 50 patients: segment accuracy 71 %, AUC 0.76 (abstract) | V |
| 26 | Muscogiuri G et al. Eur J Nucl Med Mol Imaging 2022;49:3119–3128 | 10.1007/s00259-022-05732-w | DL on CTP vs invasive FFR, 112 patients: AUC 0.98 stress (abstract) | V |
| 27 | Patel AR et al. SCCT CTP consensus. J Cardiovasc Comput Tomogr 2020;14:87–100 | 10.1016/j.jcct.2019.10.003 | Cited as the CTP consensus only; no recommendation attributed | P |
| 28 | CARE 2026 Whole Heart track, zmic.org.cn/care_2026/track_wholeheart | web page | 60/30/54 CT train/val/test with myocardium label; registration closed; no licence stated | V |

**Searched and not found:** any public CT dataset with scar / late-iodine labels, or with CT perfusion images or
labels (only MRI scar sets exist: EMIDEC, MyoPS / CARE-Myocardium); any published deep-learning voxel-wise LIE scar
segmentation validated against LGE.
