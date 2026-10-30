"""Hotel R2 E1b: are the exact (age, sex, institute, study type) matches to held-out TotalSegmentator subjects
more than chance? Null: 16 non-held-out v1 subjects drawn with the held-out subjects' study types and institutes.
Metadata only (v1 meta.csv).

    python experiments/JanusM/Hotel/r2/e1_chance.py V1_META OUT.json
"""
import json
import random
import statistics as st
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import guard_r2 as g  # noqa: E402


def main(meta, out):
    G = g.Guard()
    m = g.read_meta(meta)
    held = sorted(G.ts_ids)
    key = lambda r: (r["gender"], r["institute"], r["study_type"], r["age"])  # noqa: E731
    cnt = Counter(key(r) for r in m.values())

    def matches(S):
        return sum(cnt[key(m[s])] - 1 - sum(1 for t in S if t != s and key(m[t]) == key(m[s])) for s in S)

    obs = matches(held)
    bytype = {}
    for s, r in m.items():
        if s not in G.ts_ids:
            bytype.setdefault((r["study_type"], r["institute"]), []).append(s)
    rng = random.Random(1)
    sims = []
    need = Counter((m[h]["study_type"], m[h]["institute"]) for h in held)
    for _ in range(2000):  # without replacement within each (study type, institute) stratum
        S = [s for k, n in need.items() for s in rng.sample(bytype[k], n)]
        sims.append(matches(S))
    res = {"observed_exact_matches": obs, "chance_mean": round(st.mean(sims), 2),
           "chance_p95": sorted(sims)[int(.95 * len(sims))],
           "p_ge_observed": round(sum(x >= obs for x in sims) / len(sims), 3), "n_sims": len(sims),
           "null": "16 non-held-out v1 subjects drawn with the held-out subjects' study types and institutes"}
    Path(out).write_text(json.dumps(res, indent=1) + "\n")
    print(res)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
