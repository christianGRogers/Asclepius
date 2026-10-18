"""Post the auto screener notes in notes/*.jsonl to SegQueue14 (POST segqueue14/notes/auto, admin). Safe to rerun:
the server skips a case that already has an "auto screener" note. Cases not in SegQueue14 yet (404) are listed in
pending.txt for a later rerun. Usage: GIRDER_TOKEN_FILE=... post.py <screener dir>"""
import glob, json, os, sys, time
sys.path.insert(0, "/home/user/ccta/scripts")
import ccta_ingest
D = sys.argv[1]
p = ccta_ingest.Pool()
created = skipped = missing = failed = 0
pending = []
for f in sorted(glob.glob(os.path.join(D, "notes", "*.jsonl"))):
    for line in open(f):
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        if not row.get("note"):
            continue
        for attempt in range(4):
            try:
                r = p.req("POST", "segqueue14/notes/auto", {"caseName": row["case"], "text": row["note"],
                                                            "author": "auto screener", "once": "true"})
                created += bool(r.get("created")); skipped += not r.get("created")
                break
            except Exception as e:  # noqa: BLE001
                if "HTTP 404" in str(e):
                    missing += 1; pending.append(row["case"]); break
                if attempt == 3:
                    failed += 1; print("FAILED", row["case"], str(e)[:150]); break
                time.sleep(10 * (attempt + 1))
open(os.path.join(D, "pending.txt"), "w").write("\n".join(sorted(set(pending))) + "\n")
print(f"created {created}, already had one {skipped}, not in SegQueue14 yet {missing}, failed {failed}")
