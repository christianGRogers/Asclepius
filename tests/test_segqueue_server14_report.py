"""``segqueue14-report quality`` (#296): the read-only annotation quality report.

The report as a whole against a real Girder and MongoDB (``needs_mongo``, through
``test_segqueue_server14``'s fixtures, run in CI's server job, which refuses skips;
the figures alone are ``test_segqueue14_quality.py``'s), on a synthetic pool
written straight into the database: two two-read cases with stored pair scores,
an untrimmed read, an overlapping read, empty classes, a flagged read, a
reviewer's revision, a rejection, and a benchmark read that must count nowhere in
the pool figures. And the database and assetstore are the same afterwards.
"""

import datetime
import hashlib
import os
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import test_segqueue_server14 as base  # noqa: E402

pytestmark = pytest.mark.needs_mongo

NAMES = ["LM", "LAD", "LCx", "RCA"]


# ------------------------------------------------------- against the database


# The same scratch database and miniature world as test_segqueue_server14.py.
girder_db = base.girder_db
world = base.world


def _now(minutes):
    return datetime.datetime(2026, 11, 1, tzinfo=datetime.timezone.utc) \
        + datetime.timedelta(minutes=minutes)


def _build(world):
    """The synthetic pool. Returns ``{name: id}`` of what the assertions need."""
    import numpy as np
    from girder.models.folder import Folder
    from girder_segqueue14.models import Assignment14, Case14, Review14, Submission14
    from girder_segqueue14.utils import incomingFolder

    admin, people = world.admin, world.people
    folder = Folder().createFolder(incomingFolder(admin), "report-test", parentType="folder",
                                   creator=admin, reuseExisting=True)
    tree = base._tree(np)                           # x, y, z
    classes = {name: (tree == i + 1).astype(np.uint8) for i, name in enumerate(NAMES)}
    seedArr = (tree > 0).astype(np.uint8)

    def case(name, replicas=1, seeded=True, benchmark=False):
        base._nifti(world.data / f"{name}.nii.gz", np.full((24, 24, 24), 100, np.int16))
        seedFile = None
        if seeded:
            seedFile = base._upload(base._nifti(world.data / f"{name}.seed.nii.gz", seedArr),
                                    folder, admin)
        return Case14().createCase(
            name, fileId=None, checksum="", sizeBytes=0, replicasWanted=replicas,
            seedFileId=seedFile["_id"] if seedFile else None,
            extra={"benchmark": True, "benchmarkPending": []} if benchmark else None)

    ids = {}

    def read(key, c, login, masksByName, state, minutes, seconds=600.0, score=None,
             kind="paired"):
        user = people[login]
        masks = base._stackOf(np, masksByName)
        fileDoc, _ = base._uploadStack(world, user, c["name"], masks)
        a = Assignment14().collection.insert_one({
            "caseId": c["_id"], "userId": user["_id"], "state": state, "kind": kind,
            "attempt": 1, "assignedAt": _now(minutes - 30)}).inserted_id
        s = Submission14().collection.insert_one({
            "assignmentId": a, "caseId": c["_id"], "userId": user["_id"],
            "authorRole": "annotator", "revisionOf": None, "kind": kind,
            "fileId": fileDoc["_id"], "annotationSeconds": seconds,
            "voxelCounts": {n: int(m.sum()) for n, m in zip(NAMES, masks)},
            "labelFormat": "class-stack-nrrd/1", "scored": True, "autoScore": score,
            "created": _now(minutes)}).inserted_id
        ids[key] = {"assignment": a, "submission": s, "case": c}
        return s

    def pair(mean, perClass, partner, flags=()):
        return {"flags": list(flags), "against": ["second-read"],
                "duplicate": {"mean_dice": mean, "partnerSubmissionId": str(partner),
                              "per_structure": {n: {"dice": d} for n, d in perClass.items()}}}

    a = case("pool_a", replicas=2)
    b = case("pool_b", replicas=2)
    c = case("pool_c")                               # never read; cathy holds it
    Assignment14().collection.insert_one({
        "caseId": c["_id"], "userId": people["cathy"]["_id"], "state": "assigned",
        "kind": "normal", "attempt": 1, "assignedAt": _now(65)})
    d = case("pool_d", replicas=1)
    bench = case("annotator_benchmark_0001", benchmark=True)

    # pool_a: anna sent the seed back untouched; bobby trimmed it. Low pair Dice.
    untouched = {n: seedArr for n in NAMES}
    lowFlag = ["mean Dice 0.40 against the other read (< 0.60)"]
    sa = read("anna_a", a, "anna", untouched, "approved", 10, seconds=120.0)
    sb = read("bobby_a", a, "bobby", classes, "submitted", 20, seconds=900.0)
    lowPair = {"LM": 0.3, "LAD": 0.4, "LCx": 0.4, "RCA": 0.5}
    Submission14().collection.update_one({"_id": sa}, {"$set": {"autoScore": pair(
        0.40, lowPair, sb, lowFlag)}})
    Submission14().collection.update_one({"_id": sb}, {"$set": {"autoScore": pair(
        0.40, lowPair, sa, lowFlag)}})

    # pool_b: anna leaves LM empty and LAD inside LCx too (overlap); cathy agrees well.
    overlap = dict(classes, LM=np.zeros_like(seedArr), LCx=classes["LCx"] | classes["LAD"])
    good = {"LM": 0.8, "LAD": 0.9, "LCx": 0.9, "RCA": 1.0}
    sc = read("anna_b", b, "anna", overlap, "rejected", 30, seconds=300.0)
    sd = read("cathy_b", b, "cathy", classes, "approved", 40, seconds=400.0)
    Submission14().collection.update_one({"_id": sc}, {"$set": {"autoScore": pair(
        0.90, good, sd)}})
    Submission14().collection.update_one({"_id": sd}, {"$set": {"autoScore": pair(
        0.90, good, sc)}})
    Review14().collection.insert_one({
        "submissionId": sc, "assignmentId": ids["anna_b"]["assignment"], "caseId": b["_id"],
        "annotatorId": people["anna"]["_id"], "reviewerId": people["revy"]["_id"],
        "verdict": "reject", "comment": "LM missing", "created": _now(45)})

    # pool_d: bobby's one read has no RCA, flagged; revy revised it.
    noRca = dict(classes, RCA=np.zeros_like(seedArr))
    se = read("bobby_d", d, "bobby", noRca, "under_review", 50, seconds=700.0, kind="normal",
              score={"flags": ["required class empty in the uploaded file: RCA"],
                     "against": []})
    revFile, _ = base._uploadStack(world, people["revy"], "pool_d", base._stackOf(np, classes))
    Submission14().collection.insert_one({
        "assignmentId": ids["bobby_d"]["assignment"], "caseId": d["_id"],
        "userId": people["revy"]["_id"], "authorRole": "reviewer", "revisionOf": se,
        "kind": "normal", "fileId": revFile["_id"], "annotationSeconds": 60.0,
        "voxelCounts": {}, "scored": True, "autoScore": None, "created": _now(55)})

    # The benchmark: cathy's untouched, flagged, empty read must count nowhere in the pool.
    read("cathy_bench", bench, "cathy", {n: seedArr if n != "RCA" else np.zeros_like(seedArr)
                                         for n in NAMES},
         "submitted", 60, seconds=5.0, kind="benchmark",
         score={"flags": ["mean Dice 0.10 against ImageCAS-X (< 0.50)"], "benchmark": True,
                "against": ["imagecas-x"],
                "reference": {"mean_dice": 0.1, "per_structure": {}}})
    return ids


def _snapshot(world):
    """Every document in the database, the indexes, and the assetstore's files."""
    from girder.models.assetstore import Assetstore

    db = world.db
    docs = {name: sorted(map(str, db[name].find({})))
            for name in sorted(db.list_collection_names())}
    indexes = {name: sorted(db[name].index_information()) for name in docs}
    root = Assetstore().findOne()["root"]
    files = {}
    for dirpath, _, names in os.walk(root):
        for n in names:
            p = os.path.join(dirpath, n)
            files[p] = hashlib.sha256(Path(p).read_bytes()).hexdigest()
    return docs, indexes, files


def test_the_quality_report_on_a_synthetic_pool(world):
    # Imported here, not at collection: importing Girder binds its database, and the
    # fixtures bind it to the scratch one first.
    from girder_segqueue14 import report

    pool = world
    ids = _build(pool)
    before = _snapshot(pool)
    lines = []
    got = report.runQuality(limit=50, out=lines.append, db=pool.db)
    assert _snapshot(pool) == before, "the report wrote something"

    people, totals, eye = got["annotators"], got["totals"], got["eye"]
    zero = {s: 0 for s in ["assigned", "downloaded", "submitted", "under_review", "approved",
                           "rejected", "released"]}
    # Reviewers' revisions are not reads; the benchmark read is not a pool read.
    assert set(people) == {"anna", "bobby", "cathy"}
    anna, bobby, cathy = people["anna"], people["bobby"], people["cathy"]
    assert (anna["reads"], anna["approved"], anna["sentBack"], anna["underReview"]) == (2, 1, 1, 0)
    assert (bobby["reads"], bobby["approved"], bobby["underReview"], bobby["revisedByReviewer"]) \
        == (2, 0, 2, 1)
    assert (cathy["reads"], cathy["approved"], cathy["underReview"]) == (1, 1, 0)
    assert anna["medianSeconds"] == 210.0 and cathy["medianSeconds"] == 400.0

    # Pairs, from the stored scores.
    assert anna["pairs"]["n"] == 2 and anna["pairs"]["mean"] == 0.65
    assert (anna["pairs"]["min"], anna["pairs"]["max"], anna["pairs"]["below"]) == (0.4, 0.9, 1)
    assert anna["pairs"]["perClass"] == {"LM": 0.55, "LAD": 0.65, "LCx": 0.65, "RCA": 0.75}
    assert bobby["pairs"]["n"] == 1 and bobby["pairs"]["below"] == 1
    assert cathy["pairs"]["median"] == 0.9 and cathy["pairs"]["below"] == 0
    assert totals["pairsScored"] == 2

    # Flags.
    assert anna["flagged"] == 1 and anna["flags"]["low pair Dice"] == 1
    assert bobby["flagged"] == 2 and bobby["flags"]["empty required class"] == 1
    assert cathy["flagged"] == 0, "the benchmark's flag is not a pool flag"

    # Seeds: anna's pool_a read is the seed in all four classes.
    assert anna["untrimmed"] == 1 and anna["copies2"] == 1
    assert bobby["untrimmed"] == 0 and cathy["untrimmed"] == 0
    assert eye["likelyUntrimmed"] == [{"case": "pool_a", "login": "anna",
                                       "classes": NAMES}]
    rows = {(r["case"], r["login"]): r for r in got["reads"]}
    assert rows[("pool_a", "anna")]["kept"] == {n: 1.0 for n in NAMES}
    trimmed = rows[("pool_a", "bobby")]["kept"]
    assert all(0 < v < 0.5 for v in trimmed.values()) and abs(sum(trimmed.values()) - 1) < 1e-3

    # Overlap: all four classes in anna's untrimmed read; LAD in LCx in her pool_b read.
    assert rows[("pool_a", "anna")]["overlapFraction"] == 1.0
    assert 0 < rows[("pool_b", "anna")]["overlapFraction"] < 1
    assert rows[("pool_b", "cathy")]["overlapFraction"] == 0.0
    assert anna["overlapReads"] == 2 and cathy["overlapReads"] == 0
    assert [r["case"] for r in eye["mostOverlap"]][:2] == ["pool_a", "pool_b"]

    # Empty classes.
    assert anna["empty"] == {"LM": 1, "LAD": 0, "LCx": 0, "RCA": 0}
    assert bobby["empty"] == {"LM": 0, "LAD": 0, "LCx": 0, "RCA": 1}
    assert cathy["empty"] == {n: 0 for n in NAMES}

    # Totals: pool_c unread, pool_d once, pool_a and pool_b twice; the benchmark is not a
    # pool case.
    assert (totals["cases"], totals["reads0"], totals["reads1"], totals["reads2"]) == (4, 1, 1, 2)
    assert totals["reads"] == 5 and totals["analysed"] == 5
    assert eye["lowestPairDice"][0] == {"case": "pool_a", "logins": ["anna", "bobby"],
                                        "meanDice": 0.4}
    assert "annotator_benchmark_0001" not in str(got["reads"])

    # The text: the tables, the list, and the benchmark table at the end, case names and
    # logins only, within the step summary's lines.
    text = "\n".join(lines)
    assert len(lines) <= report.MAX_LINES
    assert "low pair Dice 0.40: pool_a (anna, bobby)" in text
    assert "likely untrimmed (LM, LAD, LCx, RCA keep the seed): pool_a (anna)" in text
    assert "Benchmark (segqueue14-benchmark status)" in text
    tail = text.split("Benchmark (segqueue14-benchmark status)")[1]
    assert "annotator_benchmark_0001" in tail and "cathy" in tail
    assert ".nrrd" not in text and ".nii" not in text

    # --limit: no files opened; empty classes then come from the stored counts.
    small = report.runQuality(limit=0, out=lambda _: None, db=pool.db)
    assert small["totals"]["analysed"] == 0 and small["annotators"]["anna"]["untrimmed"] == 0
    assert small["annotators"]["bobby"]["empty"]["RCA"] == 1
    newest = report.runQuality(limit=1, out=lambda _: None, db=pool.db)
    assert newest["totals"]["analysed"] == 1
    assert [r["case"] for r in newest["reads"] if "counts" in r] == ["pool_d"]
    assert ids["bobby_d"]["submission"]

    # Assignments by state, and approvedCount against the approved assignments: the
    # synthetic cases were never counted (approvedCount 0), two have an approved read.
    states = got["assignmentStates"]
    assert states["anna"] == dict(zero, approved=1, rejected=1)
    assert states["bobby"] == dict(zero, submitted=1, under_review=1)
    assert states["cathy"] == dict(zero, approved=1, assigned=1), "the benchmark is left out"
    assert states["all"] == dict(zero, assigned=1, submitted=1, under_review=1, approved=2,
                                 rejected=1)
    assert got["approvedCount"] == {"mismatches": 2, "examples": [
        {"case": "pool_a", "approvedCount": 0, "approvedAssignments": 1},
        {"case": "pool_b", "approvedCount": 0, "approvedAssignments": 1}]}
    assert "approvedCount check: 2 pool case(s)" in text and "pool_a (0 vs 1)" in text
    assert "Assignments by state (pool)" in text

    js = report.runQuality(limit=5, asJson=True, out=lambda _: None, db=pool.db)
    assert js["benchmark"]["case"] == "annotator_benchmark_0001"
    assert _snapshot(pool) == before
