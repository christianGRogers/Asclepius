---
aliases: [Foxtrot j1l round-2 tools]
tags: [plans, experiment, janus1-L, D45, tf1, width, threshold, cpu, tool]
status: built and self-tested (CPU, 2026-11-15); results wait on Job 0 and Job 0b
issue: christianGRogers/Asclepius#302
track: 1-L
---

# A tuning-60 error decomposition and a label-free check that t\* transfers, both self-tested and waiting on Job 0

Two questions from [[Janus 1-L Round 1]] §5 need Job 0's outputs, which do not exist yet. This note gives the method,
the code, the self-tests and the lead's commands. It gives no results.

Code: `experiments/Foxtrot/j1l_r2/`. Both scripts run on CPU. Neither reads a locked-100 label or score, or a sealed
case.

## 1. Where Janus 0 loses tF1 on the tuning 60 (§5 item 5)

**Question.** Does LCx (and every other class) lose its tree-F1 to **breaks**, **naming** or **extent**? The answer
decides whether a topology arm (e.g. Skeleton Recall), a naming arm or an extent arm is worth a GPU run in a later
round (Bridge v1 §7).

**Method** (`error_decomp.py`). Each case is scored exactly as the decisive score:
- icx4's `tf1_score` conventions: the 15 mm crop, A1 ostia from the TotalSegmentator aorta with the CT
  cross-check, D3's 1.5 mm;
- the frozen metric, loaded only after its A1c hash check;
- flagged trees apart, provisional cases out.

Then every reference centreline point that tF1 counts as not recalled goes in exactly one bin, and so does every
predicted centreline point that it counts as not precise:

| Side | Bin | Meaning | Lever it points to |
|---|---|---|---|
| Recall | `hit` | Named right and rooted (what recall counts) | — |
| Recall | `cut` | Named right, in a piece the ostium does not reach | Breaks (connectivity, topology loss) |
| Recall | `gap` | Not drawn, in a missed run with drawn centreline on both sides | Breaks (a hole) |
| Recall | `misnamed` | Drawn as another vessel class | Naming (namer, class weights) |
| Recall | `extent` | Not drawn, in a missed run that reaches a vessel end (a distal end or a whole side branch) | Extent (threshold, extent arm) |
| Precision | `correct` | Inside the right reference class (what precision counts) | — |
| Precision | `misnamed` | Inside another reference class | Naming |
| Precision | `outside` | Outside the reference | Overshoot, a vein, an FP piece |

- **The bins reproduce the metric exactly.** `hit / n` equals the frozen `tree_f1` recall and `correct / m` its
  precision, for every case and class. The script asserts this on every tree, on real data too.
- **Counterfactuals.** For each tree it reports the tF1 gain if one kind of error were removed and nothing else
  changed: breaks fixed, naming fixed, extent fixed, overshoot gone. The per-class means of these gains are the
  answer.
- **Cases:** the tuning 60 only. Any other id is refused.

**Self-test** (`python error_decomp.py --selftest`; synthetic trees from `r9_score_icx4.py`). It passes:

| Synthetic error | Bin it lands in |
|---|---|
| Perfect tree | All hit, all correct |
| 3 mm hole across the LAD | cut 0.64, gap 0.11, extent 0 |
| LCx drawn as LAD | misnamed 1.0 (LCx); LAD precision misnamed > 0.3 |
| RCA's distal 12 mm not drawn | extent 0.23, cut 0, gap 0 |
| A vein-like tube beside the RCA | outside 0.31, recall untouched |

**How round 3 reads it** (fixed now, before the numbers exist; "gain" is the macro mean tF1 gain on the decisive
trees of the tuning 60, at argmax and at t\*):

| Result | Then |
|---|---|
| Breaks-fixed gain ≥ 0.02 for LCx or macro, and larger than the naming and extent gains | A connectivity arm earns a run in a later round (Skeleton Recall, with BCS's warning on disconnected components, arXiv:2607.28327, as the risk to guard) |
| Naming-fixed gain ≥ 0.02 and the largest | A naming arm (the namer, or class-weighted CE for the weak class) |
| Extent-fixed gain the largest | The threshold already acts on it. Compare the argmax and t\* rows; no new arm until a1 is read |
| Every gain < 0.01 | No arm is worth a run on this evidence. Janus 1-L stays the plan as is |

## 2. Does t\* transfer from Janus 0 to a Janus 1-L network? (§5 item 3)

**The problem.** Rule W chooses t\* on Janus 0's probabilities for the tuning 60, which Janus 1-L then trains on. No
labelled ImageCAS-X case is left outside the locked 100. So the transfer cannot be checked against labels before the
look.

**What can be checked: how much each network draws, on images no model trained on.**
- **The images** (`calib_cases.py` → `results/calib60.json`, sha256 of the sorted ids `415c62ce…8345`):
  - ImageCAS's quality-0 group, the 200 cases ImageCAS-X did not label. They are derived here from ids alone (1000
    minus D45's 620 and 100 minus the sealed 80), and the derivation checks that the sealed quality-0 20 and the 24
    declared-development cases are inside it;
  - the sealed 20 and the 24 development cases are dropped;
  - the 60 with the smallest `sha256('asclepius-j1l-calib:' + id)` are taken.
  - No label of any kind is read for them, nothing trains on them, and none is in the 620, the locked 100 or a
    sealed list (asserted).
- **The statistic** (`t_transfer.py`):
  - f = summed vessel probability, and V(t) = the number of voxels with f ≥ t, per case;
  - **target:** Janus 0's V(t\*) on each case;
  - **t_C:** the t on Rule W's grid {0.30 … 0.50} whose median ratio V_C(t) / V_J0(t\*) is closest to 1. Ties go to
    the t nearest t\*, then to the larger t;
  - **shift s** = median V_C(t\*) / V_J0(t\*).
- **The switch, pre-registered:** the candidate is exported at t_C if |t_C − t\*| ≥ 0.10 (two grid steps), else at
  t\*. The choice is written to `transfer.json`, and its sha256 is posted on #302 before any locked-100 number of the
  candidate is computed.

**Why volume and not a threshold.** Rule W in effect chose a width: the one with the best Dice on 60 labelled cases.
What should transfer is that width, not the number t\*:
- if a1 is sharper than Janus 0 (more confident on the rim), t\* draws less for it than for Janus 0, and the Dice gain
  is lost; volume matching lowers t;
- if a1 has widened by itself, t\* over-draws and adds FP; volume matching raises t;
- if nothing changed, t_C = t\*.

**Caveats.**
- Quality-0 images are worse images than ImageCAS-X's. The statistic is a ratio between two networks on the
  same images, which cancels much of that, but not all.
- Volume includes any FP piece. A candidate with more FP volume would be thinned slightly; the H1 FP guard still
  binds.

**Self-test** (`python t_transfer.py --selftest`; synthetic tubes with sigmoid rims). It passes: an identical network
keeps t\* = 0.40; a network drawn 1 voxel wider is moved to 0.50 (s = 1.64); a sharper one with the same boundary is
moved to 0.30 (s = 0.82).

**Cost.** Janus 0 on the 60 images: Job 0b, about 1 GPU-h (`job0b_calib_volumes.sh`; only volume tables are kept).
Each Janus 1-L network on the same 60: about 0.5 GPU-h, inside the E job.

## 3. What it changes

- [[Candidates/Janus 1-L/Foxtrot v2|Foxtrot v2]] §3 adopts the switch as the pre-registered alternative to a frozen
  t\*, and §5 adopts the error decomposition as the 60-case analysis.
- No decision is taken from either before Job 0 has run.
