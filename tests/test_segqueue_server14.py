"""SegQueue14's Girder plugin against a real Girder and a real MongoDB.

Marked ``needs_mongo`` and skipped without one, exactly like
``test_segqueue_server.py`` (and named to run after it: both bind Girder to a
scratch database, and the live module refuses one it did not create). Run with::

    SEGQUEUE_TEST_MONGO=mongodb://localhost:27099 pytest tests/test_segqueue_server14.py

What is exercised is the whole SegQueue14 path on a miniature project that has a
*live* SegQueue beside it: population from the live cases, prelabel attach and
refresh, serve order, the protocol and D13 refusals at the REST layer, reference
and two-read scoring, export -- and, throughout, that nothing belonging to the
live project changed.
"""

import hashlib
import json
import os
import sys
import uuid
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
for extra in (REPO / "src", REPO / "server"):
    if str(extra) not in sys.path:
        sys.path.append(str(extra))

pytestmark = pytest.mark.needs_mongo

MONGO_ENV = "SEGQUEUE_TEST_MONGO"


@pytest.fixture(scope="module")
def girder_db(tmp_path_factory):
    uri = os.environ.get(MONGO_ENV)
    if not uri:
        pytest.skip(f"set {MONGO_ENV} to a MongoDB URI to run the server tests")
    try:
        import pymongo

        client = pymongo.MongoClient(uri, serverSelectionTimeoutMS=3000)
        client.server_info()
    except ImportError:
        pytest.skip("pymongo is not installed in this environment")
    except Exception as exc:  # pragma: no cover - depends on the machine
        pytest.skip(f"no MongoDB at {uri}: {exc}")
    # Girder binds its database when girder.models is first imported, and
    # importing `girder` at all does that -- so the URI is set before anything
    # from Girder is imported, unless another server test bound it already.
    created = None
    if "girder.models" not in sys.modules:
        created = f"segqueue14_test_{uuid.uuid4().hex[:8]}"
        os.environ["GIRDER_MONGO_URI"] = f"{uri.rstrip('/')}/{created}"
    for module in ("girder", "numpy", "SimpleITK", "nibabel", "scipy"):
        pytest.importorskip(module)
    try:
        from girder_segqueue14.models import Case14
    except ImportError as exc:
        pytest.skip(f"girder-segqueue14 cannot be imported here: {exc}")
    bound = Case14().collection.database.name
    # Never run against anything but a scratch database: the fixture below
    # empties collections.
    if not bound.startswith(("segqueue14_test_", "segqueue_test_")):
        pytest.fail(f"girder is bound to {bound!r}, which is not a scratch test database")

    from girder.models.assetstore import Assetstore

    root = tmp_path_factory.mktemp("assetstore")
    # Girder refuses uploads when a filesystem assetstore has under 10 GB free;
    # these tests write a few megabytes.
    os.environ.setdefault("GIRDER_FILESYSTEMASSETSTORE_RESERVED_MBYTES", "16")
    if Assetstore().findOne() is None:
        Assetstore().createFilesystemAssetstore(name="test", root=str(root))
    yield bound
    if created:
        client.drop_database(created)


# ------------------------------------------------------------------ the world


def _nifti(path, array, spacing=(0.5, 0.5, 0.5)):
    import nibabel as nib
    import numpy as np

    affine = np.diag(list(spacing) + [1.0])
    nib.save(nib.Nifti1Image(array, affine), str(path))
    return path


def _tree(np, shape=(24, 24, 24), shift=0):
    """Every one of the project's four classes (D25) as a small block."""
    vol = np.zeros(shape, dtype=np.uint8)
    for k in range(1, 5):
        z = 1 + (k - 1) % 7 * 3
        y = 2 + ((k - 1) // 7) * 10 + shift
        vol[z:z + 2, y:y + 4, 6:14] = k
    return vol


def _icx(np, tree):
    """``tree`` in ImageCAS-X's 14 label values, as a stored reference speaks them:
    RCA is 9 there. Scoring must collapse it back to the four (labels.ICX14_TO_4)."""
    out = tree.copy()
    out[tree == 4] = 9
    return out


def _upload(path, folder, user, name=None):
    from girder.models.upload import Upload

    with open(path, "rb") as handle:
        return Upload().uploadFromFile(handle, size=os.path.getsize(path),
                                       name=name or os.path.basename(path),
                                       parentType="folder", parent=folder, user=user)


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


@pytest.fixture
def world(girder_db, tmp_path):
    """A live SegQueue with 12 ImageCAS cases, and an empty SegQueue14.

    ImageCAS ids 1-6 are ImageCAS-X train, 7 val, 8-9 test, 10-12 not in ImageCAS-X.
    """
    import numpy as np
    from girder.models.collection import Collection
    from girder.models.file import File
    from girder.models.folder import Folder
    from girder.models.group import Group
    from girder.models.item import Item
    from girder.models.setting import Setting
    from girder.models.user import User
    from girder_segqueue14 import settings  # noqa: F401  (registers segqueue14.*)
    from girder_segqueue14.models import Assignment14, Case14, Note14, Review14, Submission14

    for model in (Case14, Assignment14, Submission14, Review14, Note14):
        model().collection.delete_many({})
    db = Case14().database
    db["segqueue_case"].delete_many({})
    for model in (User, Group, Collection, Folder, Item, File):
        model().collection.delete_many({})
    for key in ("segqueue14.policy", "segqueue14.project", "segqueue14.reference"):
        Setting().collection.delete_many({"key": key})

    admin = User().createUser("admin", "password1", "A", "Dmin", "admin@example.org",
                              admin=True)
    people = {login: User().createUser(login, "password1", login, "X",
                                       f"{login}@example.org")
              for login in ("anna", "bobby", "cathy", "revy")}

    # -- the live project, as girder_segqueue would have left it
    live = Collection().createCollection("SegQueue", creator=admin, public=False)
    casesF = Folder().createFolder(live, "cases", parentType="collection", creator=admin)
    icx = Folder().createFolder(live, "imagecas-x", parentType="collection", creator=admin)
    segs = Folder().createFolder(icx, "segmentations", parentType="folder", creator=admin)
    lists = Folder().createFolder(icx, "filelist", parentType="folder", creator=admin)

    data = tmp_path / "data"
    data.mkdir()
    split = {**{n: "train" for n in range(1, 7)}, 7: "val", 8: "test", 9: "test"}
    liveIds, references = {}, {}
    for n in range(1, 13):
        name = f"imagecas_{n:04d}"
        ct = _nifti(data / f"{name}.nii.gz", np.full((24, 24, 24), 200 + n, dtype=np.int16))
        ctFile = _upload(ct, casesF, admin)
        region = _nifti(data / f"{name}.region.nii.gz", np.ones((24, 24, 24), np.uint8))
        regionFile = _upload(region, casesF, admin)
        seed = _nifti(data / f"{name}.seed.nii.gz", np.ones((24, 24, 24), np.uint8))
        seedFile = _upload(seed, casesF, admin)
        liveIds[name] = db["segqueue_case"].insert_one({
            "name": name, "fileId": ctFile["_id"], "checksum": _sha(ct),
            "sizeBytes": ctFile["size"], "regionFileId": regionFile["_id"],
            "seedFileId": seedFile["_id"], "geometryFixed": False, "retired": False,
            "replicasWanted": 1, "activeCount": 0, "approvedCount": 0,
            "assignedUserIds": [], "priority": 0}).inserted_id
        if n in split:
            ref = _nifti(data / f"{n}.coronary.nii.gz", _icx(np, _tree(np)))
            refFile = _upload(ref, segs, admin)
            item = Item().load(refFile["itemId"], force=True)
            Item().setMetadata(item, {"segqueue_case": name})
            references[name] = refFile["_id"]
    for which in ("train", "val", "test"):
        path = data / f"{which}.txt"
        path.write_text(" ".join(str(n) for n, s in split.items() if s == which))
        _upload(path, lists, admin)
    exclude = data / "exclude.txt"
    exclude.write_text("10 11 12")
    _upload(exclude, lists, admin)

    from girder_segqueue14.utils import ensureGroups

    ensureGroups(admin)
    annotators = Group().findOne({"name": "segqueue14-annotators"})
    reviewers = Group().findOne({"name": "segqueue14-reviewers"})
    for login in ("anna", "bobby", "cathy", "revy"):
        Group().addUser(annotators, people[login])
    Group().addUser(reviewers, people["revy"])
    people = {login: User().load(u["_id"], force=True) for login, u in people.items()}

    # Every read is decided by the scores in these tests, not by the sampling roll.
    Setting().set("segqueue14.policy", {"training_gate_cases": 0, "base_review_rate": 0.0,
                                        "trusted_review_rate": 0.0})

    class World:
        pass

    w = World()
    w.admin, w.people, w.data, w.liveIds, w.references = admin, people, data, liveIds, references
    w.db = db
    return w


def _liveSnapshot(world):
    """Everything of the live project's that SegQueue14 must not change: the live
    case documents, and every file they or the ImageCAS-X items point at (the
    document and the bytes)."""
    from girder.models.file import File
    from girder.models.item import Item

    cases = sorted(world.db["segqueue_case"].find({}), key=lambda c: c["name"])
    ids = [c[k] for c in cases for k in ("fileId", "regionFileId", "seedFileId")]
    ids += list(world.references.values())
    files = []
    for fileId in ids:
        doc = File().load(fileId, force=True)
        item = Item().load(doc["itemId"], force=True)
        data = b"".join(File().download(doc, headers=False)())
        files.append((doc, item["folderId"], item["name"], item.get("meta"),
                      hashlib.sha256(data).hexdigest()))
    return json.dumps([cases, files], default=str, sort_keys=True)


def _populate(world, **kwargs):
    from girder_segqueue14 import populate

    lines = []
    summary = populate.populateImagecas(world.admin, out=lines.append, **kwargs)
    return summary, lines


# ------------------------------------------------------------------ population


def test_population_references_the_live_files_and_orders_by_imagecas_x(world):
    from girder_segqueue14.models import Case14

    before = _liveSnapshot(world)
    summary, lines = _populate(world, dryRun=True)
    assert summary["create"] == 12 and Case14().collection.count_documents({}) == 0

    summary, _ = _populate(world)
    assert summary["create"] == 12
    cases = {c["name"]: c for c in Case14().find({})}
    for name, liveId in world.liveIds.items():
        live = world.db["segqueue_case"].find_one({"_id": liveId})
        assert cases[name]["fileId"] == live["fileId"], "the same CT file, not a copy"
        assert cases[name]["regionFileId"] == live["regionFileId"]
        assert cases[name]["sourceCaseId"] == liveId
        assert cases[name]["checksum"] == live["checksum"]
        # D8: the live ImageCAS seed is never referenced (a pool case's own
        # TotalSegmentator seed is a different thing, D23).
        assert cases[name].get("seedFileId") is None, "D8: no binary seed"
        assert cases[name]["seedFileId"] != live["seedFileId"]
    assert cases["imagecas_0001"]["referenceFileId"] == world.references["imagecas_0001"]
    assert cases["imagecas_0010"]["referenceFileId"] is None

    tiers = {n: c["tier"] for n, c in cases.items()}
    assert tiers["imagecas_0001"] == tiers["imagecas_0007"] == "icx-trainval"
    assert tiers["imagecas_0008"] == "icx-test"
    assert tiers["imagecas_0011"] == "imagecas-unlabelled"
    assert cases["imagecas_0011"]["replicasWanted"] == 2
    assert all(cases[f"imagecas_{n:04d}"]["replicasWanted"] in (1, 2) for n in range(1, 10))
    # round(0.1 * 6) = 1 blind duplicate among the six train cases.
    assert sum(c["blindDuplicate"] for c in cases.values() if c["split"] == "train") == 1

    # Idempotent.
    again, _ = _populate(world)
    assert again["create"] == 0 and again["same"] == 12
    assert Case14().collection.count_documents({}) == 12
    assert _liveSnapshot(world) == before


def test_splits_can_come_from_a_local_directory_and_are_required(world, tmp_path):
    lists = tmp_path / "lists"
    lists.mkdir()
    (lists / "train.txt").write_text("1 2 3 4 5 6 7")       # 7 moved to train
    (lists / "test.txt").write_text("8 9")
    summary, lines = _populate(world, splitsDir=str(lists), dryRun=True)
    assert "file lists in" in lines[0]
    assert summary["byTier"]["icx-trainval"]["cases"] == 7

    from girder.models.item import Item

    Item().collection.delete_many({"name": {"$regex": r"\.txt$"}})
    with pytest.raises(SystemExit, match="split"):
        _populate(world, dryRun=True)


def test_update_reorders_without_lowering_reads_already_out(world):
    from girder_segqueue14.models import Case14

    _populate(world)
    # Moving the test tier to the front changes their priority and every case's
    # place in the serve order -- reported, but applied only with --update.
    summary, _ = _populate(world, priorities={"icx-test": 999})
    assert summary["differs"] == 12 and summary["update"] == 0
    assert Case14().findOne({"name": "imagecas_0008"})["priority"] == 100
    summary, _ = _populate(world, priorities={"icx-test": 999}, update=True)
    assert summary["update"] == 12
    assert Case14().findOne({"name": "imagecas_0008"})["priority"] == 999
    assert Case14().findOne({"name": "imagecas_0008"})["serveOrder"] == 0

    # Reads already handed out are never taken back.
    Case14().collection.update_one({"name": "imagecas_0011"},
                                   {"$set": {"activeCount": 1, "approvedCount": 1}})
    from segqueue14 import plan as sqplan

    summary, lines = _populate(world, priorities={"icx-test": 999}, update=True,
                               duplicateFraction=0.0)
    case = Case14().findOne({"name": "imagecas_0011"})
    assert case["replicasWanted"] == 2
    assert sqplan.DEFAULT_REPLICAS["imagecas-unlabelled"] == 2


def test_new_dataset_items_become_two_read_cases(world):
    import numpy as np
    from girder.models.collection import Collection
    from girder.models.folder import Folder
    from girder_segqueue14 import populate
    from girder_segqueue14.models import Case14

    other = Collection().createCollection("NewData", creator=world.admin, public=False)
    folder = Folder().createFolder(other, "asoca", parentType="collection",
                                   creator=world.admin)
    for i in range(2):
        path = _nifti(world.data / f"Case {i}.nii.gz", np.zeros((8, 8, 8), np.int16))
        _upload(path, folder, world.admin)
    lines = []
    summary = populate.populateExtra(world.admin, folder["_id"], "asoca", out=lines.append)
    assert summary["create"] == 2
    case = Case14().findOne({"name": "asoca_Case_0"})
    assert case["replicasWanted"] == 2 and case["dataset"] == "asoca"
    assert case["tier"] == "new-dataset" and len(case["checksum"]) == 64
    assert populate.populateExtra(world.admin, folder["_id"], "asoca",
                                  out=lines.append)["create"] == 0


# ------------------------------------------------------------------- prelabels


def _predictions(world, version, names=None, broken=()):
    import numpy as np

    directory = world.data / f"pred-{version}"
    directory.mkdir(exist_ok=True)
    for n in names or range(1, 13):
        array = _tree(np, shift=1 if version != "v1" else 0)
        if n in broken:
            array = array.astype(np.int16)
        # The model's own names: c(id - 1).
        _nifti(directory / f"c{n - 1:04d}.nii.gz", array)
    return directory


def test_prelabels_attach_by_case_name_and_refresh_only_where_allowed(world):
    from girder.models.file import File
    from girder.models.folder import Folder
    from girder_segqueue14 import prelabels
    from girder_segqueue14.models import Case14

    _populate(world)
    before = _liveSnapshot(world)
    lines = []
    summary = prelabels.runAttach(str(_predictions(world, "v1", broken=(12,))), "v1",
                                  world.admin, verifyGrid=True, out=lines.append)
    assert summary["attach"] == 11 and summary["invalid"] == 1
    assert any("imagecas_0012" in line and "uint8" in line for line in lines)
    case = Case14().findOne({"name": "imagecas_0002"})
    assert case["prelabelVersion"] == "v1"
    stored = File().load(case["prelabelFileId"], force=True)
    assert stored["name"] == "imagecas_0002.prelabel.nii.gz"
    from girder.models.item import Item

    folder = Folder().load(Item().load(stored["itemId"], force=True)["folderId"], force=True)
    assert folder["name"] == "v1"
    assert Folder().load(folder["parentId"], force=True)["name"] == "prelabels"

    # Re-run with 0012 fixed: the 11 already done are skipped, 0012 is attached.
    again = prelabels.runAttach(str(_predictions(world, "v1")), "v1", world.admin,
                                out=lines.append)
    assert again["skip"] == 11 and again["attach"] == 1

    # One case has been submitted (simulated): a D15 refresh must leave it alone,
    # and the held-out test cases too (D16).
    from girder_segqueue14.models import Submission14

    Submission14().collection.insert_one({"caseId": case["_id"], "authorRole": "annotator",
                                          "assignmentId": "x", "userId": "u"})
    lines = []
    summary = prelabels.runAttach(str(_predictions(world, "v2")), "v2", world.admin,
                                  out=lines.append)
    # 12 files: 0002 has a submission and 0008/0009 are held-out test cases, so
    # those keep v1; the other 9 refresh.
    assert summary["refresh"] == 9 and summary["attach"] == 0 and summary["skip"] == 3
    assert Case14().findOne({"name": "imagecas_0002"})["prelabelVersion"] == "v1"
    assert Case14().findOne({"name": "imagecas_0008"})["prelabelVersion"] == "v1"
    refreshed = Case14().findOne({"name": "imagecas_0003"})
    assert refreshed["prelabelVersion"] == "v2"
    assert [h["version"] for h in refreshed["prelabelHistory"]] == ["v1", "v2"]
    assert File().load(refreshed["prelabelHistory"][0]["fileId"], force=True) is not None
    assert _liveSnapshot(world) == before


def test_a_prelabel_on_the_wrong_grid_is_refused(world):
    import numpy as np
    from girder_segqueue14 import prelabels

    _populate(world)
    directory = world.data / "wrong"
    directory.mkdir()
    _nifti(directory / "imagecas_0001.nii.gz", np.zeros((24, 24, 20), np.uint8))
    lines = []
    summary = prelabels.runAttach(str(directory), "v1", world.admin, verifyGrid=True,
                                  out=lines.append)
    assert summary["invalid"] == 1 and "CT grid" in lines[-1]


# ----------------------------------------------------------------- the queue


class _Api:
    """The three SegQueue14 resources as one object, as Girder mounts them."""

    def __init__(self):
        from girder_segqueue14.rest import AdminResource14, QueueResource14, ReviewResource14

        self.queue = QueueResource14()
        self.review = ReviewResource14().attachTo(self.queue)
        self.admin = AdminResource14().attachTo(self.queue)

    def __getattr__(self, name):
        for part in (self.queue, self.review, self.admin):
            if hasattr(type(part), name):
                return getattr(part, name)
        raise AttributeError(name)


def _resource():
    return _Api()


def _as(user):
    from girder.api.rest import setCurrentUser

    setCurrentUser(user)


def _refusal(fn, *args, **kwargs):
    from girder.exceptions import RestException

    with pytest.raises(RestException) as info:
        fn(*args, **kwargs)
    return info.value


def _readyProject(world):
    _populate(world)
    from girder_segqueue14 import prelabels

    prelabels.runAttach(str(_predictions(world, "v1")), "v1", world.admin, out=lambda _: None)


def _submit(world, queue, user, info, array, counts=None, geometry=None):
    """Upload ``array`` as Slicer can store it -- an NRRD with the slice order
    reversed against the CT, same physical positions -- and submit it."""
    _as(user)
    queue.downloadCase(caseId=info["caseId"])      # ASSIGNED -> DOWNLOADED
    fileDoc, meta = _uploadSeg(world, user, info["caseName"], array, counts)
    _as(user)
    extra = {} if geometry is None else {"geometry": json.dumps(geometry)}
    return queue.submit(assignmentId=info["assignmentId"], fileId=str(fileDoc["_id"]),
                        meta=json.dumps(meta), clientProtocol=17, **extra)


def _uploadSeg(world, user, caseName, array, counts=None):
    """Write ``array`` as a ``.seg.nrrd`` on ``caseName``'s CT grid and upload it
    as ``user``. Returns ``(file document, SubmissionMeta dict)``."""
    import numpy as np
    import SimpleITK as sitk
    from girder_segqueue14.utils import incomingFolder

    ct = sitk.ReadImage(str(world.data / f"{caseName}.nii.gz"))
    nz = ct.GetSize()[2]
    image = sitk.GetImageFromArray(np.ascontiguousarray(array.transpose(2, 1, 0)[::-1]))
    image.SetSpacing(ct.GetSpacing())
    image.SetOrigin(ct.TransformIndexToPhysicalPoint((0, 0, nz - 1)))
    d = list(ct.GetDirection())
    d[2], d[5], d[8] = -d[2], -d[5], -d[8]
    image.SetDirection(d)
    path = world.data / f"{caseName}_{user['login']}_{uuid.uuid4().hex[:6]}.seg.nrrd"
    sitk.WriteImage(image, str(path), True)
    fileDoc = _upload(path, incomingFolder(world.admin), user)
    from segqueue14 import scoring as sq

    meta = {"checksum": _sha(path), "sizeBytes": os.path.getsize(path),
            "annotationSeconds": 300.0,
            "voxelCounts": counts if counts is not None else sq.voxel_counts(array),
            "extensionVersion": "test"}
    return fileDoc, meta


def test_the_protocol_is_checked_at_login_next_and_submit(world):
    _readyProject(world)
    queue = _resource()
    _as(world.people["anna"])
    for bad in (None, 1, 14, 15, 16):
        sent = {} if bad is None else {"clientProtocol": bad}
        err = _refusal(queue.getProject, **sent)
        assert err.code == 426 and err.extra["segqueueError"] == "client_too_old"
        assert "Update the SegQueue14 module" in err.extra["message"]
        assert _refusal(queue.nextCase, **sent).code == 426
    project = queue.getProject(clientProtocol=17)
    assert [s["name"] for s in project["segments"]][:3] == ["LM", "LAD", "LCx"]
    assert [s["name"] for s in project["segments"]] == ["LM", "LAD", "LCx", "RCA"]
    # The server speaks 18 (D44) and still serves the 0.17.x module the four.
    assert project["protocolVersion"] == 18
    assert queue.getProject(clientProtocol=18)["segments"] == project["segments"]
    assert "starts as a full copy of the vessel seed" in project["instructions"]


def test_next_serves_trainval_first_and_test_last(world):
    from girder_segqueue14.models import Case14

    _readyProject(world)
    queue = _resource()
    served = []
    # Hand every slot out, one annotator after another, releasing as we go.
    for _ in range(40):
        for login in ("anna", "bobby", "cathy"):
            _as(world.people[login])
            try:
                info = queue.nextCase(clientProtocol=17)
            except Exception:
                continue
            served.append(info["caseName"])
            queue.release(assignmentId=info["assignmentId"], reason="test")
    tiers = [Case14().findOne({"name": n})["tier"] for n in served]
    order = ["icx-trainval", "imagecas-unlabelled", "icx-test"]
    ranks = [order.index(t) for t in tiers]
    assert ranks == sorted(ranks), served
    assert served[0] == "imagecas_0001"
    assert "kind" not in queue.listMine(includeFinished=True)[0]


def test_a_good_read_is_scored(world):
    import numpy as np
    from girder_segqueue14 import scoring
    from girder_segqueue14.models import Assignment14, Case14, Submission14

    _readyProject(world)
    before = _liveSnapshot(world)
    queue = _resource()
    _as(world.people["anna"])
    info = queue.nextCase(clientProtocol=17)
    assert info["hasPrelabel"] and info["prelabelVersion"] == "v1"
    assert not info["hasSeed"] and info["hasRegion"]
    queue.downloadCase(caseId=info["caseId"])
    queue.downloadAsset(caseId=info["caseId"], kind="prelabel")
    # A seed is a real asset kind now (D23), but ImageCAS cases never ship one.
    assert _refusal(queue.downloadAsset, caseId=info["caseId"], kind="seed").code == 404
    assert _refusal(queue.downloadAsset, caseId=info["caseId"], kind="reference").code == 400

    truth = _tree(np)
    response = _submit(world, queue, world.people["anna"], info, truth)
    submission = Submission14().load(response["submissionId"], force=True)
    assert submission["prelabelVersion"] == "v1"
    assert submission["kind"] == "reference" and submission["scored"] is False

    assert scoring.runOnce() == 1
    submission = Submission14().load(response["submissionId"], force=True)
    ref = submission["autoScore"]["reference"]
    # The upload was z-reversed against the reference; scoring resampled it.
    assert ref["mean_dice"] == 1.0 and ref["presence_agreement"] == 1.0
    assert submission["autoScore"]["flags"] == []
    assignment = Assignment14().load(submission["assignmentId"], force=True)
    assert assignment["state"] == "approved"
    assert Case14().load(submission["caseId"], force=True)["approvedCount"] == 1
    assert _liveSnapshot(world) == before


# #270 (project lead, 2026-11-02): nothing about the segmentation is checked on
# submit or revise. Each read below would once have been refused.
_GEOMETRY = {"source": {"size": [24, 24, 24], "spacing": [0.5, 0.5, 0.5],
                        "origin": [0.0, 0.0, 0.0]},
             "segmentation": {"size": [20, 24, 24], "spacing": [0.5, 0.5, 0.5],
                              "origin": [1.0, 0.0, 0.0]}}


def _unchecked(np, case):
    """``(array, voxelCounts or None)`` for each read #270 says must go through."""
    read = _tree(np)
    if case in ("LAD", "LCx", "RCA"):
        read[read == {"LAD": 2, "LCx": 3, "RCA": 4}[case]] = 0
        return read, None
    if case == "overlap":
        # A labelmap holds one value per voxel, so classes that overlapped in the
        # editor reach the server as counts that add up to more than the file
        # holds. Recorded as sent.
        return read, {"LM": 64, "LAD": 128, "LCx": 128, "RCA": 64}
    assert case == "empty"
    return np.zeros_like(read), None


@pytest.mark.parametrize("case", ["LAD", "LCx", "RCA", "overlap", "empty"])
def test_a_submit_is_never_refused_for_its_segmentation(world, case):
    import numpy as np
    from girder_segqueue14 import scoring
    from girder_segqueue14.models import Assignment14, Submission14

    from segqueue14 import scoring as sq

    _readyProject(world)
    queue = _resource()
    anna = world.people["anna"]
    _as(anna)
    info = queue.nextCase(clientProtocol=17)
    read, counts = _unchecked(np, case)
    response = _submit(world, queue, anna, info, read, counts=counts, geometry=_GEOMETRY)

    submission = Submission14().load(response["submissionId"], force=True)
    assert submission["voxelCounts"] == (counts or sq.voxel_counts(read))
    assert submission["geometry"] == _GEOMETRY     # recorded, not enforced
    assignment = Assignment14().load(submission["assignmentId"], force=True)
    assert assignment["state"] == "submitted"

    # The worker still scores it; an empty required class is a review flag only.
    scoring.runOnce()
    submission = Submission14().load(response["submissionId"], force=True)
    missing = submission["autoScore"]["missingRequired"]
    if case in ("LAD", "LCx", "RCA"):
        assert missing == [case] and submission["needsReview"] is True
    elif case == "empty":
        assert missing == ["LAD", "LCx", "RCA"] and submission["needsReview"] is True
    else:
        assert missing == []


@pytest.mark.parametrize("case", ["LAD", "LCx", "RCA", "overlap", "empty"])
def test_a_revision_is_never_refused_for_its_segmentation(world, case):
    import numpy as np
    from girder_segqueue14 import scoring
    from girder_segqueue14.models import Assignment14, Submission14

    _readyProject(world)
    queue = _resource()
    bobby, revy = world.people["bobby"], world.people["revy"]
    _as(bobby)
    info = queue.nextCase(clientProtocol=17)
    poor = _tree(np)
    poor[poor == 4] = 3             # poor enough to need a reviewer
    original = _submit(world, queue, bobby, info, poor)["submissionId"]
    scoring.runOnce()
    assert Submission14().load(original, force=True)["needsReview"] is True

    read, counts = _unchecked(np, case)
    _as(revy)
    fileDoc, meta = _uploadSeg(world, revy, info["caseName"], read, counts)
    _as(revy)
    result = queue.revise(submissionId=original, fileId=str(fileDoc["_id"]),
                          meta=json.dumps(meta), clientProtocol=17)
    assert result["state"] == "approved"
    revision = Submission14().load(result["submissionId"], force=True)
    assert revision["voxelCounts"] == meta["voxelCounts"]
    assert revision["authorRole"] == "reviewer"
    assert Assignment14().load(revision["assignmentId"], force=True)["state"] == "approved"


def test_the_kept_checks_still_refuse_a_submit(world):
    """What #270 keeps: role, ownership, the protocol gate and the checksum."""
    import numpy as np

    _readyProject(world)
    queue = _resource()
    anna, bobby = world.people["anna"], world.people["bobby"]
    _as(anna)
    info = queue.nextCase(clientProtocol=17)
    queue.downloadCase(caseId=info["caseId"])
    fileDoc, meta = _uploadSeg(world, anna, info["caseName"], np.zeros((24, 24, 24), np.uint8))
    args = dict(assignmentId=info["assignmentId"], fileId=str(fileDoc["_id"]))

    _as(anna)
    assert _refusal(queue.submit, meta=json.dumps(meta), clientProtocol=16, **args).code == 426
    bad = dict(meta, checksum="0" * 64)
    err = _refusal(queue.submit, meta=json.dumps(bad), clientProtocol=17, **args)
    assert err.extra["segqueueError"] == "checksum_mismatch"
    _as(bobby)                       # an annotator, but not this assignment's
    assert _refusal(queue.submit, meta=json.dumps(meta), clientProtocol=17, **args).code in (
        403, 404)
    outsider = world.people["revy"]  # a reviewer, not an annotator
    _as(outsider)
    assert _refusal(queue.submit, meta=json.dumps(meta), clientProtocol=17, **args).code == 403
    _as(anna)
    assert queue.submit(meta=json.dumps(meta), clientProtocol=17, **args)["submissionId"]


def test_a_poor_read_goes_to_review_with_per_class_reasons(world):
    import numpy as np
    from girder_segqueue14 import scoring
    from girder_segqueue14.models import Assignment14, Submission14

    _readyProject(world)
    queue = _resource()
    _as(world.people["bobby"])
    info = queue.nextCase(clientProtocol=17)
    read = _tree(np)
    read[read == 4] = 3             # the RCA called LCx ...
    read[0, 0, 0] = 4               # ... and one stray voxel of "RCA" elsewhere
    response = _submit(world, queue, world.people["bobby"], info, read)
    scoring.runOnce()
    submission = Submission14().load(response["submissionId"], force=True)
    assert any("RCA" in r for r in submission["autoScore"]["flags"])
    assert submission["needsReview"] is True
    assert Assignment14().load(submission["assignmentId"], force=True)["state"] == "submitted"

    _as(world.people["revy"])
    rows = queue.reviewQueue(limit=10, offset=0)
    assert rows and rows[0]["prelabelVersion"] == "v1"
    assert rows[0]["autoScore"]["per_class_dice"]["RCA"] < 0.7
    assert any("RCA" in r for r in rows[0]["flagged"])
    # Reviewers (only) may fetch the ImageCAS-X reference.
    queue.downloadCaseAsset(caseId=info["caseId"], kind="reference")


def _scoreFiles(world, read, reference):
    """``scoring.scoreAgainst`` on two stored files, ``reference`` an ImageCAS-X one."""
    from girder.models.folder import Folder
    from girder_segqueue14 import scoring

    folder = Folder().createFolder(world.admin, f"scratch-{uuid.uuid4().hex[:6]}",
                                   parentType="user", creator=world.admin)
    # ImageCAS-like voxel size, so "nearest" is measured in mm (array axes are x, y, z).
    spacing = (0.35, 0.35, 0.5)
    readFile = _upload(_nifti(world.data / "scratch_read.nii.gz", read, spacing),
                       folder, world.admin)
    refFile = _upload(_nifti(world.data / "scratch_ref.nii.gz", reference, spacing),
                      folder, world.admin)
    result, _ = scoring.scoreAgainst(readFile, refFile, icx14=True)
    return result


def test_imagecas_x_other_beside_an_lad_is_scored_as_lad(world):
    """#57, D25: "Other" (14: D3/D4, OM3/OM4) takes the class of the nearest LAD/LCx in
    mm, as the icx4 training labels do -- a read that draws that D3 as LAD is right."""
    import numpy as np

    tree = _tree(np)
    reference = _icx(np, tree)
    read = tree.copy()
    lad = np.argwhere(tree == 2)
    x0, x1, y = lad[:, 0].min(), lad[:, 0].max() + 1, lad[:, 1].max() + 1
    assert not tree[x0:x1, y:y + 2].any()
    reference[x0:x1, y:y + 2, 6:14] = 14        # a D3 alongside the LAD block
    read[x0:x1, y:y + 2, 6:14] = 2
    result = _scoreFiles(world, read, reference)
    assert result["per_structure"]["LAD"]["dice"] == 1.0
    assert result["mean_dice"] == 1.0


def test_imagecas_x_reference_with_nothing_above_four_is_still_collapsed(world):
    """#57: which labels a reference speaks is decided by what it is, not by its
    highest value. LM, LAD, LCx and a D1 (4) -- no RCA: the 4 is LAD, not RCA."""
    import numpy as np

    tree = _tree(np)
    reference = tree.copy()                      # 1 LM, 2 LAD, 3 LCx, 4 = D1
    read = tree.copy()
    read[tree == 4] = 2                          # the D1, drawn as LAD
    result = _scoreFiles(world, read, reference)
    assert result["per_structure"]["LAD"]["dice"] == 1.0
    assert result["per_structure"]["RCA"]["voxels_ref"] == 0


def test_a_reviewer_sees_who_sent_what_and_under_which_filenames(world):
    import numpy as np
    from bson import ObjectId
    from girder_segqueue14 import scoring

    _readyProject(world)
    queue = _resource()
    _as(world.people["bobby"])
    info = queue.nextCase(clientProtocol=17)
    read = _tree(np)
    read[read == 4] = 3             # poor enough to need a reviewer,
    read[0, 0, 0] = 4               # but with every required class present
    response = _submit(world, queue, world.people["bobby"], info, read)
    scoring.runOnce()

    _as(world.people["revy"])
    row = queue.getSubmission(submissionId=response["submissionId"])
    bobby = world.people["bobby"]
    assert row["annotator"] == {"id": str(bobby["_id"]), "login": "bobby",
                                "name": "bobby X"}
    # The filenames Slicer picks its reader from travel with the row.
    assert row["volumeName"] == f"{info['caseName']}.nii.gz"
    assert row["submissionName"].endswith(".seg.nrrd")
    assert isinstance(row["submittedAt"], str) and row["history"] == []

    [history] = queue.caseSubmissions(caseId=info["caseId"])
    assert history["submissionId"] == response["submissionId"]
    assert history["revisionOf"] is None and isinstance(history["created"], str)

    listed = {r["caseId"]: r for r in queue.listCases(state="submitted")}
    [lease] = listed[info["caseId"]]["assignments"]
    assert lease["annotator"] == "bobby" and lease["submissionCount"] == 1

    missing = str(ObjectId())
    for call in (queue.caseSubmissions, queue.downloadCaseVolume):
        err = _refusal(call, caseId=missing)
        assert err.code == 404 and err.extra["segqueueError"] == "no_such_case"
    err = _refusal(queue.assignCase, caseId=missing, userId=str(bobby["_id"]))
    assert err.extra["segqueueError"] == "no_such_case"


def test_a_two_read_case_is_decided_when_both_reads_are_in(world):
    import numpy as np
    from girder_segqueue14 import scoring
    from girder_segqueue14.models import Case14, Submission14

    _readyProject(world)
    queue = _resource()
    # Put only the unlabelled tier in the queue.
    Case14().collection.update_many({"tier": {"$ne": "imagecas-unlabelled"}},
                                    {"$set": {"retired": True}})
    _as(world.people["anna"])
    first = queue.nextCase(clientProtocol=17)
    _as(world.people["bobby"])
    second = queue.nextCase(clientProtocol=17)
    assert first["caseId"] == second["caseId"], "both slots of the first two-read case"

    a = _submit(world, queue, world.people["anna"], first, _tree(np))
    assert scoring.runOnce() == 0, "the first read waits for its partner"
    b = _submit(world, queue, world.people["bobby"], second, _tree(np))
    assert scoring.runOnce() == 2
    for sid in (a["submissionId"], b["submissionId"]):
        sub = Submission14().load(sid, force=True)
        assert sub["kind"] == "paired" and sub["autoScore"]["duplicate"]["mean_dice"] == 1.0
    case = Case14().load(first["caseId"], force=True)
    assert case["approvedCount"] == 2 and case["activeCount"] == 0


def test_export_writes_four_masks_per_approved_read(world, tmp_path):
    import numpy as np
    from girder_segqueue14 import export, scoring

    _readyProject(world)
    queue = _resource()
    _as(world.people["cathy"])
    info = queue.nextCase(clientProtocol=17)
    _submit(world, queue, world.people["cathy"], info, _tree(np))
    scoring.runOnce()
    out = tmp_path / "export"
    assert export.main(["--out", str(out)]) == 0
    masks = sorted(p.name for p in (out / info["caseName"] / "segmentations").iterdir())
    assert masks == ["LAD.nii.gz", "LCx.nii.gz", "LM.nii.gz", "RCA.nii.gz"]
    manifest = json.loads((out / "manifest.json").read_text())
    assert manifest["source"]["label_set"] == "coronary_icx4"
    assert manifest["source"]["prelabel_versions"][info["caseName"]] == "v1"


# ------------------------------------------------- D39 (#275): every class whole


def _stackOf(np, classes, names=None):
    """``classes`` (``{name: 0/1 array in _tree's x, y, z order}``) as a class stack's
    masks, in ``names`` order (default the project's four) and SimpleITK's (z, y, x)
    order. Missing classes are empty."""
    from segqueue14 import labels

    shape = next(iter(classes.values())).shape
    return [np.ascontiguousarray((classes.get(name, np.zeros(shape, np.uint8)) != 0)
                                 .astype(np.uint8).transpose(2, 1, 0))
            for name in (labels.NAMES if names is None else names)]


def _uploadStack(world, user, caseName, masks, names=None):
    """Write ``masks`` as the 0.17.0 module does -- a class stack on the CT grid -- and
    upload it as ``user``. ``names`` are the channels (default the four; all 21 for
    an extended read, as 0.18.0 writes it). Returns ``(file document, SubmissionMeta
    dict)``."""
    import SimpleITK as sitk
    from girder_segqueue14.utils import incomingFolder

    from segqueue14 import labelfile, labels

    ct = sitk.ReadImage(str(world.data / f"{caseName}.nii.gz"))
    d, sp, o = ct.GetDirection(), ct.GetSpacing(), ct.GetOrigin()
    ijkToLps = [[d[3 * r + c] * sp[c] for c in range(3)] + [o[r]] for r in range(3)]
    names = list(labels.NAMES if names is None else names)
    path = world.data / f"{caseName}_{user['login']}_{uuid.uuid4().hex[:6]}.seg.nrrd"
    labelfile.write_class_stack(str(path), masks, names, ijkToLps)
    fileDoc = _upload(path, incomingFolder(world.admin), user)
    meta = {"checksum": _sha(path), "sizeBytes": os.path.getsize(path),
            "annotationSeconds": 300.0,
            "voxelCounts": {n: int((m != 0).sum()) for n, m in zip(names, masks)},
            "extensionVersion": "0.18.0" if labels.is_extended(names) else "0.17.0"}
    return fileDoc, meta


def _submitStack(world, queue, user, info, masks, labelFormat="class-stack-nrrd/1",
                 names=None, clientProtocol=17):
    _as(user)
    queue.downloadCase(caseId=info["caseId"])
    fileDoc, meta = _uploadStack(world, user, info["caseName"], masks, names=names)
    _as(user)
    return queue.submit(assignmentId=info["assignmentId"], fileId=str(fileDoc["_id"]),
                        meta=json.dumps(meta), labelFormat=labelFormat,
                        clientProtocol=clientProtocol)


def _storedStack(world, submission):
    """The stored file of ``submission``, read back without Slicer."""
    from girder.models.file import File

    from segqueue14 import labelfile

    path = world.data / f"stored_{uuid.uuid4().hex[:6]}.seg.nrrd"
    fileDoc = File().load(submission["fileId"], force=True)
    with open(path, "wb") as out:
        for chunk in File().download(fileDoc, headers=False)():
            out.write(chunk)
    assert labelfile.sniff(str(path)) == labelfile.FORMAT_CLASS_STACK
    return labelfile.read_class_stack(str(path))


def test_an_untouched_seeded_case_keeps_all_four_classes_whole(world, tmp_path):
    """#275: four identical full copies (D26, nothing trimmed) are stored, counted,
    scored, opened by a reviewer and exported as four whole classes -- not as all RCA."""
    import numpy as np
    from girder_segqueue14 import export, scoring
    from girder_segqueue14.models import Submission14

    from segqueue14 import labels

    _readyProject(world)
    queue = _resource()
    cathy = world.people["cathy"]
    _as(cathy)
    info = queue.nextCase(clientProtocol=17)
    tree = (_tree(np) > 0).astype(np.uint8)
    whole = int(tree.sum())
    masks = _stackOf(np, {name: tree for name in labels.NAMES})
    response = _submitStack(world, queue, cathy, info, masks)

    submission = Submission14().load(response["submissionId"], force=True)
    assert submission["labelFormat"] == "class-stack-nrrd/1"
    assert submission["voxelCounts"] == {name: whole for name in labels.NAMES}
    stored = _storedStack(world, submission)
    assert stored["names"] == labels.NAMES
    assert [int(m.sum()) for m in stored["masks"]] == [whole] * 4

    scoring.runOnce()
    submission = Submission14().load(response["submissionId"], force=True)
    score = submission["autoScore"]
    assert score["voxelCounts"] == {name: whole for name in labels.NAMES}
    assert score["missingRequired"] == []
    ref = score["reference"]["per_structure"]
    # Every class is scored from its own whole mask against the reference.
    assert all(ref[name]["voxels_read"] == whole for name in labels.NAMES)
    assert all(0 < ref[name]["dice"] < 1 for name in labels.NAMES)

    _as(world.people["revy"])
    row = queue.getSubmission(submissionId=response["submissionId"])
    assert row["labelFormat"] == "class-stack-nrrd/1"

    Submission14().collection.update_one({"_id": submission["_id"]},
                                         {"$set": {"needsReview": False}})
    from girder_segqueue14.models import Assignment14

    Assignment14().collection.update_one({"_id": submission["assignmentId"]},
                                         {"$set": {"state": "approved"}})
    out = tmp_path / "export"
    assert export.main(["--out", str(out)]) == 0
    import nibabel as nib

    for name in labels.NAMES:
        mask = np.asarray(nib.load(str(out / info["caseName"] / "segmentations"
                                       / f"{name}.nii.gz")).dataobj)
        assert int((mask > 0).sum()) == whole, name
        assert np.array_equal(mask > 0, tree > 0), name


def test_a_partly_trimmed_case_keeps_every_class_s_own_voxels(world, tmp_path):
    import numpy as np
    from girder_segqueue14 import scoring
    from girder_segqueue14.models import Submission14

    _readyProject(world)
    queue = _resource()
    anna = world.people["anna"]
    _as(anna)
    info = queue.nextCase(clientProtocol=17)
    tree = _tree(np)
    classes = {name: (tree == value).astype(np.uint8)
               for name, value in (("LM", 1), ("LAD", 2), ("LCx", 3), ("RCA", 4))}
    classes["LAD"] = classes["LAD"] | classes["LCx"]     # LAD not yet cut off the LCx
    response = _submitStack(world, queue, anna, info, _stackOf(np, classes))
    scoring.runOnce()

    submission = Submission14().load(response["submissionId"], force=True)
    stored = _storedStack(world, submission)
    for name, mask in zip(stored["names"], stored["masks"]):
        assert np.array_equal(mask != 0, classes[name].transpose(2, 1, 0) != 0), name
    ref = submission["autoScore"]["reference"]["per_structure"]
    assert ref["LCx"]["dice"] == 1.0 and ref["LM"]["dice"] == 1.0 and ref["RCA"]["dice"] == 1.0
    assert ref["LAD"]["voxels_read"] == int(classes["LAD"].sum())
    assert ref["LAD"]["dice"] < 1.0


def test_a_revision_round_trips_as_a_class_stack(world):
    import numpy as np
    from girder_segqueue14 import scoring
    from girder_segqueue14.models import Submission14

    from segqueue14 import labels

    _readyProject(world)
    queue = _resource()
    bobby, revy = world.people["bobby"], world.people["revy"]
    _as(bobby)
    info = queue.nextCase(clientProtocol=17)
    tree = (_tree(np) > 0).astype(np.uint8)
    original = _submitStack(world, queue, bobby, info,
                            _stackOf(np, {name: tree for name in labels.NAMES}))["submissionId"]
    scoring.runOnce()

    masks = _stackOf(np, {name: tree for name in labels.NAMES})
    _as(revy)
    fileDoc, meta = _uploadStack(world, revy, info["caseName"], masks)
    _as(revy)
    assert _refusal(queue.revise, submissionId=original, fileId=str(fileDoc["_id"]),
                    meta=json.dumps(meta), clientProtocol=16).code == 426
    result = queue.revise(submissionId=original, fileId=str(fileDoc["_id"]),
                          meta=json.dumps(meta), labelFormat="class-stack-nrrd/1",
                          clientProtocol=17)
    revision = Submission14().load(result["submissionId"], force=True)
    assert revision["labelFormat"] == "class-stack-nrrd/1"
    assert revision["voxelCounts"] == {name: int(tree.sum()) for name in labels.NAMES}
    stored = _storedStack(world, revision)
    assert [int(m.sum()) for m in stored["masks"]] == [int(tree.sum())] * 4


def test_a_0_16_module_is_told_to_update_and_formats_are_recorded_as_stored(world):
    """A 0.16.5 module (protocol 16) writes one label volume and loses overlapping
    classes: refused with the update message. An unknown format name is refused; a
    declared format is recorded as the stored bytes say, and a submission without one
    is an old label volume."""
    import numpy as np
    from girder_segqueue14.models import Submission14

    _readyProject(world)
    queue = _resource()
    anna = world.people["anna"]
    _as(anna)
    info = queue.nextCase(clientProtocol=17)
    queue.downloadCase(caseId=info["caseId"])
    fileDoc, meta = _uploadSeg(world, anna, info["caseName"], _tree(np))
    args = dict(assignmentId=info["assignmentId"], fileId=str(fileDoc["_id"]),
                meta=json.dumps(meta))
    _as(anna)
    err = _refusal(queue.submit, clientProtocol=16, **args)
    assert err.code == 426 and "Update the SegQueue14 module" in err.extra["message"]
    err = _refusal(queue.submit, labelFormat="png", clientProtocol=17, **args)
    assert err.code == 400 and err.extra["segqueueError"] == "bad_label_format"
    # Declared a class stack, uploaded a label volume: the bytes win.
    response = queue.submit(labelFormat="class-stack-nrrd/1", clientProtocol=17, **args)
    assert Submission14().load(response["submissionId"], force=True)["labelFormat"] == "labelmap"


def test_old_label_volume_submissions_still_score_and_export(world, tmp_path):
    """Everything stored before protocol 17 is one label volume: no labelFormat on the
    row, and it scores and exports exactly as before."""
    import numpy as np
    from girder_segqueue14 import export, scoring
    from girder_segqueue14.models import Submission14

    _readyProject(world)
    queue = _resource()
    _as(world.people["cathy"])
    info = queue.nextCase(clientProtocol=17)
    response = _submit(world, queue, world.people["cathy"], info, _tree(np))
    Submission14().collection.update_one({"_id": __import__("bson").ObjectId(
        response["submissionId"])}, {"$unset": {"labelFormat": ""}})
    scoring.runOnce()
    submission = Submission14().load(response["submissionId"], force=True)
    assert submission["autoScore"]["reference"]["mean_dice"] == 1.0
    _as(world.people["revy"])
    assert queue.getSubmission(submissionId=response["submissionId"])["labelFormat"] == "labelmap"
    out = tmp_path / "export"
    assert export.main(["--out", str(out)]) == 0
    import nibabel as nib

    lad = np.asarray(nib.load(str(out / info["caseName"] / "segmentations"
                                  / "LAD.nii.gz")).dataobj)
    assert int((lad > 0).sum()) == int((_tree(np) == 2).sum())


def test_export_leaves_a_d27_sealed_case_out_unless_acceptance_scoring(world, tmp_path, capsys):
    import numpy as np
    from girder_segqueue14 import export, scoring
    from girder_segqueue14.models import Case14

    seal = json.loads((Path(__file__).resolve().parents[1] / "configs" / "segqueue14"
                       / "sealed-pool-2026-10.json").read_text())
    sealedName = seal["primary"]["volumes"][0][: -len(".nii.gz")]
    _readyProject(world)
    queue = _resource()
    _as(world.people["cathy"])
    info = queue.nextCase(clientProtocol=17)
    _submit(world, queue, world.people["cathy"], info, _tree(np))
    scoring.runOnce()
    case = Case14().findOne({"name": info["caseName"]})
    Case14().update({"_id": case["_id"]}, {"$set": {"name": sealedName}})

    out = tmp_path / "export"
    assert export.main(["--out", str(out)]) == 0
    assert not (out / sealedName).exists()
    assert "1 D27 sealed pool case(s) left out" in capsys.readouterr().out

    accepted = tmp_path / "acceptance"
    assert export.main(["--out", str(accepted), "--acceptance-scoring"]) == 0
    assert (accepted / sealedName / "segmentations" / "LM.nii.gz").is_file()
    manifest = json.loads((accepted / "manifest.json").read_text())
    assert manifest["source"]["pool_seal"]["mode"] == "acceptance"
    assert manifest["source"]["pool_seal"]["included_reads"] == 1


def test_admin_prelabel_route_and_stats(world):
    from girder_segqueue14.models import Case14

    _populate(world)
    queue = _resource()
    path = _predictions(world, "v1", names=[1]) / "c0000.nii.gz"
    from girder_segqueue14.utils import incomingFolder

    fileDoc = _upload(path, incomingFolder(world.admin), world.admin)
    _as(world.admin)
    dry = queue.attachPrelabel(caseName="imagecas_0001", fileId=str(fileDoc["_id"]),
                               modelVersion="v1", includeTest=False, dryRun=True)
    assert dry["action"] == "attach" and Case14().findOne(
        {"name": "imagecas_0001"})["prelabelVersion"] == ""
    done = queue.attachPrelabel(caseName="imagecas_0001", fileId=str(fileDoc["_id"]),
                                modelVersion="v1", includeTest=False, dryRun=False)
    assert done["prelabelVersion"] == "v1"
    status = queue.prelabelStatus()
    assert status["byVersion"]["v1"] == {"icx-trainval": 1}
    assert status["withoutPrelabel"] == 11
    stats = queue.stats()
    assert stats["tiers"]["icx-test"]["cases"] == 2
    assert stats["tiers"]["imagecas-unlabelled"]["readsWanted"] == 6


def test_an_auto_screener_note_is_added_once_and_shown_as_system(world):
    from girder_segqueue14.models import Case14, Note14

    _populate(world)
    queue = _resource()
    _as(world.admin)
    first = queue.addAutoNote(caseName="imagecas_0001", text="Seed looks complete.",
                              author="auto screener", once=True)
    assert first["created"] is True
    again = queue.addAutoNote(caseName="imagecas_0001", text="Second opinion.",
                              author="auto screener", once=True)
    assert again["created"] is False
    case = Case14().findOne({"name": "imagecas_0001"})
    thread = Note14().forCase(case["_id"])
    assert [(n["author"], n["system"], n["authorId"]) for n in thread] == [
        ("auto screener", True, None)]
    assert thread[0]["text"] == "Seed looks complete."
    missing = _refusal(queue.addAutoNote, caseName="no_such_case", text="x",
                       author="auto screener", once=True)
    assert missing.code == 404


def test_both_plugins_load_side_by_side(world):
    from girder.models.group import Group
    from girder_segqueue import SegQueuePlugin
    from girder_segqueue14 import SegQueue14Plugin

    class Root:
        pass

    root = Root()
    info = {"apiRoot": root}
    # Built without an entry point: that plumbing is Girder's, not under test.
    for cls, name in ((SegQueuePlugin, "segqueue"), (SegQueue14Plugin, "segqueue14")):
        plugin = object.__new__(cls)
        plugin._name = name
        plugin.load(info)
    assert root.segqueue.resourceName == "segqueue"
    assert root.segqueue14.resourceName == "segqueue14"
    names = {g["name"] for g in Group().find({})}
    assert {"segqueue-annotators", "segqueue-reviewers", "segqueue14-annotators",
            "segqueue14-reviewers"} <= names


def test_the_command_lines_dry_run_and_change_nothing(world, capsys):
    from girder_segqueue14 import populate, prelabels
    from girder_segqueue14.models import Case14

    before = _liveSnapshot(world)
    assert populate.main(["--dry-run"]) == 0
    assert Case14().collection.count_documents({}) == 0
    out = capsys.readouterr().out
    assert "would create 12" in out and "icx-test" in out
    assert populate.main([]) == 0
    directory = _predictions(world, "v1")
    assert prelabels.main(["attach", "--dir", str(directory), "--model-version", "v1",
                           "--dry-run"]) == 0
    assert Case14().collection.count_documents({"prelabelVersion": "v1"}) == 0
    assert prelabels.main(["attach", "--dir", str(directory), "--model-version", "v1"]) == 0
    assert Case14().collection.count_documents({"prelabelVersion": "v1"}) == 12
    assert prelabels.main(["status"]) == 0
    assert "v1: 12 case(s)" in capsys.readouterr().out
    with pytest.raises(SystemExit):
        prelabels.main(["attach", "--dir", str(directory), "--model-version", "../x"])
    assert _liveSnapshot(world) == before


def test_a_broken_or_disabled_segqueue14_never_stops_girder(world, monkeypatch):
    import girder_segqueue14
    from girder_segqueue14 import SegQueue14Plugin

    class Root:
        pass

    def fresh():
        plugin = object.__new__(SegQueue14Plugin)
        plugin._name = "segqueue14"
        return plugin

    monkeypatch.setenv("SEGQUEUE14_DISABLE", "1")
    root = Root()
    fresh().load({"apiRoot": root})
    assert not hasattr(root, "segqueue14")

    monkeypatch.delenv("SEGQUEUE14_DISABLE")
    monkeypatch.setattr(girder_segqueue14, "mount",
                        lambda info: (_ for _ in ()).throw(RuntimeError("boom")))
    root = Root()
    fresh().load({"apiRoot": root})       # logged, not raised
    assert not hasattr(root, "segqueue14")
    monkeypatch.setenv("SEGQUEUE14_STRICT", "1")
    with pytest.raises(RuntimeError):
        fresh().load({"apiRoot": root})


# ------------------------------------------------------------- the pool (D23)
# Last in the file: pool cases are priority 200, above the held-out test cases,
# so they must not exist while the serve-order tests run.


def test_the_pool_creates_listed_cases_with_their_seeds_and_attaches_late_seeds(world):
    import numpy as np
    from girder.models.collection import Collection
    from girder.models.folder import Folder
    from girder.models.item import Item
    from girder_segqueue14 import populate
    from girder_segqueue14.models import Case14
    from girder_segqueue14.rest.queue import assignmentInfo

    before = _liveSnapshot(world)
    coll = Collection().createCollection("PoolTest", creator=world.admin, public=False)
    cases = Folder().createFolder(coll, "cases", parentType="collection", creator=world.admin)
    seeds = Folder().createFolder(coll, "seeds", parentType="collection", creator=world.admin)
    names = ["SetA__p1.nii.gz", "SetA__p2.nii.gz", "SetB__x9.nii.gz"]
    for name in names + ["SetC__unlisted.nii.gz"]:
        ct = _upload(_nifti(world.data / name, np.full((8, 8, 8), 300, np.int16)), cases,
                     world.admin)
        Item().setMetadata(Item().load(ct["itemId"], force=True), {"source": name.split("__")[0]})
    seedArray = np.zeros((8, 8, 8), np.uint8)
    seedArray[2:5, 2:5, 2:5] = 1
    for name in names[:2]:
        seedName = name.replace(".nii.gz", "__totalseg-coronary.nii.gz")
        _upload(_nifti(world.data / seedName, seedArray), seeds, world.admin)

    lines = []
    kwargs = dict(poolFolderId=cases["_id"], seedFolderId=seeds["_id"], startOrder=1000,
                  out=lines.append)
    dry = populate.populatePool(world.admin, names + ["SetZ__missing.nii.gz"], dryRun=True,
                                **kwargs)
    assert dry["create"] == 3 and dry["missing"] == 1 and Case14().findOne(
        {"name": "SetA__p1"}) is None
    held = populate.populatePool(world.admin, names, requireSeed=True, **kwargs)
    assert held["create"] == 2 and held["noSeed"] == 1
    assert Case14().findOne({"name": "SetB__x9"}) is None

    summary = populate.populatePool(world.admin, names, **kwargs)
    assert summary["create"] == 1 and summary["same"] == 2
    # Serve order is the list position, whichever run created the case.
    assert [Case14().findOne({"name": n[:-7]})["serveOrder"] for n in names] == [1000, 1001, 1002]
    p1 = Case14().findOne({"name": "SetA__p1"})
    assert p1["dataset"] == "SetA" and p1["tier"] == "new-dataset"
    assert p1["replicasWanted"] == 2 and p1["referenceFileId"] is None
    assert p1["seedFileId"] and "TotalSegmentator" in p1["seedSource"]
    assert len(p1["checksum"]) == 64
    assert Case14().findOne({"name": "SetC__unlisted"}) is None
    x9 = Case14().findOne({"name": "SetB__x9"})
    assert x9["seedFileId"] is None

    # The seed for x9 arrives later: a plain re-run attaches it, nothing else changes.
    _upload(_nifti(world.data / "SetB__x9__totalseg-coronary.nii.gz", seedArray), seeds,
            world.admin)
    again = populate.populatePool(world.admin, names, **kwargs)
    assert again["seed"] == 1 and again["same"] == 2 and again["create"] == 0
    x9 = Case14().findOne({"name": "SetB__x9"})
    assert x9["seedFileId"]

    # The annotator is told there is a seed, and a reviewer can fetch it.
    info = assignmentInfo({"_id": x9["_id"], "caseId": x9["_id"], "state": "assigned"})
    assert info.has_seed and not info.has_prelabel
    api = _resource()
    _as(world.people["revy"])
    api.downloadCaseAsset(caseId=str(x9["_id"]), kind="seed")

    # Nothing of the live project changed; the pool cases are retired again so
    # the run leaves the queue as the tests above expect it.
    assert _liveSnapshot(world) == before
    Case14().collection.update_many({"dataset": {"$in": ["SetA", "SetB"]}},
                                    {"$set": {"retired": True}})


# ------------------------------------- D44 (#280): the optional extended classes


def _protocolHeader(version):
    """Send ``version`` the way every module sends it on every request: the header."""
    import cherrypy

    from segqueue14 import protocol

    if version is None:
        cherrypy.request.headers.pop(protocol.PROTOCOL_HEADER, None)
    else:
        cherrypy.request.headers[protocol.PROTOCOL_HEADER] = str(version)


@pytest.fixture
def header():
    yield _protocolHeader
    _protocolHeader(None)


def _fourOf(np, tree):
    """``tree``'s four classes as ``{name: 0/1 array}``."""
    from segqueue14 import labels

    return {name: (tree == labels.LABEL_VALUES[name]).astype(np.uint8)
            for name in labels.NAMES}


#: Where ``_extendedOf`` moves branches to, as ``(class, parent, x-slice)`` inside
#: the parent's block of ``_tree``, which spans x 6:14 on axis 2.
_MOVES = (("D1", "LAD", slice(10, 12)), ("S1", "LAD", slice(12, 14)),
          ("OM1", "LCx", slice(10, 12)), ("Ramus", "LCx", slice(12, 14)),
          ("SN", "RCA", slice(10, 12)), ("PDA", "RCA", slice(12, 14)))


def _extendedOf(np, tree, materials=("Stent", "Calcified plaque")):
    """``tree`` as a 21-class read: branches moved out of their parents into their
    own classes, and materials painted over the LAD (stent) and RCA (plaque). The
    same vessel voxels as ``_fourOf(tree)`` once collapsed."""
    from segqueue14 import labels

    classes = _fourOf(np, tree)
    shape = tree.shape
    for name in labels.EXTRA_NAMES:
        classes[name] = np.zeros(shape, np.uint8)
    for name, parent, xs in _MOVES:
        block = np.zeros(shape, bool)
        block[..., xs] = classes[parent][..., xs] != 0
        classes[name][block] = 1
        classes[parent][block] = 0
    paint = {"Stent": ("LAD", slice(6, 8)), "Calcified plaque": ("RCA", slice(6, 7)),
             "Non-calcified plaque": ("LCx", slice(6, 7))}
    for name in materials:
        vessel, xs = paint[name]
        source = _fourOf(np, tree)[vessel]
        classes[name][..., xs] = source[..., xs]
    return classes


def _poor(np):
    """A read poor enough to go to a reviewer, every required class present."""
    read = _tree(np)
    read[read == 4] = 3
    read[0, 0, 0] = 4
    return read


def test_an_extended_read_is_stored_scored_and_exported_whole(world, tmp_path):
    """A 21-class read: stored with its classes, scored collapsed to the four (a
    perfect read stays perfect), shown to reviewers as extended, exported with all
    its classes, and with --four-class collapsed."""
    import nibabel as nib
    import numpy as np
    from girder_segqueue14 import export, scoring
    from girder_segqueue14.models import Assignment14, Submission14

    from segqueue14 import labels

    _readyProject(world)
    queue = _resource()
    cathy = world.people["cathy"]
    _as(cathy)
    info = queue.nextCase(clientProtocol=18)
    tree = _tree(np)
    classes = _extendedOf(np, tree)
    response = _submitStack(world, queue, cathy, info,
                            _stackOf(np, classes, labels.ALL_NAMES),
                            names=labels.ALL_NAMES, clientProtocol=18)

    submission = Submission14().load(response["submissionId"], force=True)
    assert submission["classes"] == labels.ALL_NAMES and submission["extended"] is True
    assert _storedStack(world, submission)["names"] == labels.ALL_NAMES

    scoring.runOnce()
    submission = Submission14().load(response["submissionId"], force=True)
    score = submission["autoScore"]
    ref = score["reference"]
    # Collapsed, the read is exactly the reference's four classes.
    assert ref["mean_dice"] == 1.0
    assert all(ref["per_structure"][n]["dice"] == 1.0 for n in labels.NAMES)
    assert ref["extended"] == {"read": True, "reference": False}
    assert "materials" not in ref                   # ImageCAS-X has none
    assert score["voxelCounts"] == {n: int((tree == labels.LABEL_VALUES[n]).sum())
                                    for n in labels.NAMES}
    assert Assignment14().load(submission["assignmentId"], force=True)["state"] == "approved"

    _as(world.people["revy"])
    row = queue.getSubmission(submissionId=response["submissionId"])
    assert row["extended"] is True and row["classes"] == labels.ALL_NAMES
    [lease] = [r for r in queue.listCases(state="approved")
               if r["caseId"] == info["caseId"]][0]["assignments"]
    assert lease["extended"] is True

    out = tmp_path / "export"
    assert export.main(["--out", str(out)]) == 0
    folder = out / info["caseName"] / "segmentations"
    names = sorted(p.name for p in folder.iterdir())
    assert len(names) == 21 and "Calcified_plaque.nii.gz" in names
    d1 = np.asarray(nib.load(str(folder / "D1.nii.gz")).dataobj)
    assert np.array_equal(d1 > 0, classes["D1"] > 0)
    manifest = json.loads((out / "manifest.json").read_text())
    assert manifest["source"]["classes"] == "read"
    assert manifest["source"]["extended_reads"] == [info["caseName"]]

    four = tmp_path / "four"
    assert export.main(["--out", str(four), "--four-class"]) == 0
    folder = four / info["caseName"] / "segmentations"
    assert sorted(p.name for p in folder.iterdir()) == \
        ["LAD.nii.gz", "LCx.nii.gz", "LM.nii.gz", "RCA.nii.gz"]
    for name in labels.NAMES:
        mask = np.asarray(nib.load(str(folder / f"{name}.nii.gz")).dataobj)
        assert np.array_equal(mask > 0, tree == labels.LABEL_VALUES[name]), name
    assert json.loads((four / "manifest.json").read_text())["source"]["classes"] == "four"


def test_the_collapsed_score_equals_the_four_class_score_of_the_same_voxels(world):
    """Against the ImageCAS-X reference, an imperfect extended read scores exactly as
    the same voxels drawn into the parents do."""
    import numpy as np
    from girder.models.folder import Folder
    from girder_segqueue14 import scoring

    from segqueue14 import labels

    _readyProject(world)
    queue = _resource()
    anna = world.people["anna"]
    _as(anna)
    info = queue.nextCase(clientProtocol=18)
    read = _tree(np, shift=1)                         # off by a voxel: Dice below 1
    extended = _stackOf(np, _extendedOf(np, read), labels.ALL_NAMES)
    drawn = _stackOf(np, _fourOf(np, read))
    folder = Folder().createFolder(world.admin, f"scratch-{uuid.uuid4().hex[:6]}",
                                   parentType="user", creator=world.admin)
    extFile, _ = _uploadStack(world, anna, info["caseName"], extended, names=labels.ALL_NAMES)
    fourFile, _ = _uploadStack(world, anna, info["caseName"], drawn)
    from girder.models.file import File
    from girder_segqueue14.models import Case14

    case = Case14().load(info["caseId"], force=True)
    reference = File().load(case["referenceFileId"], force=True)
    got, gotMasks = scoring.scoreAgainst(extFile, reference, icx14=True)
    want, wantMasks = scoring.scoreAgainst(fourFile, reference, icx14=True)
    assert folder is not None
    assert 0 < want["mean_dice"] < 1
    assert got["per_structure"] == want["per_structure"]
    assert got["mean_dice"] == want["mean_dice"]
    assert got["required_min_dice"] == want["required_min_dice"]
    assert np.array_equal(gotMasks, wantMasks)
    assert "extended" not in want and got["extended"]["read"] is True


def test_a_protocol_17_module_still_logs_in_fetches_submits_and_reviews(world, header):
    """D44: 0.17.x is not 426'd. It logs in, gets a case, submits four classes, and
    a 0.17.x reviewer claims, opens and revises a four-class read."""
    import numpy as np
    from girder_segqueue14 import scoring
    from girder_segqueue14.models import Submission14

    from segqueue14 import labels

    _readyProject(world)
    queue = _resource()
    bobby, revy = world.people["bobby"], world.people["revy"]
    header(17)
    _as(bobby)
    assert [s["name"] for s in queue.getProject(clientProtocol=17)["segments"]] == labels.NAMES
    info = queue.nextCase(clientProtocol=17)
    sid = _submitStack(world, queue, bobby, info, _stackOf(np, _fourOf(np, _poor(np))),
                       clientProtocol=17)["submissionId"]
    assert Submission14().load(sid, force=True)["extended"] is False
    scoring.runOnce()

    _as(revy)
    queue.claim(submissionId=sid)
    assert callable(queue.downloadSubmission(submissionId=sid))
    fileDoc, meta = _uploadStack(world, revy, info["caseName"],
                                 _stackOf(np, _fourOf(np, _tree(np))))
    _as(revy)
    result = queue.revise(submissionId=sid, fileId=str(fileDoc["_id"]),
                          meta=json.dumps(meta), labelFormat="class-stack-nrrd/1",
                          clientProtocol=17)
    assert result["state"] == "approved"
    revision = Submission14().load(result["submissionId"], force=True)
    assert revision["classes"] == labels.NAMES and revision["extended"] is False


def test_a_protocol_17_reviewer_is_refused_only_on_an_extended_read(world, header):
    import numpy as np
    from girder_segqueue14 import scoring
    from girder_segqueue14.models import Submission14

    from segqueue14 import labels

    _readyProject(world)
    queue = _resource()
    anna, bobby, revy = (world.people[n] for n in ("anna", "bobby", "revy"))
    _as(anna)
    first = queue.nextCase(clientProtocol=18)
    extended = _submitStack(world, queue, anna, first,
                            _stackOf(np, _extendedOf(np, _poor(np)), labels.ALL_NAMES),
                            names=labels.ALL_NAMES, clientProtocol=18)["submissionId"]
    _as(bobby)
    second = queue.nextCase(clientProtocol=17)
    four = _submitStack(world, queue, bobby, second,
                        _stackOf(np, _fourOf(np, _poor(np))))["submissionId"]
    scoring.runOnce()

    _as(revy)
    header(17)
    for call in (queue.claim, queue.downloadSubmission):
        err = _refusal(call, submissionId=extended)
        assert err.code == 426 and err.extra["segqueueError"] == "update_to_review"
        assert "Update SegQueue14 to review this read" in err.extra["message"]
    fileDoc, meta = _uploadStack(world, revy, first["caseName"],
                                 _stackOf(np, _fourOf(np, _tree(np))))
    _as(revy)
    err = _refusal(queue.revise, submissionId=extended, fileId=str(fileDoc["_id"]),
                   meta=json.dumps(meta), labelFormat="class-stack-nrrd/1",
                   clientProtocol=17)
    assert err.code == 426 and err.extra["segqueueError"] == "update_to_review"
    assert Submission14().countForAssignment(
        Submission14().load(extended, force=True)["assignmentId"]) == 1
    # The four-class read is unaffected.
    queue.claim(submissionId=four)
    assert callable(queue.downloadSubmission(submissionId=four))
    # No protocol at all is not a module (a browser): it may download, never save.
    header(None)
    assert callable(queue.downloadSubmission(submissionId=extended))

    # The 0.18 module opens and revises it with every class.
    header(18)
    queue.claim(submissionId=extended)
    assert callable(queue.downloadSubmission(submissionId=extended))
    fileDoc, meta = _uploadStack(world, revy, first["caseName"],
                                 _stackOf(np, _extendedOf(np, _tree(np)), labels.ALL_NAMES),
                                 names=labels.ALL_NAMES)
    _as(revy)
    result = queue.revise(submissionId=extended, fileId=str(fileDoc["_id"]),
                          meta=json.dumps(meta), labelFormat="class-stack-nrrd/1",
                          clientProtocol=18)
    revision = Submission14().load(result["submissionId"], force=True)
    assert revision["classes"] == labels.ALL_NAMES and revision["extended"] is True
    assert _storedStack(world, revision)["names"] == labels.ALL_NAMES
    original = Submission14().load(extended, force=True)
    assert _storedStack(world, original)["names"] == labels.ALL_NAMES


def test_an_extended_read_pairs_with_a_four_class_read(world):
    """Two-read cases: an extended read pairs with a four-class one (collapsed, the
    same voxels: Dice 1.0, no materials); two extended reads also get a Dice per
    material both have."""
    import numpy as np
    from girder_segqueue14 import scoring
    from girder_segqueue14.models import Case14, Submission14

    from segqueue14 import labels

    _readyProject(world)
    queue = _resource()
    Case14().collection.update_many({"tier": {"$ne": "imagecas-unlabelled"}},
                                    {"$set": {"retired": True}})
    tree = _tree(np)
    anna, bobby, cathy, revy = (world.people[n] for n in ("anna", "bobby", "cathy", "revy"))

    _as(anna)
    a = queue.nextCase(clientProtocol=17)
    _as(bobby)
    b = queue.nextCase(clientProtocol=18)
    assert a["caseId"] == b["caseId"]
    sa = _submitStack(world, queue, anna, a, _stackOf(np, _fourOf(np, tree)))
    sb = _submitStack(world, queue, bobby, b,
                      _stackOf(np, _extendedOf(np, tree), labels.ALL_NAMES),
                      names=labels.ALL_NAMES, clientProtocol=18)
    assert scoring.runOnce() == 2
    for sid in (sa["submissionId"], sb["submissionId"]):
        pair = Submission14().load(sid, force=True)["autoScore"]["duplicate"]
        assert pair["mean_dice"] == 1.0 and "materials" not in pair

    _as(cathy)
    c = queue.nextCase(clientProtocol=18)
    _as(revy)
    d = queue.nextCase(clientProtocol=18)
    assert c["caseId"] == d["caseId"] != a["caseId"]
    sc = _submitStack(world, queue, cathy, c,
                      _stackOf(np, _extendedOf(np, tree), labels.ALL_NAMES),
                      names=labels.ALL_NAMES, clientProtocol=18)
    sd = _submitStack(world, queue, revy, d,
                      _stackOf(np, _extendedOf(np, tree, materials=("Stent",)),
                               labels.ALL_NAMES),
                      names=labels.ALL_NAMES, clientProtocol=18)
    assert scoring.runOnce() == 2
    pair = Submission14().load(sd["submissionId"], force=True)["autoScore"]["duplicate"]
    assert pair["mean_dice"] == 1.0                   # materials never move the headline
    assert pair["materials"]["Stent"]["dice"] == 1.0
    assert pair["materials"]["Calcified plaque"]["dice"] == 0.0
    assert pair["materials"]["Non-calcified plaque"]["dice"] is None
    mirrored = Submission14().load(sc["submissionId"], force=True)["autoScore"]["duplicate"]
    assert mirrored["materials"]["Stent"]["dice"] == 1.0


def test_the_project_setting_refuses_the_extended_classes(world):
    """0.17.x builds its panel from /project, so the extended classes never go there."""
    from girder.exceptions import ValidationException
    from girder.models.setting import Setting

    from segqueue14 import labels

    value = {"name": "x", "instructions": "y",
             "segments": labels.segment_dicts() + labels.extra_segment_dicts()[:1]}
    with pytest.raises(ValidationException, match="extended class"):
        Setting().set("segqueue14.project", value)
