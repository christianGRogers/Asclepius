---
aliases: [Annotator proficiency, Training time medical imaging, Learning curves annotation]
tags: [research, annotation, training, non-experts, literature]
status: complete
updated: 2026-09-20
---

# How much training and how fast does annotator agreement improve

The project's annotator pool is a class of undergraduates. [[Can non-experts label vessels as well as experts]] shows that non-experts *can* produce high-quality labels conditional on clear instructions and QA. This note asks the follow-on question: **how much training time is needed before a new annotator reaches acceptable proficiency, and how fast does their agreement improve over time?**

The short answer: **the literature does not provide a generalizable number**, but measured examples show proficiency emerging over ~20–40 examples, with continuous improvement over dozens of cases. However, improvement curves are task- and individual-specific, and no coronary-specific study exists.

## Direct evidence from medical imaging annotation tasks

### Endoscopic procedure annotation: 28–36 procedures to proficiency

**Endoscopic sleeve gastroplasty (ESG) video annotation learning curve study (2024).** The study measured annotator proficiency on video procedure annotation (breaking ESG procedures into phases).

**Finding**: Annotators needed an average of **28.40 procedures** to reach proficiency on the overall task, but individual phases varied: "the other suture phase" required the highest (n = 36), while other phases required fewer.

**Variability**: "The learning process differs among trainees, as mirrored in the variable number of procedures needed to master ESG," ranging from one trainee needing ~20 to another needing ~40+.

**What this tells us**: For a complex multi-step procedure, proficiency emerges over ~25–40 examples. Coronary branch splitting is simpler than full endoscopic procedure annotation, so proficiency might come faster, but the ballpark is 20–40 cases.

### General annotation improvement: F1 scores increase by 6–9 % over iterations

**Training iteration study on annotation task proficiency (2024).** Tracked annotators across multiple rounds on a repeated task.

**Findings**:
- F1 score improvement between training and final iterations: **6.79 % without proposals, 9.19 % with feedback**.
- **Annotation time decreased significantly**: from average 6.56 minutes per task in round 1 to 5.86 minutes in repeated rounds.
- Annotators showed consistent negative slope in annotation time across iterations, indicating they became progressively faster.

**Interpretation**: Accuracy improves by ~7–9 % with repetition and feedback; speed improves by ~10 % (time drops by 0.7 min on ~6.5 min baseline). Modest but consistent gains emerge quickly.

### Inter-annotator agreement divergence by training level

**Skandarani 2021** (cited in [[Can non-experts label vessels as well as experts]]): A briefly-trained non-expert (30 min training) showed 12 % Dice loss on the hard structures (myocardium, RV) compared to an expert; an extensively-trained non-expert (months of training) stayed within measurement noise of the expert. The extensively-trained annotator had had "fine delineation guidelines" and active domain learning, suggesting **training depth, not time alone, drives proficiency**.

## What the literature does NOT say clearly

**No specific paper measures "cases to proficiency for coronary vessel annotation."** The ESG study is the most directly measured (28–40 procedures), but procedures are not cases, and ESG is not vessels.

**No paper tracks inter-annotator agreement *improving over time* as annotators gain training.** The ESG and general-annotation papers measure *performance* (accuracy, speed) but not specifically "did this annotator's Dice against a gold reference increase over their first 50 cases?" — that would be the direct measure needed here.

**No paper measures whether instruction quality (Rädsch's pictures) *reduces the learning curve*.** Rädsch et al. (cited in [[Can non-experts label vessels as well as experts]]) shows pictures reduce catastrophic errors, but do not measure whether annotators trained on pictures reach proficiency faster. Likely they do, but it is not quantified.

## Synthetic extrapolation for coronary branch splitting

Based on the above and the specifics of the coronary task:

**Time to entry-level proficiency**: ~20–30 cases. This assumes a **5-case onboarding gate** (practiced on gold cases, not scored) + **15–25 cases with feedback** before an annotator's scores stop showing large downward variance.

**Justification**: Coronary branch splitting is simpler than ESG (fewer phases), but more complex than flat endoscopic image labeling. The 20–30 figure is between the two.

**Speed improvement**: Annotators should converge on time/case around iteration 10–20, based on the general-annotation study showing ~10 % speed gain over iterations.

**Agreement improvement**: Per-class Dice should improve ~5–10 % between the first scored case and cases 20–30, based on general-annotation improvement rates. This is *not* measured on coronary data; marked as an extrapolation.

**Beyond proficiency**: Improvement likely continues slowly beyond case 30 (learning plateaus slowly, not sharply), but the steepest gains are in the first 20–30.

## What this implies for [[Training plan]]

- **Budget for a 5-case onboarding gate** on gold-standard cases, as SegQueue already does (`src/segqueue/policy.py`). This is below the ~20–30 proficiency threshold, but it screens for "can this person follow instructions at all."
- **Accept case 1–15 from new annotators as lower-quality**, and weight them lower in overlap sets. Variance is high, and agreement-based arbitration should account for this. (Concretely: if a new annotator flags a case for review because it disagrees with a veteran, consider asking a third veteran, not necessarily a tie between the two.)
- **Expect per-class Dice improvement of ~7–10 % between a new annotator's first scored submission and their 20th.** Use this as a baseline for detecting a pathological annotator (one who *doesn't* improve, or who gets worse) vs. normal learning variance.
- **No need for off-line training materials before starting.** The 5-case gate + live feedback on the first 20–30 cases, with clear exemplar images in the guideline (per Rädsch), should suffice. Annotators learn by doing, not in a classroom.
- **Time assumption**: onboarding + proficiency reaches ~3–4 cases/day (35 min/case per CoronaryExplorer benchmark) × 0.67 proficiency (some cases sent for review) ≈ 2 cases/day of credible output by a new annotator in their first month. Experienced annotators are faster if they stay focused.

## What this implies for quality control

- **Track learning curves per annotator.** Store per-class Dice against gold and duplicate references, time-ordered. New annotators should show downward-then-plateau curves; those who stay flat or drift upward (no improvement or worsening) after case 30 are flagged for retraining or removal (see [[Detecting a drifting or bad annotator]]).
- **Do not penalize early-case variance.** A Dice score of 0.75 on case 5 is normal; the same on case 50 is a warning sign. The flag rule should account for case number.
