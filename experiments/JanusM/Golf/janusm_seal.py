"""Golf: a proposed Janus-M sealed test, drawn now, before any Janus-M model or read exists.

Population: the 1000 ImageCAS CCTA cases (c0000-c0999; adult, ECG-gated, on Girder `SegQueue/cases` and on Fir as
$SCRATCH/icx4 layout) minus every case the coronary plan has sealed (trillium/icx4/sealed_test.json:
sealed_icx_test 80 + sealed_quality0 20, A14).  The coronary pool seal, reserve and D35 draws are pool volumes, not
ImageCAS cases, so none can enter.  Ranking: sha256('asclepius-janusm-sealed-r1:' + case).  The first 60 are the
Janus-M seal (two team reads of the LV borders each, scored once at a milestone); the next 40 are the Janus-M
decision set (reads decide recipe questions, never trained on); the rest may be trained on.

Usage: python janusm_seal.py   (writes janusm_seal_proposal.json next to this file)
"""
import hashlib, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SALT = "asclepius-janusm-sealed-r1:"
N_SEAL, N_DEC = 60, 40


def main():
    S = json.loads((ROOT / "trillium/icx4/sealed_test.json").read_text())
    coronary_sealed = set(S["sealed_icx_test"]) | set(S["sealed_quality0"])
    assert len(coronary_sealed) == 100
    allowed = [f"c{i:04d}" for i in range(1000) if f"c{i:04d}" not in coronary_sealed]
    rank = sorted(allowed, key=lambda c: hashlib.sha256((SALT + c).encode()).hexdigest())
    seal, dec, rest = rank[:N_SEAL], rank[N_SEAL:N_SEAL + N_DEC], rank[N_SEAL + N_DEC:]
    assert not (set(seal) | set(dec)) & coronary_sealed
    out = {
        "what": "Golf v1 proposal for the Janus-M sealed test and decision set (not binding until the judge and lead adopt it)",
        "salt": SALT, "population": "ImageCAS c0000-c0999 minus trillium/icx4/sealed_test.json sealed_icx_test + sealed_quality0",
        "coronary_sealed_sha256": hashlib.sha256((ROOT / "trillium/icx4/sealed_test.json").read_bytes()).hexdigest(),
        "n_allowed": len(allowed), "janusm_sealed": sorted(seal), "janusm_decision": sorted(dec),
        "n_trainable": len(rest),
        "note": "Janus-M seal cases may also sit in the coronary train/val/open/dev groups; that is allowed (the "
                "coronary model is not scored here), but no Janus-M seal case is ever a Janus-M training or decision case.",
    }
    (Path(__file__).parent / "janusm_seal_proposal.json").write_text(json.dumps(out, indent=1))
    print(f"allowed {len(allowed)}; Janus-M seal {len(seal)}, decision {len(dec)}, trainable {len(rest)}")
    print("seal:", " ".join(sorted(seal)))


if __name__ == "__main__":
    main()
