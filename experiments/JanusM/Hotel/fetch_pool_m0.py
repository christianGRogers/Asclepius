"""Job M0, step 1 (the lead runs it): download the Janus-M Round 1 pool volumes from Girder.

Reads janusm_r1_pool_volumes.tsv (made by pool_census.py), re-checks every name against the
coronary guard (D27 seal, A34 reserve, every D35 draft) and refuses the whole run if any is held
out, then downloads each CCTA-Pool item into OUT/<name without .nii.gz>/ct.nii.gz.
The Girder token is read from $GIRDER_TOKEN_FILE and never written anywhere.

Usage (from the repository root):
  GIRDER_TOKEN_FILE=~/.girder_token python experiments/JanusM/Hotel/fetch_pool_m0.py OUT_DIR
"""
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from coronary_holdout import PoolGuard  # noqa: E402

API = os.environ.get("GIRDER_API", "https://janus.bradensbay.com/api/v1")


def main(out: Path) -> None:
    rows = [ln.split("\t") for ln in (HERE / "janusm_r1_pool_volumes.tsv").read_text().splitlines()
            if ln and not ln.startswith("#")]
    guard = PoolGuard()
    bad = [(r[0], guard.reason(r[0])) for r in rows if guard.reason(r[0])]
    print(f"volumes: {len(rows)}; refused (coronary hold-outs): {len(bad)}")
    if bad:
        sys.exit(f"refusing to fetch anything: {bad}")
    import girder_client
    tok = os.environ.get("GIRDER_TOKEN_FILE")
    if not tok:
        sys.exit("set GIRDER_TOKEN_FILE to a file holding a Girder token")
    gc = girder_client.GirderClient(apiUrl=API)
    gc.setToken(Path(tok).expanduser().read_text().strip())
    for name, item_id, *_ in rows:
        dst = out / name.replace(".nii.gz", "")
        if (dst / "ct.nii.gz").exists():
            continue
        dst.mkdir(parents=True, exist_ok=True)
        files = list(gc.listFile(item_id))
        nii = [f for f in files if f["name"].endswith(".nii.gz")]
        if len(nii) != 1:
            print(f"skip {name}: {len(nii)} .nii.gz files in item")
            continue
        gc.downloadFile(nii[0]["_id"], str(dst / "ct.nii.gz"))
        (dst / "done").write_text("pool")
        print("fetched", name, flush=True)


if __name__ == "__main__":
    main(Path(sys.argv[1]))
