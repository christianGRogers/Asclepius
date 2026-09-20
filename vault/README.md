# Asclepius vault

An [Obsidian](https://obsidian.md) vault, kept inside the repository so the
reasoning behind the model travels with the code that implements it. Open
Obsidian, choose **Open folder as vault**, and point it at this directory.

Nothing in here is read by the pipeline. It is the *why*: decisions, the
evidence behind them, and what is still open. Anything a script parses belongs
in `configs/`, and anything an operator follows belongs in `docs/`.

## Notes

- **[[Training plan]]** — the method for the multiclass coronary model: what is
  decided, the reasoning, and the evidence. The repository's README carries a
  short summary and points here.
- **[[Plan status]]** — what was removed when the previous plan was retired, and
  where it went. The plan itself is preserved on the `plan-v1` branch.
- **[[Proposed changes to the training plan]]** — everything the literature
  research argues for, in one reviewable set, ordered by what it would change
  and marked by how good its evidence is. Nothing here has been applied to the
  plan. Start with §0: per-branch labels for 800 of the 1000 cases turn out to
  already exist.
- **[[Verification log]]** — which claims in the research were checked against
  full text, which were wrong, and which are still behind a paywall.

`vault/Research/` holds the notes those two summarise: seven topic folders, 84
notes, each carrying its reasoning and its sources.

`[[Research context]]` is linked from the training plan and is deliberately
unresolved: the condensed ImageCAS and nnU-Net notes live outside the
repository. Drop them in as a note of that name and the link resolves.

## Conventions

- One note per subject, titled as a sentence rather than a filename —
  `Training plan`, not `TRAINING-PLAN.md`. The old filenames survive as
  `aliases` in the frontmatter, so links and searches for them still land.
- Link between notes with `[[wikilinks]]`. Link *out* to code as an inline path
  (`configs/tasks/Dataset710_Coronary.yaml`) — a relative link would break in
  one of the two tools.
- Frontmatter carries `tags`, `status` and `updated`. Update `updated` when the
  substance changes, not for a typo.
- Decisions are written with their reasoning and evidence attached. A decision
  recorded without a "why" is a decision nobody can revisit.
