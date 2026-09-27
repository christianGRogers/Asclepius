---
aliases: [Review summary, Ten-agent review]
tags: [review, verification, decision-record]
status: complete
updated: 2026-09-26
repo: Asclepius
---

# Review summary

Ten independent reviews of this vault, run in parallel on 2026-09-26, each given
one slice and instructed to check primary sources rather than trust the vault's
own summary of them. Every load-bearing claim was checked against a paper, a
dataset record, or real source code at a named tag. Nothing in `vault/`, `src/`,
`configs/` or `docs/` was edited by the reviewers.

The reviews are the ten notes beside this one. They are long because they carry
their evidence; this note is the ranked result.

## The verdict

The research is good. The plan is not the most effective one available, and the
plan of record contained errors that had already forked from the code.

Six reviewers converged, without being told to, on the same conclusion: the
project's stated contribution no longer exists, a better one does, and it costs
roughly a tenth of the planned work.

**The failure mode is not rigour, it is routing.** `Research/` is consistently
stronger than [[Proposed changes to the training plan]], which summarises it, and
the things consolidation dropped are the things that change decisions. The
finding that reshapes the project was written down on 2026-09-20, reached
`configs/` and `docs/` the same day, and never reached [[Training plan]].

## What each review found

| Review | The finding that matters most |
|---|---|
| [[The ImageCAS-X finding and the shape of the project]] | The §0 pivot is real and every number checks out — but §0 sends annotators at the 200 scans excluded as non-diagnostic, and §1.4 quotes the one column of ImageCAS-X's table that flatters the plan |
| [[The class schema]] | "Fourteen merges down to four" is false; the Voronoi bifurcation rule is understated ~100×; the taper rule is already decided by both comparator datasets |
| [[Architecture and compute]] | nnU-Net caps the patch at 256³ by construction, so `--gpu-mem 70` buys batch size, fails the plan's own gate (c), and models 77.3 GB on an 80 GB card |
| [[Losses and topology]] | clDice is ruled out on evidence, and there is a third coronary measurement the vault does not have; Skeleton Recall is a vendored fork, not a trainer swap |
| [[Metrics and evaluation]] | The macro-vs-merged aggregation gap is 10.4 points, not 2–5; NSD is unusable at any tolerance; multiple comparisons appear nowhere |
| [[The annotation programme]] | The Sim & Wright sizing is a category error; intersection auto-accept erodes vessels by construction; the seed shipped today is the original mask |
| [[Augmentation and preprocessing]] | The rotation dispute dissolves but the experiment survives for a better reason; mirroring is live at train and test time in this repo |
| [[The code against the plan]] | Phase 1 is not runnable — `convert` cannot read the flat layout `index` now detects — plus four correctness bugs the vault did not find |
| [[Citation integrity]] | One fabricated citation, and it is the only one; the `[reported]` tier carries ~21 % scope/count/attribution errors and near-zero invented numbers |
| [[Red team of the whole plan]] | The contribution claim is refuted by the vault's own §0, and the revised sequence is ~10 % of the planned work |

## Blocking

- **Phase 1 cannot be run.** `src/segtrain/convert.py` derives case paths with the
  nested helpers and never calls the flat scanner, so every case of a flat
  ImageCAS dataset fails at convert. It exits non-zero, so the failure is loud,
  not silent — but it is after a CPU queue wait.
- **Nobody has downloaded ImageCAS-X.** 1.4 GB gates a decision about a term of a
  team's labour, and §1.1, §1.4, §2.1, §2.2 and §2.4 are all conditioned on
  label content nobody has opened.

## The corrections applied

Applied on 2026-09-26 in the commit that added this note's siblings. These were
falsehoods, not decisions, so they did not wait on the strategic review. See
[[Plan status]] for the record.

The 0.856 ceiling, the 12.5 % cascade gate (plan, `README.md`, and the research
note that asserted it was correct), the "labels do not exist yet" premise, the
ASOCA licence, six-versus-eight pretrained baselines, the "<1 %" rare-class
prevalence, the fabricated clDice attribution, three misattributed first authors,
the 1.5 mm resolution claim, the §0/D12 conflict over the excluded 200, and ten
stale repo paths.

## What still needs a decision

Not applied, because they are judgements and not corrections:

1. **The contribution.** The plan's answer is refuted. The reviewers' preferred
   replacement is the first automated per-branch benchmark on ImageCAS-X —
   Bransby et al. released the 14-class labels and never trained a model on
   them, which three reviewers confirmed independently.
2. **`--gpu-mem 70` → 56**, and gate (a) demoted from a gate to a recorded fact,
   since patch fraction is pinned at 23–31 % and cannot be bought with VRAM.
3. **The annotation programme.** Option 1 reshaped (~270–380 h) against Option 2
   from scratch (~1,780–2,750 h). Option 3 costs the same as Option 1 and buys a
   structurally invalid verification.
4. **Stop seeding from the ImageCAS masks**, and drop intersection auto-accept.
5. **What to drop:** run A, the heart-crop run, ResEnc, the elastic ablation,
   TTA, partial-annotation self-training, active learning.

## Two things outside the technical scope

Eighty-four notes contain no occurrence of REB, IRB, ethics, consent,
de-identification or data-use agreement, while a self-hosted copy of a public
dataset is served to student annotators. They also contain no occurrence of
thesis, supervisor, deadline, committee or target venue — so nothing states what
this is for or when it is due, which leaves every sequencing judgement in the
vault unanchored, including the ones above.

## How much to trust this review

Each note ends with what its reviewer could not check. The recurring gaps:
Sim & Wright's Table 8 (which §2.5's whole sizing table rests on) was unreachable
to the reviewer as well as to the original researcher; SCCT's 2014 Appendix 1 and
the 2026 SCCT update were both paywalled; the ImageCAS-X archive itself has still
not been opened by anyone; and roughly 31 DOIs and 40 arXiv ids went unchecked,
concentrated in `Research/Metrics and clinical validation/` and
`Research/Class schema/` — which is where the one fabrication was found.
