"""Golf R3: form-entry time for the LGE read form and the registration check form, by the keystroke-level model.

Operators (Card, Moran & Newell 1980, Commun. ACM 23(7):396-410, doi:10.1145/358886.358895):
  M mental preparation 1.35 s; P point with a mouse 1.10 s; B mouse button press or release 0.10 s (a click = BB).
A choice field = M + P + BB; a confirmation = P + BB; moving to the next item adds no M when the layout is fixed.
This is the time to ENTER a read, not to READ the images: image review is clinical judgement that no keystroke
model covers, and it is stated separately as an assumption to be measured on the mock-up with the project's readers.

Scarred-patient segment counts come from the E10 model (k = 1 + Binomial(n_territory - 1, 0.45), mean 3.3).
Usage: python klm_time.py      writes klm_time.json
"""
import json
from pathlib import Path

M, P, B = 1.35, 1.10, 0.10
CHOICE = M + P + 2 * B
CONFIRM = P + 2 * B


def lge_entry(n_pos, n_na=0):
    header = CONFIRM + 3 * CHOICE + CHOICE           # attest, quality, coverage, artefact
    if n_pos == 0 and n_na == 0:
        return header + CONFIRM + M + CONFIRM         # "no LGE in any segment", look at bull's-eye, submit
    neg = 17 - n_pos - n_na
    # presence on every segment; pattern and bin on positive ones; one M per positive segment to judge the share
    return header + neg * (P + 2 * B) + M + n_na * CHOICE + n_pos * (3 * CHOICE + M) + CONFIRM


def reg_entry(fails=0):
    return 3 * CHOICE + fails * (CHOICE + CHOICE) + CONFIRM


if __name__ == "__main__":
    mean_k = sum((1 + 0.45 * (n - 1)) * w for n, w in ((7, 0.5), (5, 0.3), (5, 0.2)))
    out = {"operators_s": {"M": M, "P": P, "B": B},
           "lge_entry_s": {"negative_patient": round(lge_entry(0), 1),
                           "scarred_patient_mean_k": round(lge_entry(round(mean_k)), 1),
                           "scarred_patient_k7": round(lge_entry(7), 1), "mean_k": round(mean_k, 2)},
           "reg_entry_s": {"pass": round(reg_entry(0), 1), "one_slice_fails": round(reg_entry(1), 1)}}
    # per-study entry totals at 160 patients, 60 % scarred, two readers (adjudication not included)
    n, f = 160, 0.6
    entry_h = 2 * n * (f * lge_entry(round(mean_k)) + (1 - f) * lge_entry(0)) / 3600
    out["study_entry_hours_160pt_2readers"] = round(entry_h, 1)
    out["note"] = ("entry time only; image review (assumed 6-10 min per LGE study per reader) dominates and is "
                   "measured on the mock-up")
    (Path(__file__).resolve().parent / "klm_time.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out, indent=1))
