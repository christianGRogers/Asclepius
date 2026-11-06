"""The annotator benchmark (D43, #286) against a real Girder and MongoDB.

Marked ``needs_mongo`` (through ``test_segqueue_server14``'s fixtures) and run in
CI's server job, which refuses skips. Synthetic data only: a miniature ImageCAS-X
collection holding the drawn case and the next one in draw order, beside the
miniature project ``test_segqueue_server14.world`` builds.

What is checked is the issue's acceptance list: the pick is the project's own,
deterministic and reused; the case is next only for the annotators assigned it and
never for an excluded one; pool serving is unchanged for everyone else; a
submission lands in review with its reference Dice and no pair score; a retest is a
fresh attempt and both scores are kept; and no export takes its reads.
"""

import json
import os
import stat
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import test_segqueue_server14 as base  # noqa: E402
from test_segqueue_server14 import (  # noqa: E402  (helpers)
    _as,
    _icx,
    _nifti,
    _readyProject,
    _refusal,
    _resource,
    _submit,
    _tree,
    _upload,
)

# The same scratch database and miniature project as test_segqueue_server14.py.
girder_db = base.girder_db
world = base.world

pytestmark = pytest.mark.needs_mongo

#: The project's draw (``test_segqueue14_benchmark``) and the next case in draw order.
PICK, NEXT = 855, None


def _drawOrder():
    from janusm import guard
    from segqueue14 import benchmark as b

    g = guard.load_guard(REPO)
    splits = json.loads((REPO / "trillium-results/icx14/results/splits.json").read_text())
    sealed = json.loads((REPO / "trillium/sealed_test.json").read_text())
    e = b.eligibility(splits, sealed, lambda c: g.reason(c, source="ImageCAS-X"))
    return [b.imagecas_id(c) for c in e.eligible[:2]]


@pytest.fixture
def bench(world):
    """ImageCAS-X with the first two cases in draw order, and an empty seed folder."""
    import numpy as np
    from girder.models.collection import Collection
    from girder.models.folder import Folder
    from girder.models.item import Item

    first, second = _drawOrder()
    assert first == PICK
    admin = world.admin
    icx = Collection().createCollection("ImageCAS-X", creator=admin, public=False)
    cases = Folder().createFolder(icx, "cases", parentType="collection", creator=admin)
    labels = Folder().createFolder(icx, "labels", parentType="collection", creator=admin)
    segs = Folder().createFolder(labels, "segmentations", parentType="folder", creator=admin)
    live = Collection().findOne({"name": "SegQueue"})
    seeds = Folder().createFolder(live, "seeds-totalseg", parentType="collection",
                                  creator=admin)
    files = {}
    for n in (first, second):
        ctPath = _nifti(world.data / f"ImageCAS__{n:04d}.nii.gz",
                        np.full((24, 24, 24), 100, dtype=np.int16))
        ct = _upload(ctPath, cases, admin)
        Item().setMetadata(Item().load(ct["itemId"], force=True),
                           {"icx_split": "train", "imagecas_id": n})
        ref = _upload(_nifti(world.data / f"ImageCAS-X__{n:04d}__labels14.nii.gz",
                             _icx(np, _tree(np))), segs, admin)
        files[n] = {"ct": ct, "ref": ref}
        # Where the test helpers look for a case's CT grid.
        name = f"annotator_benchmark_{n:04d}"
        (world.data / f"{name}.nii.gz").write_bytes(ctPath.read_bytes())
    world.bench = {"first": first, "second": second, "files": files, "seeds": seeds,
                   "segs": segs}
    return world


def _lines():
    lines = []
    return lines, lines.append


def _create(apply=True):
    from girder_segqueue14 import benchmark

    lines, out = _lines()
    return benchmark.runCreate(apply=apply, root=str(REPO), out=out), lines


def _seedFile(world, shape=(24, 24, 24)):
    import numpy as np

    mask = np.zeros(shape, np.uint8)
    mask[4:9, 4:9, 4:20] = 3          # any non-zero value is vessel; stored as 1
    return _nifti(world.data / f"seed_{shape[0]}.nii.gz", mask)


def _seeded(world):
    from girder_segqueue14 import benchmark

    _create()
    benchmark.runSeed(apply=True, seedFile=str(_seedFile(world)), out=lambda _: None)


def _assign(exclude, apply=True, **kwargs):
    """``exclude`` names the fixture's admin too: it created the group, so it is a
    member, as the lead's account is on janus."""
    from girder_segqueue14 import benchmark

    lines, out = _lines()
    return benchmark.runAssign(exclude, apply=apply, out=out, **kwargs), lines


def _benchCase():
    from girder_segqueue14.models import Case14

    return Case14().benchmarkCase()


# ------------------------------------------------------------------ create


def test_create_draws_the_project_pick_once_and_reuses_it(bench):
    from girder_segqueue14.models import Case14

    summary, lines = _create(apply=False)
    assert summary["name"] == "annotator_benchmark_0855" and _benchCase() is None
    assert any("eligible: 400" in line for line in lines), lines

    summary, lines = _create()
    case = _benchCase()
    assert summary["created"] and case["name"] == "annotator_benchmark_0855"
    files = bench.bench["files"][PICK]
    assert case["fileId"] == files["ct"]["_id"], "the ImageCAS-X CT in place, not a copy"
    assert case["referenceFileId"] == files["ref"]["_id"]
    assert case["benchmark"] is True and case["tier"] == "annotator-benchmark"
    assert case["seedFileId"] is None and case["benchmarkPending"] == []
    assert len(case["checksum"]) == 64
    pick = case["benchmarkPick"]
    assert pick["imagecasId"] == 855 and pick["icxCase"] == "c0854" and pick["split"] == "train"
    assert pick["salt"] and pick["rank"] and "JA12 guard" in pick["why"]
    assert "no list of ImageCAS cases" in pick["twins"]

    again, lines = _create()
    assert not again["created"] and any("never redrawn" in line for line in lines)
    assert Case14().collection.count_documents({"benchmark": True}) == 1
    assert _benchCase()["benchmarkPick"]["rank"] == pick["rank"]


def test_create_skips_a_case_whose_reference_is_missing(bench):
    from girder.models.item import Item

    ref = bench.bench["files"][PICK]["ref"]
    Item().remove(Item().load(ref["itemId"], force=True))
    summary, lines = _create()
    second = bench.bench["second"]
    assert summary["name"] == f"annotator_benchmark_{second:04d}"
    assert summary["pick"]["position"] == 1
    assert any("skipped c0854" in line for line in lines), lines


# -------------------------------------------------------------------- seed


def test_a_seed_must_be_on_the_ct_grid_and_is_stored_like_the_pool_seeds(bench):
    from girder.models.item import Item
    from girder_segqueue14 import benchmark

    _create()
    lines, out = _lines()
    with pytest.raises(SystemExit, match="grid"):
        benchmark.runSeed(apply=True, seedFile=str(_seedFile(bench, (20, 24, 24))), out=out)
    dry = benchmark.runSeed(apply=False, seedFile=str(_seedFile(bench)), out=out)
    assert dry["seed"] == "would upload" and _benchCase()["seedFileId"] is None

    done = benchmark.runSeed(apply=True, seedFile=str(_seedFile(bench)), out=out)
    assert done["seed"] == "uploaded"
    case = _benchCase()
    assert case["seedFileId"] and "TotalSegmentator 2.18.0" in case["seedSource"]
    item = Item().findOne({"folderId": bench.bench["seeds"]["_id"]})
    assert item["name"] == "ImageCAS__0855__totalseg-coronary.nii.gz"
    assert item["meta"]["segqueue14_case"] == "annotator_benchmark_0855"
    assert benchmark.runSeed(apply=True, seedFile=str(_seedFile(bench)), out=out) == {
        "seed": "present"}


def _fakeTotalseg(tmp_path, version="2.18.0"):
    """A stand-in TotalSegmentator: a ``python`` beside it that reports ``version``,
    and an executable that writes a coronary mask on the input's grid."""
    bindir = tmp_path / "ts-venv" / "bin"
    bindir.mkdir(parents=True)
    py = bindir / "python"
    py.write_text(f"#!/bin/sh\necho {version}\n")
    helper = tmp_path / "fake_ts.py"
    helper.write_text(
        "import sys\nimport numpy as np\nimport SimpleITK as sitk\n"
        "a = sys.argv[1:]\nsrc, dst = a[a.index('-i') + 1], a[a.index('-o') + 1]\n"
        "assert a[:2] == ['-ta', 'coronary_arteries'] and '--ml' in a, a\n"
        "ct = sitk.ReadImage(src)\nm = np.zeros(sitk.GetArrayFromImage(ct).shape, np.uint8)\n"
        "m[3:8, 3:8, 3:8] = 1\nout = sitk.GetImageFromArray(m)\nout.CopyInformation(ct)\n"
        "sitk.WriteImage(out, dst)\n")
    ts = bindir / "TotalSegmentator"
    ts.write_text(f"#!/bin/sh\nexec {sys.executable} {helper} \"$@\"\n")
    for path in (py, ts):
        path.chmod(path.stat().st_mode | stat.S_IEXEC)
    return ts


def test_the_seed_runs_totalseg_2_18_0_as_the_pool_batch_did(bench, tmp_path):
    from girder_segqueue14 import benchmark

    _create()
    lines, out = _lines()
    with pytest.raises(SystemExit, match="2.18.0"):
        benchmark.runSeed(apply=True, totalseg=str(_fakeTotalseg(tmp_path / "old", "2.11.0")),
                          out=out)
    ts = _fakeTotalseg(tmp_path)
    assert benchmark.runSeed(apply=False, totalseg=str(ts), out=out) == {"seed": "would run"}
    assert _benchCase()["seedFileId"] is None
    done = benchmark.runSeed(apply=True, totalseg=str(ts), out=out)
    assert done["seed"] == "uploaded" and done["voxels"] == 125
    assert any("-ta coronary_arteries --ml -d cpu -nr 4 -ns 4" in line for line in lines)
    assert _benchCase()["seedFileId"]


# ---------------------------------------------------------- assign and serve


def test_assign_needs_a_seed_and_refuses_an_unknown_excluded_login(bench):
    _create()
    with pytest.raises(SystemExit, match="no seed"):
        _assign("cathy,admin")
    _seeded(bench)
    with pytest.raises(SystemExit, match="no such login"):
        _assign("cathy,admin,typo")
    with pytest.raises(SystemExit, match="exclude is required"):
        _assign(None)
    result, _ = _assign("cathy,admin", apply=False)
    assert result["anna"] == "would invite" and _benchCase()["benchmarkPending"] == []


def test_it_is_next_for_assigned_annotators_only_and_pool_serving_is_unchanged(bench):
    import numpy as np
    from girder_segqueue14.models import Assignment14, Case14

    _readyProject(bench)
    _seeded(bench)
    queue = _resource()
    people = bench.people

    # bobby already holds a pool case when the invitations go out.
    _as(people["bobby"])
    held = queue.nextCase(clientProtocol=17)
    assert held["caseName"] == "imagecas_0001"

    result, _ = _assign("cathy,admin")
    assert result["cathy"] == "excluded" and result["anna"] == "invited"
    pending = set(_benchCase()["benchmarkPending"])
    assert pending == {people[n]["_id"] for n in ("anna", "bobby", "revy")}

    # anna: the benchmark first, with its seed and no prelabel; the kind stays hidden.
    _as(people["anna"])
    info = queue.nextCase(clientProtocol=17)
    assert info["caseName"] == "annotator_benchmark_0855"
    assert info["hasSeed"] and not info["hasPrelabel"]
    assert "kind" not in queue.listMine()[0]
    queue.downloadAsset(caseId=info["caseId"], kind="seed")
    assert _refusal(queue.downloadAsset, caseId=info["caseId"], kind="reference").code == 400

    # bobby holds a case: nothing more until it is done, then the benchmark.
    _as(people["bobby"])
    assert _refusal(queue.nextCase, clientProtocol=17).code == 409
    _submit(bench, queue, people["bobby"], held, _tree(np))
    _as(people["bobby"])
    assert queue.nextCase(clientProtocol=17)["caseName"] == "annotator_benchmark_0855"

    # cathy (excluded) is served the pool exactly as before, and never the benchmark.
    served = []
    for _ in range(20):
        _as(people["cathy"])
        try:
            got = queue.nextCase(clientProtocol=17)
        except Exception:
            break
        served.append(got["caseName"])
        queue.release(assignmentId=got["assignmentId"], reason="test")
    assert "annotator_benchmark_0855" not in served
    assert served[0] == "imagecas_0002"     # 0001 is bobby's, so the next in serve order
    case = _benchCase()
    assert people["cathy"]["_id"] not in case["assignedUserIds"]
    assert all(c["name"] != case["name"] for c in Case14().candidates(people["cathy"]["_id"]))
    # Nor can a reviewer hand it to her: it is not a pool case.
    _as(people["revy"])
    assert _refusal(queue.assignCase, caseId=str(case["_id"]),
                    userId=str(people["cathy"]["_id"])).code == 409

    # Every invited annotator holds it at once; replicasWanted is never consulted.
    _as(people["revy"])
    assert queue.nextCase(clientProtocol=17)["caseName"] == "annotator_benchmark_0855"
    case = _benchCase()
    assert case["replicasWanted"] == 1 and case["activeCount"] == 3
    assert case["benchmarkPending"] == []
    leases = Assignment14().benchmarkHistory(case["_id"])
    assert [a["benchmarkAttempt"] for a in leases] == [1, 1, 1]
    assert {a["kind"] for a in leases} == {"benchmark"}

    # An invitation is served once: anna's next /next is the pool again.
    _assign("cathy,admin")
    assert people["anna"]["_id"] not in _benchCase()["benchmarkPending"]


def test_excluding_a_login_withdraws_its_invitation(bench):
    _seeded(bench)
    _assign("admin")
    assert bench.people["cathy"]["_id"] in _benchCase()["benchmarkPending"]
    result, _ = _assign("cathy,admin")
    assert result["cathy"] == "excluded; invitation withdrawn"
    assert bench.people["cathy"]["_id"] not in _benchCase()["benchmarkPending"]


# --------------------------------------------------------------- scoring


def _benchmarkRead(world, queue, login, array):
    _as(world.people[login])
    info = queue.nextCase(clientProtocol=17)
    assert info["caseName"].startswith("annotator_benchmark_")
    return _submit(world, queue, world.people[login], info, array)


def test_a_submission_goes_to_review_with_its_own_dice_and_no_pair(bench):
    import numpy as np
    from girder_segqueue14 import scoring
    from girder_segqueue14.models import Assignment14, Submission14
    from girder_segqueue14.rest.queue import quotaRemaining

    _seeded(bench)
    _assign("cathy,bobby,admin")
    queue = _resource()
    perfect = _benchmarkRead(bench, queue, "anna", _tree(np))
    poor = _tree(np)
    poor[poor == 4] = 0                                    # no RCA
    second = _benchmarkRead(bench, queue, "revy", poor)
    assert perfect["awaitingReview"] and second["awaitingReview"]

    assert scoring.runOnce() == 2
    for response, mean in ((perfect, 1.0), (second, None)):
        submission = Submission14().load(response["submissionId"], force=True)
        assert submission["kind"] == "benchmark" and submission["needsReview"]
        score = submission["autoScore"]
        assert score["benchmark"] and score["against"] == ["imagecas-x"]
        assert "duplicate" not in score, "never paired with another annotator's read"
        if mean is not None:
            assert score["reference"]["mean_dice"] == mean and score["flags"] == []
        assignment = Assignment14().load(submission["assignmentId"], force=True)
        assert assignment["state"] == "submitted", "never auto-approved"
    poorScore = Submission14().load(second["submissionId"], force=True)["autoScore"]
    assert poorScore["reference"]["per_structure"]["RCA"]["dice"] == 0.0

    _as(bench.people["revy"])
    rows = {r["submissionId"]: r for r in queue.reviewQueue(limit=50, offset=0)}
    row = rows[perfect["submissionId"]]
    assert row["benchmark"] and row["kind"] == "benchmark" and row["benchmarkAttempt"] == 1
    assert row["caseName"] == "annotator_benchmark_0855"
    assert row["autoScore"]["reference_mean_dice"] == 1.0
    assert row["autoScore"]["duplicate_mean_dice"] is None
    assert any("annotator benchmark (D43)" in reason for reason in row["flagged"])

    # Approving it does not count as a pool read: no quota used, no sampling record.
    queue.verdict(submissionId=perfect["submissionId"], verdict="approve")
    anna = bench.people["anna"]
    assert Assignment14().recordFor(anna["_id"]).approved == 0
    anna["segqueue14Quota"] = 1
    assert quotaRemaining(anna) == 1


def test_a_retest_is_a_fresh_attempt_and_both_scores_are_kept(bench):
    import numpy as np
    from girder_segqueue14 import benchmark, scoring

    _seeded(bench)
    _assign("cathy,bobby,revy,admin")
    queue = _resource()
    first = _benchmarkRead(bench, queue, "anna", _tree(np))
    scoring.runOnce()
    _as(bench.people["revy"])
    queue.verdict(submissionId=first["submissionId"], verdict="approve")

    result, _ = _assign("cathy,bobby,revy,admin")
    assert result["anna"].startswith("benchmarked (1 attempt")
    result, _ = _assign("cathy,admin", logins="anna", retest=True)
    assert set(result) == {"anna"} and "retest; attempt 2" in result["anna"]

    worse = _tree(np)
    worse[worse == 2] = 0                                  # no LAD
    second = _benchmarkRead(bench, queue, "anna", worse)
    scoring.runOnce()

    lines, out = _lines()
    status = benchmark.runStatus(asJson=True, out=out)
    attempts = [a for a in status["attempts"] if a["login"] == "anna"]
    assert [a["attempt"] for a in attempts] == [1, 2]
    assert [a["state"] for a in attempts] == ["approved", "submitted"]
    assert attempts[0]["score"]["mean_dice"] == 1.0
    assert attempts[1]["score"]["per_class_dice"]["LAD"] == 0.0
    assert attempts[1]["score"]["mean_dice"] < 1.0
    assert second["submissionId"] != first["submissionId"]
    lines, out = _lines()
    benchmark.runStatus(out=out)
    assert any("anna" in line and "approved" in line and "1.000" in line for line in lines)


# ----------------------------------------------------------------- export


def test_no_export_takes_a_benchmark_read(bench, tmp_path):
    import numpy as np
    from girder_segqueue14 import export, scoring

    _readyProject(bench)
    _seeded(bench)
    _assign("bobby,revy,cathy,admin")
    queue = _resource()
    read = _benchmarkRead(bench, queue, "anna", _tree(np))
    _as(bench.people["cathy"])
    pool = queue.nextCase(clientProtocol=17)
    _submit(bench, queue, bench.people["cathy"], pool, _tree(np))
    scoring.runOnce()
    _as(bench.people["revy"])
    queue.verdict(submissionId=read["submissionId"], verdict="approve")

    yielded = [(case["name"], name) for case, _, name in
               export.collect(includeUnreviewed=True, replicas="all")]
    assert ("annotator_benchmark_0855", export.BENCHMARK) in yielded
    out = tmp_path / "export"
    assert export.main(["--out", str(out), "--include-unreviewed"]) == 0
    written = sorted(p.name for p in out.iterdir() if p.is_dir())
    assert written == [pool["caseName"]]
    manifest = json.loads((out / "manifest.json").read_text())
    assert manifest["source"]["annotator_benchmark_excluded"] == 1
    assert not any(n.startswith("annotator_benchmark") for n in os.listdir(out))


# ----------------------------------------------- seed --from-girder (#293)


def _leadPublic(world):
    """``user/christian/Public``: the lead's own Girder folder (made with the account)."""
    from girder.models.folder import Folder
    from girder.models.user import User

    lead = User().createUser("christian", "password1", "C", "R", "christian@example.org")
    public = Folder().findOne({"parentId": lead["_id"], "parentCollection": "user",
                               "name": "Public"})
    assert public is not None
    return lead, public


def _mask(world, name, shape=(24, 24, 24), value=3, spacing=(0.5, 0.5, 0.5)):
    import numpy as np

    mask = np.zeros(shape, np.uint8)
    if value:
        mask[4:9, 4:9, 4:20] = 1
        mask[10:12, 10:12, 10:12] = value   # a second label: still vessel
    return _nifti(world.data / name, mask, spacing)


def _fromGirder(apply=True, **kwargs):
    from girder_segqueue14 import benchmark

    lines, out = _lines()
    return benchmark.runSeed(apply=apply, fromGirder="user/christian/Public", out=out,
                             **kwargs), lines


def _snapshot(fileDoc):
    """The lead's file as stored: its document and its bytes."""
    from girder.models.file import File

    doc = File().load(fileDoc["_id"], force=True)
    data = b"".join(File().download(doc, headers=False)())
    return {k: doc.get(k) for k in ("name", "itemId", "size", "sha512", "updated")}, data


def test_from_girder_finds_the_0855_file_binarises_and_copies_it(bench):
    import numpy as np
    import SimpleITK as sitk
    from girder.models.file import File
    from girder.models.folder import Folder
    from girder.models.item import Item

    _create()
    lead, public = _leadPublic(bench)
    sub = Folder().createFolder(public, "totalseg", parentType="folder", creator=lead)
    src = _upload(_mask(bench, "ImageCAS__0855_coronary.nii.gz"), sub, lead)
    Item().setMetadata(Item().load(src["itemId"], force=True),
                       {"totalsegmentator_version": "2.18.0"})
    notes = bench.data / "seed_notes.txt"
    notes.write_text("made with TotalSegmentator")
    _upload(notes, public, lead)                        # not a volume: ignored
    before = _snapshot(src)

    dry, lines = _fromGirder(apply=False)
    assert dry["seed"] == "would upload" and dry["voxels"] == 5 * 5 * 16 + 8
    assert _benchCase()["seedFileId"] is None
    assert any("totalseg/ImageCAS__0855_coronary.nii.gz" in line for line in lines)
    assert any("24 x 24 x 24 voxels" in line for line in lines)

    done, _ = _fromGirder()
    assert done["seed"] == "uploaded"
    case = _benchCase()
    assert case["seedSource"] == (
        "TotalSegmentator coronary_arteries (binary), version 2.18.0, supplied by the lead "
        "from user/christian/Public/totalseg/ImageCAS__0855_coronary.nii.gz")
    seed = Item().findOne({"folderId": bench.bench["seeds"]["_id"]})
    assert seed["name"] == "ImageCAS__0855__totalseg-coronary.nii.gz"
    assert seed["meta"]["seed_source"] == case["seedSource"]
    stored = File().load(case["seedFileId"], force=True)
    assert stored["_id"] != src["_id"] and stored["itemId"] == seed["_id"]
    path = bench.data / "stored.nii.gz"
    path.write_bytes(b"".join(File().download(stored, headers=False)()))
    arr = sitk.GetArrayFromImage(sitk.ReadImage(str(path)))
    assert arr.dtype == np.uint8 and set(np.unique(arr)) == {0, 1}

    # The lead's file is untouched, where it was; a re-run changes nothing.
    assert _snapshot(src) == before
    seedsBefore = list(Item().find({"folderId": bench.bench["seeds"]["_id"]}))
    again, _ = _fromGirder()
    assert again == {"seed": "present"}
    assert list(Item().find({"folderId": bench.bench["seeds"]["_id"]})) == seedsBefore
    assert _benchCase()["seedFileId"] == case["seedFileId"]
    assert _snapshot(src) == before


def test_from_girder_takes_the_only_volume_and_says_when_the_version_is_unknown(bench):
    _create()
    lead, public = _leadPublic(bench)
    _upload(_mask(bench, "coronary.nii.gz"), public, lead)
    dry, _ = _fromGirder(apply=False)
    assert dry["seedSource"].startswith(
        "TotalSegmentator coronary_arteries (binary), version unknown, supplied by the lead "
        "from user/christian/Public/coronary.nii.gz")


def test_from_girder_refuses_ambiguity_and_lists_the_candidates(bench):
    from girder.models.item import Item

    _create()
    lead, public = _leadPublic(bench)
    _upload(_mask(bench, "a_0855.nii.gz"), public, lead)
    _upload(_mask(bench, "b_0855.nii.gz"), public, lead)
    with pytest.raises(SystemExit, match=r"2 label volume.*a_0855.nii.gz \(\d+ bytes\).*"
                                         r"b_0855.nii.gz \(\d+ bytes\)"):
        _fromGirder(apply=False)
    assert _benchCase()["seedFileId"] is None
    # Neither name holds 0855 and there are two: refused too.
    for item in list(Item().find({"folderId": public["_id"]})):
        Item().remove(item)
    _upload(_mask(bench, "x.nii.gz"), public, lead)
    _upload(_mask(bench, "y.nii.gz"), public, lead)
    with pytest.raises(SystemExit, match="none has the case id"):
        _fromGirder(apply=False)
    # --from-girder-file picks one explicitly.
    dry, _ = _fromGirder(apply=False, fromGirderFile="y.nii.gz")
    assert dry["seed"] == "would upload" and "Public/y.nii.gz" in dry["seedSource"]
    with pytest.raises(SystemExit, match="0 label volume"):
        _fromGirder(apply=False, fromGirderFile="nope.nii.gz")


def test_from_girder_refuses_a_wrong_grid_and_an_empty_mask(bench):
    from girder.models.item import Item

    _create()
    lead, public = _leadPublic(bench)
    item = _upload(_mask(bench, "shape_0855.nii.gz", shape=(20, 24, 24)), public, lead)
    with pytest.raises(SystemExit, match="grid"):
        _fromGirder()
    Item().remove(Item().load(item["itemId"], force=True))
    item = _upload(_mask(bench, "spacing_0855.nii.gz", spacing=(0.6, 0.5, 0.5)), public, lead)
    with pytest.raises(SystemExit, match="grid"):
        _fromGirder()
    Item().remove(Item().load(item["itemId"], force=True))
    _upload(_mask(bench, "empty_0855.nii.gz", value=0), public, lead)
    with pytest.raises(SystemExit, match="empty"):
        _fromGirder()
    assert _benchCase()["seedFileId"] is None
    assert Item().findOne({"folderId": bench.bench["seeds"]["_id"]}) is None


def test_from_girder_refuses_a_missing_folder_and_mixed_sources(bench):
    from girder_segqueue14 import benchmark

    _create()
    with pytest.raises(SystemExit, match="no Girder resource"):
        _fromGirder(apply=False)
    with pytest.raises(SystemExit, match="one of"):
        benchmark.runSeed(fromGirder="user/christian/Public", seedFile="x", out=print)
    with pytest.raises(SystemExit, match="needs --from-girder"):
        benchmark.runSeed(fromGirderFile="x.nii.gz", out=print)
