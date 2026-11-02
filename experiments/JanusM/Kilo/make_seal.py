"""Kilo v1: the proposed Janus-M seal (all adult, gated, good-grid CCTA patients free for Janus-M; E0).

Population: Taiwan-AICUP-CardiacCT patients in allowed_volumes.json (not coronary-sealed, not reserve, not in any
D35 draw). All of them are sealed for Janus-M, so no draw is needed; the order is sha256(salt + patient) for
reporting only. Not binding until the judge adopts it.  Usage: python3 make_seal.py
"""
import hashlib, json, os

HERE = os.path.dirname(os.path.abspath(__file__))
SALT = "asclepius-janusm-seal-r1:"
a = json.load(open(os.path.join(HERE, "allowed_volumes.json")))
vols = [v for v in a["volumes"] if v["source"] == "Taiwan-AICUP-CardiacCT"]
pats = sorted({v["patient"] for v in vols}, key=lambda p: hashlib.sha256((SALT + p).encode()).hexdigest())
out = {"what": "Kilo v1 proposal for the Janus-M seal (not binding until the Round 1 judge adopts it)",
       "salt": SALT, "allowed_volumes_sha256": hashlib.sha256(open(os.path.join(HERE, "allowed_volumes.json"), "rb").read()).hexdigest(),
       "coronary_seal_sha256": a["seal_sha256"], "n_patients": len(pats),
       "patients": pats, "volumes": sorted(v["name"] for v in vols),
       "rule": "every volume of every listed patient is withheld from Janus-M training, tuning and seed edits; scored once at acceptance"}
p = os.path.join(HERE, "janusm_seal_proposal.json")
json.dump(out, open(p, "w"), indent=1)
print(len(pats), "patients", hashlib.sha256(open(p, "rb").read()).hexdigest())
