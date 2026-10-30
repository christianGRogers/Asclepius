# Janus-M paired-scar: the merged JA32 power run

`ja32_power_r2.json` is the output of the one power script (JA35 item 4, #182):

    python -m janusm.scar.power --out experiments/JanusM/Scar/ja32_power_r2.json --sims 400 --boot 400

Simulation only. No image, case or identifier is read or written. The code is `src/janusm/scar/`.
Round 3 re-runs it, and JA28's re-powering re-runs it on development numbers.

- `reproduction`: each Round 2 cell (Golf, Kilo, Juliet) re-run through the merged engine, with
  its committed value and the Monte-Carlo z-score.
- `grid`: power at the JA32 bars for each combination of clustering (weak: patient logit SD 0.7;
  strong: 1.2), enrichment (0.5, 0.7), whole-patient registration failure counted by
  intention-to-diagnose (0, 0.02, 0.05), reader anchor (0.6, 0.7, 0.8; `null` means the anchor is
  below 0.60 and transmurality is reported only) and N.
- `seal_size`: JA28's seal size, max(N at ≥ 80 % joint power, 120, the N for ≥ 270 scarred
  segments). `null` means no N up to 320 reaches 80 % power.
