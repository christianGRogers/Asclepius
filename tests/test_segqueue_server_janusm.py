"""The Janus-M read queue (``server/girder_janusm``) against a real Girder and MongoDB.

Marked ``needs_mongo`` and skipped without one, like the SegQueue server tests, and
named to run after them in one pytest process (Girder binds one scratch database).
Run with::

    SEGQUEUE_TEST_MONGO=mongodb://localhost:27099 pytest tests/test_segqueue_server_janusm.py

A miniature world: SegQueue14 with a case, an assignment, its groups and settings,
and an ``ImageCAS-X`` collection holding a CT for every frozen Janus-M case plus an
A14-sealed one. Then the Janus-M queue end to end -- populate, serve order, two
independent reads, blank cases, the read form, the read check (return once, then
accept and flag), release, the JA12 guard, third reads (JA47 rule 2), export --
and, at the end, every SegQueue14 document compared with what it was before.
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
    except Exception as exc:  # pragma: no cover
        pytest.skip(f"no MongoDB at {uri}: {exc}")
    created = None
    if "girder.models" not in sys.modules:
        # The SegQueue server tests accept this prefix, whichever module binds first.
        created = f"segqueue_test_janusm_{uuid.uuid4().hex[:8]}"
        os.environ["GIRDER_MONGO_URI"] = f"{uri.rstrip('/')}/{created}"
    for module in ("girder", "numpy", "scipy", "nibabel"):
        pytest.importorskip(module)
    try:
        from girder_janusm.models import JanusMCase
        from girder_segqueue14.models import Case14  # noqa: F401
    except ImportError as exc:
        pytest.skip(f"girder-janusm or girder-segqueue14 cannot be imported: {exc}")
    bound = JanusMCase().collection.database.name
    if not bound.startswith(("segqueue14_test_", "segqueue_test_")):
        pytest.fail(f"girder is bound to {bound!r}, which is not a scratch test database")
    from girder.models.assetstore import Assetstore

    os.environ.setdefault("GIRDER_FILESYSTEMASSETSTORE_RESERVED_MBYTES", "16")
    if Assetstore().findOne() is None:
        Assetstore().createFilesystemAssetstore(
            name="test", root=str(tmp_path_factory.mktemp("assetstore")))
    yield bound
    if created:
        client.drop_database(created)


# ------------------------------------------------------------------ the world


def _save(path, array, spacing=(0.5, 0.5, 0.5)):
    import nibabel as nib
    import numpy as np

    nib.save(nib.Nifti1Image(array, np.diag(list(spacing) + [1.0])), str(path))
    return path


def _upload(path, folder, user):
    from girder.models.upload import Upload

    with open(path, "rb") as handle:
        return Upload().uploadFromFile(handle, size=os.path.getsize(path),
                                       name=os.path.basename(path), parentType="folder",
                                       parent=folder, user=user)


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _as(user):
    from girder.api.rest import setCurrentUser

    setCurrentUser(user)


def _refusal(fn, *args, **kwargs):
    from girder.exceptions import RestException

    with pytest.raises(RestException) as info:
        fn(*args, **kwargs)
    return info.value


@pytest.fixture(scope="module")
def world(girder_db, tmp_path_factory):
    import numpy as np
    from girder.models.collection import Collection
    from girder.models.file import File
    from girder.models.folder import Folder
    from girder.models.group import Group
    from girder.models.item import Item
    from girder.models.setting import Setting
    from girder.models.user import User
    from girder_janusm.models import JanusMCase, JanusMRead
    from girder_segqueue14 import settings as _sq14settings  # noqa: F401
    from girder_segqueue14.models import Assignment14, Case14
    from girder_segqueue14.utils import ensureGroups as ensureGroups14

    from janusm_reads import phantom, readset, seeds

    for model in (Case14, Assignment14, JanusMCase, JanusMRead, User, Group, Collection,
                  Folder, Item, File):
        model().collection.delete_many({})
    Setting().collection.delete_many({"key": {"$regex": "^(segqueue14|janusm)\\."}})

    tmp = tmp_path_factory.mktemp("janusm")
    admin = User().createUser("admin", "password1", "A", "Dmin", "admin@example.org",
                              admin=True)
    people = {login: User().createUser(login, "password1", login, "X", f"{login}@example.org")
              for login in ("anna", "bobby", "cathy", "dora")}

    # -- SegQueue14, as janus has it (D36): one collection, its groups, a case in flight.
    sq = Collection().createCollection("SegQueue", creator=admin, public=False)
    sqCases = Folder().createFolder(sq, "cases", parentType="collection", creator=admin)
    sqCt = _upload(_save(tmp / "Pool__0001.nii.gz", np.full((8, 8, 8), 50, np.int16)),
                   sqCases, admin)
    ensureGroups14(admin)
    annotators = Group().findOne({"name": "segqueue14-annotators"})
    Group().addUser(annotators, people["dora"])
    Setting().set("segqueue14.policy", {"base_review_rate": 0.0})
    case14 = Case14().createCase("Pool__0001", sqCt["_id"], "x" * 64, sqCt["size"],
                                 creator=admin, replicasWanted=2)
    Assignment14().createAssignment(case14, User().load(people["dora"]["_id"], force=True))

    # -- ImageCAS-X: a CT for every frozen Janus-M case, and one A14-sealed case (c0002).
    sets = readset.load_freeze()
    icx = Collection().createCollection("ImageCAS-X", creator=admin, public=False)
    icxCases = Folder().createFolder(icx, "cases", parentType="collection", creator=admin)
    truth, spacing = phantom.heart()
    heartCt = phantom.ct_from(truth, spacing, noise_hu=10.0).astype(np.int16)
    target = sets["decision"][0]              # served first: the case the check runs on
    tiny = np.zeros((8, 8, 8), np.int16)
    seedsDir = tmp / "seeds"
    seedsDir.mkdir()
    for case in sets["decision"] + sets["seal"] + ["c0002"]:
        n = readset.imagecas_number(case)
        ct = heartCt if case == target else tiny + n
        _upload(_save(tmp / f"ImageCAS__{n:04d}.nii.gz", ct, spacing), icxCases, admin)
        seed = seeds.coarsen(truth, spacing) if case == target else tiny.astype(np.uint8)
        _save(seedsDir / f"{case}.janusm-seed.nii.gz", seed, spacing)

    from girder_janusm.utils import ensureGroups

    ensureGroups(admin)
    readers = Group().findOne({"name": "janusm-readers"})
    for login in ("anna", "bobby", "cathy"):
        Group().addUser(readers, people[login])
    people = {k: User().load(v["_id"], force=True) for k, v in people.items()}

    class World:
        pass

    w = World()
    w.admin, w.people, w.tmp, w.sets, w.seedsDir = admin, people, tmp, sets, seedsDir
    w.truth, w.spacing, w.target = truth, spacing, target
    w.db = JanusMCase().database
    w.before14 = _snapshot14(w)
    w.icxBefore = _icxSnapshot()
    return w


def _snapshot14(world):
    """Everything of SegQueue14's the Janus-M queue must not change."""
    from girder.models.collection import Collection
    from girder.models.file import File
    from girder.models.folder import Folder
    from girder.models.group import Group
    from girder.models.item import Item
    from girder.models.setting import Setting
    from girder.models.user import User

    db = world.db
    out = {name: sorted(json.dumps(d, default=str, sort_keys=True)
                         for d in db[name].find({}))
           for name in db.list_collection_names() if name.startswith("segqueue")}
    sq = Collection().findOne({"name": "SegQueue"})
    out["collection"] = json.dumps(sq, default=str, sort_keys=True)
    folders = list(Folder().find({"baseParentId": sq["_id"]}))
    out["folders"] = sorted(json.dumps(f, default=str, sort_keys=True) for f in folders)
    items = list(Item().find({"baseParentId": sq["_id"]}))
    out["items"] = sorted(json.dumps(i, default=str, sort_keys=True) for i in items)
    out["files"] = sorted(json.dumps(f, default=str, sort_keys=True)
                          for i in items for f in File().find({"itemId": i["_id"]}))
    groups = list(Group().find({"name": {"$regex": "^segqueue"}}))
    out["groups"] = sorted(json.dumps(g, default=str, sort_keys=True) for g in groups)
    ids = {g["_id"] for g in groups}
    # Who holds a SegQueue14 group (users created later for Janus-M hold none).
    members = ((u["login"], sorted(str(g) for g in u.get("groups", []) if g in ids))
               for u in User().find({}))
    out["members"] = sorted(m for m in members if m[1])
    out["settings"] = sorted(json.dumps(s, default=str, sort_keys=True)
                             for s in Setting().find({"key": {"$regex": "^segqueue"}}))
    return out


def _icxSnapshot():
    from girder.models.collection import Collection
    from girder.models.file import File
    from girder.models.item import Item

    icx = Collection().findOne({"name": "ImageCAS-X"})
    items = list(Item().find({"baseParentId": icx["_id"]}))
    return sorted(json.dumps(f, default=str, sort_keys=True)
                  for i in items for f in File().find({"itemId": i["_id"]}))


def _api():
    from girder_janusm.rest import JanusMResource

    return JanusMResource()


FORM = {"LM": "0", "LAD": "2", "LCx": "0", "RCA": "1"}


def _submit(api, world, user, readId, array, checksum=None, form=FORM, points=None):
    import numpy as np
    from girder.models.upload import Upload
    from girder_janusm.utils import incomingFolder

    path = _save(world.tmp / f"read-{readId}-{uuid.uuid4().hex[:6]}.nii.gz",
                 array.astype(np.uint8), world.spacing)
    with open(path, "rb") as handle:
        up = Upload().uploadFromFile(handle, size=os.path.getsize(path), name=path.name,
                                     parentType="folder", parent=incomingFolder(user),
                                     user=user)
    counts = {str(v): int((array == v).sum()) for v in range(1, 5)}
    meta = {"checksum": checksum or _sha(path), "sizeBytes": os.path.getsize(path),
            "voxelCounts": counts, "clientVersion": "test", "seconds": 61.5,
            "cadrads": form or {}, "lesionPoints": points or {}}
    _as(user)
    return api.submit(readId=readId, fileId=str(up["_id"]), meta=json.dumps(meta),
                      clientProtocol=1)


# ------------------------------------------------------------------ populate


def test_populate_refuses_the_whole_run_on_a_held_out_case(world, monkeypatch):
    from girder_janusm import populate
    from girder_janusm.models import JanusMCase

    from janusm_reads import holdout

    bad = {k: list(v) for k, v in world.sets.items()}
    bad["decision"][5] = "c0002"     # A14 sealed
    monkeypatch.setattr(populate.readset, "load_freeze", lambda path=None: bad)
    with pytest.raises(holdout.HoldoutError, match="A14"):
        populate.populate(world.admin, seedsDir=str(world.seedsDir), out=lambda _: None)
    assert JanusMCase().collection.count_documents({}) == 0


def test_populate_creates_the_frozen_cases_and_no_blank_seed(world):
    from girder_janusm import populate
    from girder_janusm.models import JanusMCase

    from janusm_reads import readset

    lines = []
    dry = populate.populate(world.admin, seedsDir=str(world.seedsDir), dryRun=True,
                            out=lines.append)
    assert dry["create"] == 100 and JanusMCase().collection.count_documents({}) == 0
    populate.populate(world.admin, seedsDir=str(world.seedsDir), out=lambda _: None)
    cases = list(JanusMCase().find({}))
    assert len(cases) == 100
    names = {c["name"] for c in cases}
    assert names == set(world.sets["seal"]) | set(world.sets["decision"])
    assert "c0002" not in names
    blank = {c["name"] for c in cases if c["blank"]}
    assert blank == set(readset.blank_cases(world.sets["seal"]))
    assert all(c["seedFileId"] is None for c in cases if c["blank"])
    assert all(c["seedFileId"] for c in cases if not c["blank"])
    assert all(c["readsWanted"] == 2 for c in cases)
    # Re-running creates nothing; ImageCAS-X is only read.
    again = populate.populate(world.admin, seedsDir=str(world.seedsDir), out=lambda _: None)
    assert again["create"] == 0
    assert _icxSnapshot() == world.icxBefore


# --------------------------------------------------------------------- serving


def test_only_readers_and_only_janusm_clients(world):
    api = _api()
    _as(world.people["dora"])                 # a SegQueue14 annotator, not a reader
    assert _refusal(api.nextRead, clientProtocol=1).code == 403
    _as(world.people["anna"])
    assert _refusal(api.nextRead).code == 426  # says nothing
    for sent in (16, 14, 0):                  # 16: SegQueue14's own protocol
        assert _refusal(api.nextRead, clientProtocol=sent).code == 426
    project = api.getProject(clientProtocol=1)
    assert project["protocol"] == "janusm-read"
    assert project["protocolVersion"] == 1 and project["border_protocol"] == 1
    assert [x["value"] for x in project["labels"]] == [1, 2, 3, 4]
    assert project["readForm"]["vessels"] == ["LM", "LAD", "LCx", "RCA"]
    assert "4B" in project["readForm"]["cadrads"]


def test_two_independent_reads_and_the_read_check(world):
    import numpy as np
    from girder_janusm.models import JanusMCase

    from janusm_reads import phantom

    api = _api()
    anna, bobby, cathy = (world.people[k] for k in ("anna", "bobby", "cathy"))
    _as(anna)
    a = api.nextRead(clientProtocol=1)
    assert a["caseName"] == world.target and a["hasSeed"]
    assert "readSet" not in a and "blank" not in a          # blind to the set
    assert _refusal(api.nextRead, clientProtocol=1).code == 409   # one open read at a time
    _as(bobby)
    b = api.nextRead(clientProtocol=1)
    assert b["caseName"] == world.target                      # the second slot, another reader
    _as(cathy)
    c = api.nextRead(clientProtocol=1)
    assert c["caseName"] != world.target                      # two slots only

    # Nobody reaches another reader's read.
    _as(cathy)
    assert _refusal(api.downloadCt, readId=a["readId"]).code == 403
    _as(anna)
    api.downloadCt(readId=a["readId"])
    api.downloadSeed(readId=a["readId"])

    # Refusals at submit: a missing class, a wrong checksum, an incomplete read form.
    empty_la = world.truth.copy()
    empty_la[empty_la == 4] = 0
    assert _refusal(_submit, api, world, anna, a["readId"], empty_la).code == 400
    assert _refusal(_submit, api, world, anna, a["readId"], world.truth,
                    checksum="0" * 64).code == 400
    assert _refusal(_submit, api, world, anna, a["readId"], world.truth,
                    form={"LM": "0"}).code == 400
    assert _refusal(_submit, api, world, anna, a["readId"], world.truth,
                    points={"LM": [1.0, 2.0, 3.0]}).code == 400   # LM graded 0

    # Anna's read is right; Bobby's epicardium spills 2 mm into the fat.
    from girder_janusm.check import runOnce
    from girder_janusm.models import JanusMRead

    _submit(api, world, anna, a["readId"], world.truth, points={"LAD": [1.5, -2.0, 30.0]})
    off = phantom.move_border(world.truth, world.spacing, "epicardial", 2.0)
    _submit(api, world, bobby, b["readId"], off)
    assert runOnce(out=lambda _: None) == 2
    _as(anna)
    mine = {r["readId"]: r for r in api.listMine()}
    assert mine[a["readId"]]["state"] == "accepted" and not mine[a["readId"]]["flagged"]
    assert mine[a["readId"]]["checkProfile"] == {}          # profiles go with a return only
    _as(bobby)
    mine = {r["readId"]: r for r in api.listMine()}
    first = mine[b["readId"]]
    assert first["state"] == "returned" and not first["flagged"]
    assert "epicardial" in first["checkSummary"]
    # The return carries the half-maximum profiles, the failing border marked.
    prof = first["checkProfile"]
    assert prof["epicardial"]["failed"] and not prof["endocardial"]["failed"]
    assert prof["epicardial"]["offsetMm"] == pytest.approx(2.0, abs=0.4)   # canonical
    assert len(prof["epicardial"]["s_mm"]) == len(prof["epicardial"]["hu"]) > 10
    assert prof["epicardial"]["thresholdHU"] is not None

    # Returned once. Bobby resubmits it still wrong: accepted, and flagged with reasons.
    _submit(api, world, bobby, b["readId"], off)
    runOnce(out=lambda _: None)
    mine = {r["readId"]: r for r in api.listMine()}
    assert mine[b["readId"]]["state"] == "accepted" and mine[b["readId"]]["flagged"]
    assert "flagged" in mine[b["readId"]]["checkSummary"]
    stored = JanusMRead().load(b["readId"], force=True)
    assert stored["attempts"] == 2 and stored["flagged"] is True
    assert any("epicardial" in r for r in stored["flagReasons"])
    assert stored["border_protocol"] == 1 and stored["check"]["border_protocol"] == 1
    assert stored["cadrads"] == FORM
    case = JanusMCase().findOne({"name": world.target})
    assert case["acceptedCount"] == 2 and case["slotsTaken"] == 2
    assert len(set(case["assignedUserIds"])) == 2
    stored = JanusMRead().load(a["readId"], force=True)
    assert stored["lesionPoints"] == {"LAD": [1.5, -2.0, 30.0]} and stored["attempts"] == 1
    _as(cathy)
    api.release(readId=c["readId"])
    assert np.asarray(world.truth).any()


def test_a_returned_read_fixed_on_its_second_try_is_accepted_unflagged(world):
    from girder_janusm.check import decide

    from janusm_reads import protocol

    failed = {"passed": False, "errors": ["The epicardial border is 2.00 mm past ..."],
              "summary": "Failed"}
    assert decide(failed, 1)[:2] == (protocol.RETURNED, False)
    assert decide(failed, 2)[:2] == (protocol.ACCEPTED, True)
    assert "epicardial" in decide(failed, 2)[2]
    assert decide(failed, 2, crashed=True)[:2] == (protocol.RETURNED, False)
    assert decide({"passed": True, "summary": "Passed"}, 2)[:2] == (protocol.ACCEPTED, False)


def test_release_frees_the_slot_for_someone_else_only(world):
    from girder_janusm.models import JanusMCase, JanusMRead

    api = _api()
    cathy, anna = world.people["cathy"], world.people["anna"]
    released = JanusMRead().findOne({"userId": cathy["_id"], "state": "released"})
    name = JanusMCase().load(released["caseId"], force=True)["name"]
    _as(cathy)
    got = api.nextRead(clientProtocol=1)
    assert got["caseName"] != name                 # never handed back to cathy
    api.release(readId=got["readId"])
    _as(anna)
    assert api.nextRead(clientProtocol=1)["caseName"] == name
    for r in JanusMRead().find({"state": "assigned"}):
        _as({"cathy": cathy, "anna": anna}.get(
            next(k for k, u in world.people.items() if u["_id"] == r["userId"])))
        api.release(readId=str(r["_id"]))


def test_seal_cases_wait_until_an_admin_opens_the_seal(world):
    from girder_janusm.models import JanusMCase, JanusMRead

    api = _api()
    readers = [world.people[k] for k in ("anna", "bobby", "cathy")]
    served = []
    # Drain the decision set: every reader takes and releases until nothing is left.
    for _ in range(200):
        took = False
        for user in readers:
            _as(user)
            try:
                got = api.nextRead(clientProtocol=1)
            except Exception:  # noqa: BLE001 - 404 for this reader
                continue
            served.append(got["caseName"])
            api.release(readId=got["readId"])
            took = True
        if not took:
            break
    assert set(served) <= set(world.sets["decision"])
    _as(world.people["dora"])
    assert _refusal(api.adminOpenSeal, open=True).code == 403
    _as(world.admin)
    assert api.adminOpenSeal(open=True)["sealOpen"] is True
    # A fourth reader sees seal cases now, and blank ones say they have no seed.
    from girder.models.group import Group
    from girder.models.user import User

    eve = User().createUser("evelyn", "password1", "Eve", "X", "eve@example.org")
    Group().addUser(Group().findOne({"name": "janusm-readers"}), eve)
    eve = User().load(eve["_id"], force=True)
    _as(eve)
    blank = {c["name"] for c in JanusMCase().find({"blank": True})}
    seen = []
    for _ in range(120):
        try:
            got = api.nextRead(clientProtocol=1)
        except Exception:  # noqa: BLE001 - queue empty for eve
            break
        seen.append(got["caseName"])
        if got["caseName"] in blank:
            assert got["hasSeed"] is False
            assert _refusal(api.downloadSeed, readId=got["readId"]).code == 404
        api.release(readId=got["readId"])
    assert set(seen) & set(world.sets["seal"])
    assert blank <= set(seen)
    # Decision cases are still served before seal cases.
    first_seal = next(i for i, n in enumerate(seen) if n in set(world.sets["seal"]))
    assert all(n in set(world.sets["decision"]) for n in seen[:first_seal])
    assert JanusMRead().collection.count_documents({"state": "assigned"}) == 0


def test_a_case_the_guard_refuses_later_is_retired_not_served(world, monkeypatch):
    from girder_janusm import rest
    from girder_janusm.models import JanusMCase

    from janusm_reads import holdout

    real = holdout.refuse
    victim = world.sets["seal"][-1]

    def refuse(names, what="", purpose="any", source=None):
        if victim in list(names):
            raise holdout.HoldoutError(f"{victim}: newly held out")
        return real(names, what=what, purpose=purpose, source=source)

    monkeypatch.setattr(rest.holdout, "refuse", refuse)
    from girder.models.user import User

    fresh = User().createUser("finn", "password1", "Finn", "X", "finn@example.org")
    from girder.models.group import Group

    Group().addUser(Group().findOne({"name": "janusm-readers"}), fresh)
    fresh = User().load(fresh["_id"], force=True)
    api = _api()
    _as(fresh)
    names = []
    for _ in range(120):
        try:
            got = api.nextRead(clientProtocol=1)
        except Exception:  # noqa: BLE001
            break
        names.append(got["caseName"])
        api.release(readId=got["readId"])
    assert victim not in names
    assert JanusMCase().findOne({"name": victim})["retired"] is True


# ---------------------------------------------------------------------- export


def test_third_reads_are_blank_by_a_fresh_reader_and_never_reference(world):
    """S5 point 5 (JA47 rule 2): an admin opens a flagged wave's third reads."""
    from girder.models.group import Group
    from girder.models.user import User
    from girder_janusm.check import runOnce
    from girder_janusm.models import JanusMCase, JanusMRead

    api = _api()
    blank = JanusMCase().findOne({"blank": True})
    _as(world.people["anna"])
    assert _refusal(api.adminThirdReads, cases=json.dumps([world.target])).code == 403
    _as(world.admin)
    # Only seeded cases whose two reads are both accepted.
    assert _refusal(api.adminThirdReads, cases=json.dumps([blank["name"]])).code == 400
    other = json.dumps([world.sets["decision"][1]])
    assert _refusal(api.adminThirdReads, cases=other).code == 400
    one = json.dumps([world.target])
    assert api.adminThirdReads(cases=one)["opened"] == [world.target]
    assert api.adminThirdReads(cases=one)["alreadyOpen"] == [world.target]

    # Anna and Bobby read it: the third read goes to someone else.
    target = JanusMCase().findOne({"name": world.target})
    for login in ("anna", "bobby"):
        assert world.people[login]["_id"] in target["assignedUserIds"]
    gus = User().createUser("gustav", "password1", "Gus", "X", "gus@example.org")
    Group().addUser(Group().findOne({"name": "janusm-readers"}), gus)
    gus = User().load(gus["_id"], force=True)
    _as(gus)
    third = api.nextRead(clientProtocol=1)
    assert third["caseName"] == world.target and third["hasSeed"] is False
    assert _refusal(api.downloadSeed, readId=third["readId"]).code == 404   # from blank
    assert "third" not in third                                            # reader-blind
    _submit(api, world, gus, third["readId"], world.truth)
    runOnce(out=lambda _: None)
    after = JanusMCase().findOne({"name": world.target})
    assert after["acceptedCount"] == 2 and after["thirdReadAccepted"] is True
    stored = JanusMRead().load(third["readId"], force=True)
    assert stored["third"] and not stored["seeded"] and stored["state"] == "accepted"
    # No second third read on the case.
    _as(world.people["cathy"])
    try:
        got = api.nextRead(clientProtocol=1)
        assert got["caseName"] != world.target
        api.release(readId=got["readId"])
    except Exception as exc:  # noqa: BLE001 - nothing left for cathy is fine too
        assert getattr(exc, "code", None) == 404


def test_export_feeds_the_anchoring_report(world):
    """S5 point 8: a record per read, offsets in the canonical sign, border_protocol."""
    from girder_janusm.export import export

    from janusm_reads import anchoring

    out = world.tmp / "wave1"
    manifest = export(str(out), str(world.seedsDir), wave="1", seedOffsets=True,
                      out=lambda _: None)
    assert manifest["border_protocol"] == 1
    assert [c["case"] for c in manifest["cases"]] == [world.target]
    row = manifest["cases"][0]
    records = row["readRecords"]
    assert len(records) == 2 and not any(r["third"] for r in records)
    for rec in records:
        assert set(rec) >= {"reader", "seeded", "blank", "seconds", "attempts", "flagged",
                            "flagReasons", "halfMaxOffsetsMm", "border_protocol", "cadrads"}
        assert rec["border_protocol"] == 1 and rec["seeded"] and not rec["blank"]
        assert rec["seconds"] == pytest.approx(61.5) and rec["offsetSign"] == "canonical"
    byFlag = {r["flagged"]: r for r in records}
    assert byFlag[True]["attempts"] == 2 and byFlag[True]["flagReasons"]
    assert byFlag[True]["halfMaxOffsetsMm"]["epicardial"] == pytest.approx(2.0, abs=0.4)
    assert byFlag[False]["attempts"] == 1
    assert abs(byFlag[False]["halfMaxOffsetsMm"]["endocardial"]) < 0.5
    assert {r["reader"] for r in records} == {str(world.people[k]["_id"])
                                              for k in ("anna", "bobby")}
    # The third read is exported apart, never as a reference read.
    assert row["thirdRead"].endswith("__third.nii.gz") and row["thirdReadRecord"]["third"]
    assert set(row["halfMaxOffsets"]["seed"]) == {"endocardial", "epicardial", "septal_rv"}

    report = anchoring.report_from_manifest(out / "manifest.json")
    assert report["cases"] == 1 and report["seededCases"] == 1
    assert report["borders"]["endocardial"]["interReadSeeded"] == pytest.approx(0.0)
    assert report["rows"][0]["thirdReadVsSeed"]["endocardial"] is not None
    assert "seedMedian" in report["halfMaxOffsets"]["endocardial"]


# ------------------------------------------------------------ SegQueue14 untouched


def test_segqueue14_is_untouched(world):
    """Run last: every SegQueue14 document, folder, file, group, membership and setting
    is as it was before the Janus-M queue did anything."""
    assert _snapshot14(world) == world.before14


def test_both_plugins_mount_side_by_side_and_janusm_cannot_stop_girder(world, monkeypatch):
    import girder_janusm
    import girder_segqueue14
    from girder_janusm import JanusMPlugin
    from girder_segqueue14 import SegQueue14Plugin

    class Root:
        pass

    def fresh(cls, name):
        plugin = object.__new__(cls)
        plugin._name = name
        return plugin

    root = Root()
    fresh(SegQueue14Plugin, "segqueue14").load({"apiRoot": root})
    fresh(JanusMPlugin, "janusm").load({"apiRoot": root})
    assert root.segqueue14.resourceName == "segqueue14"
    assert root.janusm.resourceName == "janusm"
    from girder_janusm import constants as jm
    from girder_segqueue14 import constants as sq

    assert {jm.READER_GROUP, jm.ADMIN_GROUP}.isdisjoint({sq.ANNOTATOR_GROUP, sq.REVIEWER_GROUP})
    assert jm.COLLECTION_NAME != sq.COLLECTION_NAME

    monkeypatch.setattr(girder_janusm, "mount",
                        lambda info: (_ for _ in ()).throw(RuntimeError("boom")))
    root = Root()
    fresh(JanusMPlugin, "janusm").load({"apiRoot": root})        # logged, not raised
    fresh(SegQueue14Plugin, "segqueue14").load({"apiRoot": root})
    assert not hasattr(root, "janusm") and hasattr(root, "segqueue14")
    monkeypatch.setenv("JANUSM_DISABLE", "1")
    root = Root()
    fresh(JanusMPlugin, "janusm").load({"apiRoot": root})
    assert not hasattr(root, "janusm")
    assert girder_segqueue14 is not None
