"""The Janus-M read queue (``server/girder_janusm``) against a real Girder and MongoDB.

Marked ``needs_mongo`` and skipped without one, like the SegQueue server tests, and
named to run after them in one pytest process (Girder binds one scratch database).
Run with::

    SEGQUEUE_TEST_MONGO=mongodb://localhost:27099 pytest tests/test_segqueue_server_janusm.py

A miniature world: SegQueue14 with a case, an assignment, its groups and settings,
and an ``ImageCAS-X`` collection holding a CT for every frozen Janus-M case plus an
A14-sealed one. Then the Janus-M queue end to end -- populate, serve order, two
independent reads, blank cases and their hidden check seeds (JA66), the read form
(JA67), the read check (return once, then accept and flag; a crash never spends the
return, JA68), release, the JA12 guard, waves and the drawn third reads (JA47 rule 2,
JA68), export -- and, at the end, every SegQueue14 document compared with what it was
before.
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
#: The wire protocol this server speaks (JA67: 2).
CP = 2


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
    truth, spacing = phantom.heart()          # a mitral gap of 2 mm (JA46 (a))
    plain, _ = phantom.heart(mitral_gap_mm=None)   # no gap: no mitral plane can be fitted
    heartCt = phantom.ct_from(truth, spacing, noise_hu=10.0).astype(np.int16)
    plainCt = phantom.ct_from(plain, spacing, noise_hu=10.0).astype(np.int16)
    target = sets["decision"][0]              # served first: the case the check runs on
    crashCase = sets["decision"][1]           # R4-S17: a crash, then real failures
    planeless = sets["decision"][2]           # R4-S16: a read that could not be checked
    blankCase = next(c for c in readset.blank_cases(sets["seal"]) if c != sets["seal"][-1])
    # Round 5 (#232): each test its own case, outside decision[3:9] (rule 2's waves).
    afterReturn = sets["decision"][9]         # R5-S11: a genuine return, then plane-less
    unreadMover = sets["decision"][10]        # R5-S9: an unread case moves wave
    noBounds = sets["decision"][12]           # R5-S8: a CT header that cannot be parsed
    competing = sets["decision"][13]          # R5-S11 / S21: a competing wave
    noCheckSeed = next(c for c in readset.blank_cases(sets["seal"])
                       if c not in (blankCase, sets["seal"][-1]))   # R5-S7
    hearts = {target: (heartCt, truth), crashCase: (heartCt, truth),
              blankCase: (heartCt, truth), planeless: (plainCt, plain),
              afterReturn: (heartCt, truth)}
    tiny = np.zeros((8, 8, 8), np.int16)
    seedsDir = tmp / "seeds"
    seedsDir.mkdir()
    for case in sets["decision"] + sets["seal"] + ["c0002"]:
        n = readset.imagecas_number(case)
        ct, labels = hearts.get(case, (tiny + n, None))
        _upload(_save(tmp / f"ImageCAS__{n:04d}.nii.gz", ct, spacing), icxCases, admin)
        seed = (seeds.coarsen(labels, spacing) if labels is not None
                else tiny.astype(np.uint8))
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
    w.plain, w.crashCase, w.planeless, w.blankCase = plain, crashCase, planeless, blankCase
    w.afterReturn, w.unreadMover, w.noBounds = afterReturn, unreadMover, noBounds
    w.competing, w.noCheckSeed = competing, noCheckSeed
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


def _submit(api, world, user, readId, array, checksum=None, form=FORM, points=None,
            seconds=61.5):
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
            "voxelCounts": counts, "clientVersion": "test", "seconds": seconds,
            "cadrads": form or {}, "lesionPoints": points or {}}
    _as(user)
    return api.submit(readId=readId, fileId=str(up["_id"]), meta=json.dumps(meta),
                      clientProtocol=CP)


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
    """No blank case has a servable seed; each has a check seed no reader can read (JA66)."""
    from girder.constants import AccessType
    from girder.models.file import File
    from girder.models.folder import Folder
    from girder.models.item import Item
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
    assert all(c["checkSeedFileId"] for c in cases if c["blank"])
    assert all(c.get("checkSeedFileId") is None for c in cases if not c["blank"])
    for case in cases:
        if not case["blank"]:
            continue
        item = Item().load(File().load(case["checkSeedFileId"], force=True)["itemId"],
                           force=True)
        folder = Folder().load(item["folderId"], force=True)
        assert folder["name"] == "check-seeds" and not folder["public"]
        assert not (folder.get("access") or {}).get("groups")
        for login in ("anna", "bobby", "cathy"):
            assert not Folder().hasAccess(folder, world.people[login], AccessType.READ)
    assert all(c["readsWanted"] == 2 for c in cases)
    # Re-running creates nothing; ImageCAS-X is only read.
    again = populate.populate(world.admin, seedsDir=str(world.seedsDir), out=lambda _: None)
    assert again["create"] == 0
    assert _icxSnapshot() == world.icxBefore


# --------------------------------------------------------------------- serving


def test_only_readers_and_only_janusm_clients(world):
    api = _api()
    _as(world.people["dora"])                 # a SegQueue14 annotator, not a reader
    assert _refusal(api.nextRead, clientProtocol=CP).code == 403
    _as(world.people["anna"])
    assert _refusal(api.nextRead).code == 426  # says nothing
    for sent in (16, 14, 0):                  # 16: SegQueue14's own protocol
        assert _refusal(api.nextRead, clientProtocol=sent).code == 426
    project = api.getProject(clientProtocol=CP)
    assert project["protocol"] == "janusm-read"
    assert project["protocolVersion"] == 2 and project["border_protocol"] == 1
    assert [x["value"] for x in project["labels"]] == [1, 2, 3, 4]
    assert project["readForm"]["vessels"] == ["LM", "LAD", "LCx", "RCA"]
    assert project["readForm"]["grades"]["LM"] == ["0", "1", "2", "4B", "5", "N"]
    assert "4B" not in project["readForm"]["grades"]["LAD"]


def test_r4s20_a_protocol_1_client_is_refused_at_next_before_any_claim(world):
    """JA67: a JanusMRead 0.2.x client cannot claim and draw a case it cannot submit."""
    from girder_janusm.models import JanusMCase, JanusMRead

    api = _api()
    _as(world.people["anna"])
    before = (JanusMRead().collection.count_documents({}),
              sorted((c["name"], c["slotsTaken"]) for c in JanusMCase().find({})))
    for sent in (1, "1"):
        assert _refusal(api.nextRead, clientProtocol=sent).code == 426
        assert _refusal(api.getProject, clientProtocol=sent).code == 426
    after = (JanusMRead().collection.count_documents({}),
             sorted((c["name"], c["slotsTaken"]) for c in JanusMCase().find({})))
    assert after == before


def test_two_independent_reads_and_the_read_check(world):
    import numpy as np
    from girder_janusm.models import JanusMCase

    from janusm_reads import phantom

    api = _api()
    anna, bobby, cathy = (world.people[k] for k in ("anna", "bobby", "cathy"))
    # JA78: waves are set before reading; a case that has been read never changes wave.
    _as(world.admin)
    assert api.adminWave(wave="1", cases=json.dumps([world.target]))["moved"] == [world.target]
    _as(anna)
    a = api.nextRead(clientProtocol=CP)
    assert a["caseName"] == world.target and a["hasSeed"]
    assert "readSet" not in a and "blank" not in a          # blind to the set
    assert _refusal(api.nextRead, clientProtocol=CP).code == 409   # one open read at a time
    _as(bobby)
    b = api.nextRead(clientProtocol=CP)
    assert b["caseName"] == world.target                      # the second slot, another reader
    _as(cathy)
    c = api.nextRead(clientProtocol=CP)
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
    # JA67: 4B is not a LAD grade, 3 is not an LM grade; a point 1 m away is refused.
    for bad in ({**FORM, "LAD": "4B"}, {**FORM, "LM": "3"}):
        refused = _refusal(_submit, api, world, anna, a["readId"], world.truth, form=bad)
        assert refused.code == 400 and "not a grade on this vessel" in str(refused)
    refused = _refusal(_submit, api, world, anna, a["readId"], world.truth,
                       points={"LAD": [1000.0, 2.0, 30.0]})
    assert refused.code == 400 and "outside the CT" in str(refused)

    # Anna's read is right; Bobby's epicardium spills 2 mm into the fat.
    from girder_janusm.check import runOnce
    from girder_janusm.models import JanusMRead

    _submit(api, world, anna, a["readId"], world.truth, points={"LAD": [1.5, 2.0, 30.0]})
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
    assert (stored["returns"], stored["crashes"]) == (1, 0)
    assert stored["seconds"] == pytest.approx(2 * 61.5)          # summed over attempts
    assert any("epicardial" in r for r in stored["flagReasons"])
    assert stored["border_protocol"] == 1 and stored["check"]["border_protocol"] == 1
    assert stored["cadrads"] == FORM
    case = JanusMCase().findOne({"name": world.target})
    assert case["acceptedCount"] == 2 and case["slotsTaken"] == 2
    assert len(set(case["assignedUserIds"])) == 2
    stored = JanusMRead().load(a["readId"], force=True)
    assert stored["lesionPoints"] == {"LAD": [1.5, 2.0, 30.0]} and stored["attempts"] == 1
    assert stored["check"]["mitral"]["source"] == "seed"
    assert JanusMCase().findOne({"name": world.target})["ctWorldBounds"]
    _as(cathy)
    api.release(readId=c["readId"])
    assert np.asarray(world.truth).any()


def test_a_returned_read_fixed_on_its_second_try_is_accepted_unflagged(world):
    from girder_janusm.check import decide

    from janusm_reads import protocol

    failed = {"passed": False, "errors": ["The epicardial border is 2.00 mm past ..."],
              "summary": "Failed"}
    assert decide(failed, 0)[:2] == (protocol.RETURNED, False)       # not yet returned
    assert decide(failed, 1)[:2] == (protocol.ACCEPTED, True)        # returned once
    assert "epicardial" in decide(failed, 1)[2]
    assert decide(failed, 1, crashed=True)[:2] == (protocol.RETURNED, False)
    assert decide({"passed": True, "summary": "Passed"}, 1)[:2] == (protocol.ACCEPTED, False)


def test_release_frees_the_slot_for_someone_else_only(world):
    from girder_janusm.models import JanusMCase, JanusMRead

    api = _api()
    cathy, anna = world.people["cathy"], world.people["anna"]
    released = JanusMRead().findOne({"userId": cathy["_id"], "state": "released"})
    name = JanusMCase().load(released["caseId"], force=True)["name"]
    _as(cathy)
    got = api.nextRead(clientProtocol=CP)
    assert got["caseName"] != name                 # never handed back to cathy
    api.release(readId=got["readId"])
    _as(anna)
    assert api.nextRead(clientProtocol=CP)["caseName"] == name
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
                got = api.nextRead(clientProtocol=CP)
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
            got = api.nextRead(clientProtocol=CP)
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
            got = api.nextRead(clientProtocol=CP)
        except Exception:  # noqa: BLE001
            break
        names.append(got["caseName"])
        api.release(readId=got["readId"])
    assert victim not in names
    assert JanusMCase().findOne({"name": victim})["retired"] is True


# ------------------------------------------- JA66 / JA68: the check, Round 4


def _reader(login):
    from girder.models.group import Group
    from girder.models.user import User

    user = User().createUser(login, "password1", login, "X", f"{login}@example.org")
    Group().addUser(Group().findOne({"name": "janusm-readers"}), user)
    return User().load(user["_id"], force=True)


def _user(login):
    from girder.models.user import User

    return User().findOne({"login": login})


def _take(api, user, name):
    """Take ``name`` for ``user``, releasing whatever else comes first."""
    _as(user)
    for _ in range(150):
        got = api.nextRead(clientProtocol=CP)
        if got["caseName"] == name:
            return got
        api.release(readId=got["readId"])
    raise AssertionError(f"{name} was never served")


def _overreach(world, height):
    """The pool pushed ``height`` mm into the LA over the mitral footprint, with a
    myocardium rim kept against the LA (India's +4 / +6 mm blank reads)."""
    import numpy as np
    from scipy import ndimage

    from janusm_reads import checker
    from janusm_reads import labels as L

    truth, spacing = world.truth, world.spacing
    centre, normal, radius, _ = checker.mitral_plane(truth, spacing, seed=truth)
    rel = np.indices(truth.shape).reshape(3, -1).T * np.asarray(spacing) - centre
    h = (rel @ normal).reshape(truth.shape)
    ip = np.sqrt(np.maximum(0, (rel ** 2).sum(1) - (rel @ normal) ** 2)).reshape(truth.shape)
    read = truth.copy()
    read[(h > 0) & (h <= height) & (ip <= radius) & (truth != L.LV_POOL)
         & np.isin(truth, (L.LV_MYO, L.LA_POOL))] = L.LV_POOL
    read[ndimage.binary_dilation(read == L.LV_POOL) & (read == L.LA_POOL)] = L.LV_MYO
    return read


def test_r4s16_a_blank_read_is_checked_against_the_hidden_check_seed(world):
    """JA66: the blank case's seed is never served (4xx, hasSeed false), yet its check
    report says the plane was fitted to the seed; a +6 mm overreach is returned."""
    from girder_janusm.check import runOnce
    from girder_janusm.models import JanusMCase, JanusMRead

    api = _api()
    ida = _reader("idalia")
    case = JanusMCase().findOne({"name": world.blankCase})
    assert case["blank"] and case["seedFileId"] is None and case["checkSeedFileId"]
    got = _take(api, ida, world.blankCase)
    assert got["hasSeed"] is False
    assert _refusal(api.downloadSeed, readId=got["readId"]).code == 404
    _submit(api, world, ida, got["readId"], _overreach(world, 6.0))
    runOnce(out=lambda _: None)
    _as(ida)
    mine = {r["readId"]: r for r in api.listMine()}[got["readId"]]
    assert mine["state"] == "returned" and not mine["flagged"]
    assert "above the mitral plane" in mine["checkSummary"]
    stored = JanusMRead().load(got["readId"], force=True)
    assert stored["check"]["mitral"]["source"] == "seed"
    assert "fitted to the seed" in stored["check"]["mitral"]["note"]
    assert (stored["returns"], stored["crashes"]) == (1, 0)
    _submit(api, world, ida, got["readId"], world.truth)
    runOnce(out=lambda _: None)
    _as(ida)
    mine = {r["readId"]: r for r in api.listMine()}[got["readId"]]
    assert mine["state"] == "accepted" and not mine["flagged"]
    stored = JanusMRead().load(got["readId"], force=True)
    assert stored["check"]["mitral"]["source"] == "seed" and not stored["seeded"]
    # Nothing a reader received names the check seed or its file.
    seen = json.dumps([got, api.listMine(), api.getProject(clientProtocol=CP)], default=str)
    assert "checkSeed" not in seen and str(case["checkSeedFileId"]) not in seen
    assert _refusal(api.downloadSeed, readId=got["readId"]).code in (404, 409)


def test_r4s17_a_crash_never_spends_the_return(world, monkeypatch):
    """JA68: crash, then a failure -> RETURNED, unflagged, with its profile; a further
    failure -> accepted and flagged."""
    from girder_janusm.check import runOnce
    from girder_janusm.models import JanusMRead

    from janusm_reads import checker, phantom

    api = _api()
    jon = _reader("jonas")
    got = _take(api, jon, world.crashCase)
    wrong = phantom.move_border(world.truth, world.spacing, "epicardial", 2.0)

    real = checker.check_files
    monkeypatch.setattr(checker, "check_files",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("disk full")))
    _submit(api, world, jon, got["readId"], wrong)
    lines = []
    runOnce(out=lines.append)
    assert any("COULD NOT BE CHECKED" in line for line in lines)
    stored = JanusMRead().load(got["readId"], force=True)
    assert stored["state"] == "returned" and not stored["flagged"]
    assert (stored["returns"], stored["crashes"]) == (0, 1)
    monkeypatch.setattr(checker, "check_files", real)

    _submit(api, world, jon, got["readId"], wrong)
    runOnce(out=lambda _: None)
    _as(jon)
    mine = {r["readId"]: r for r in api.listMine()}[got["readId"]]
    assert mine["state"] == "returned" and not mine["flagged"]
    assert mine["checkProfile"]["epicardial"]["failed"]
    stored = JanusMRead().load(got["readId"], force=True)
    assert (stored["returns"], stored["crashes"], stored["attempts"]) == (1, 1, 2)

    _submit(api, world, jon, got["readId"], wrong)
    runOnce(out=lambda _: None)
    stored = JanusMRead().load(got["readId"], force=True)
    assert stored["state"] == "accepted" and stored["flagged"]
    assert any("epicardial" in r for r in stored["flagReasons"])
    assert stored["seconds"] == pytest.approx(3 * 61.5)


def test_r4s16_a_plane_less_read_is_returned_uncounted(world):
    """JA66: no fittable plane (neither the seed nor the read has a mitral gap) is
    "could not be checked": returned, unflagged, not counted as the return."""
    from girder_janusm.check import runOnce
    from girder_janusm.models import JanusMRead

    api = _api()
    kim = _reader("kimberly")
    got = _take(api, kim, world.planeless)
    for _ in range(2):                             # twice: still never flagged
        _submit(api, world, kim, got["readId"], world.plain)
        runOnce(out=lambda _: None)
        stored = JanusMRead().load(got["readId"], force=True)
        assert stored["state"] == "returned" and not stored["flagged"]
        assert stored["returns"] == 0
        assert stored["check"]["couldNotBeChecked"]
        assert stored["check"]["mitral"]["checked"] is False
    assert stored["crashes"] == 2
    _as(kim)
    mine = {r["readId"]: r for r in api.listMine()}[got["readId"]]
    assert mine["checkSummary"].startswith("The read could not be checked")
    api.release(readId=got["readId"])


# ----------------------------------------------------- waves and third reads


def _report(wave, seeded, flagged=True, shares=None):
    """The parts of an anchoring report the third-read route reads. Its seeded rows'
    changed shares give rule 2's flag (JA78): ``shares`` (per read, for every case), or
    1 % (following) when ``flagged`` and 20 % when not."""
    if shares is None:
        shares = [0.01, 0.01] if flagged else [0.2, 0.2]
    return json.dumps({"wave": wave, "rule2": {"flagged": flagged},
                       "rows": [{"case": c, "blank": False, "changedShare": list(shares)}
                                for c in seeded]})


def test_r4s18_third_reads_open_only_on_a_flagged_waves_draw(world):
    """JA68: an arbitrary list, 4 of the 5, or 6 names -> 400; so is an unflagged wave."""
    from girder_janusm.models import JanusMCase

    from janusm_reads import readset

    api = _api()
    six = world.sets["decision"][3:9]
    _as(world.people["anna"])
    assert _refusal(api.adminWave, wave="w5", cases=json.dumps(six)).code == 403
    _as(world.admin)
    assert _refusal(api.adminWave, wave="w5", cases=json.dumps(["c9999"])).code == 400
    assert _refusal(api.adminWave, wave="", cases=json.dumps(six)).code == 400
    assert api.adminWave(wave="w5", cases=json.dumps(six))["cases"] == sorted(six)
    # Pretend their two reads were accepted: the route counts the database's cases.
    JanusMCase().collection.update_many({"name": {"$in": six}}, {"$set": {"acceptedCount": 2}})
    try:
        drawn = readset.third_read_cases("w5", six)
        assert len(drawn) == 5
        left_out = next(c for c in six if c not in drawn)
        report = _report("w5", six)
        for cases in ([world.target], drawn[:4], drawn + [left_out], drawn + drawn[:1],
                      [world.sets["decision"][20]] + drawn[1:]):
            assert _refusal(api.adminThirdReads, wave="w5", report=report,
                            cases=json.dumps(cases)).code == 400
        for bad in (_report("w5", six, flagged=False), _report("w6", six),
                    _report("w5", six[:5])):
            assert _refusal(api.adminThirdReads, wave="w5", report=bad,
                            cases=json.dumps(drawn)).code == 400
        assert not JanusMCase().collection.count_documents({"thirdReadWanted": True})
    finally:
        JanusMCase().collection.update_many({"name": {"$in": six}},
                                            {"$set": {"acceptedCount": 0, "wave": None}})


# ---------------------------------------------------------------------- export


def test_third_reads_are_blank_by_a_fresh_reader_and_never_reference(world):
    """S5 point 5 (JA47 rule 2): an admin opens a flagged wave's third reads."""
    from girder_janusm.check import runOnce
    from girder_janusm.models import JanusMCase, JanusMRead

    api = _api()
    one = json.dumps([world.target])
    report = _report("1", [world.target])
    _as(world.people["anna"])
    assert _refusal(api.adminThirdReads, wave="1", report=report, cases=one).code == 403
    _as(world.admin)
    assert api.adminWave(wave="1", cases=one)["moved"] == []      # the same wave again: 200
    # Wave 1 is the target alone: its draw is the target.
    assert api.adminThirdReads(wave="1", report=report, cases=one)["opened"] == [world.target]
    assert api.adminThirdReads(wave="1", report=report,
                               cases=one)["alreadyOpen"] == [world.target]

    # Anna and Bobby read it: the third read goes to someone else.
    target = JanusMCase().findOne({"name": world.target})
    for login in ("anna", "bobby"):
        assert world.people[login]["_id"] in target["assignedUserIds"]
    gus = _reader("gustav")
    _as(gus)
    third = api.nextRead(clientProtocol=CP)
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
        got = api.nextRead(clientProtocol=CP)
        assert got["caseName"] != world.target
        api.release(readId=got["readId"])
    except Exception as exc:  # noqa: BLE001 - nothing left for cathy is fine too
        assert getattr(exc, "code", None) == 404


def test_export_feeds_the_anchoring_report(world):
    """S5 point 8 and R4-S21: one wave, a record per read, offsets in the canonical
    sign, border_protocol; seed offsets by default; seconds summed over attempts; third
    reads apart under third/ (R4-S18)."""
    from girder_janusm.export import export

    from janusm_reads import anchoring

    out = world.tmp / "wave1"
    manifest = export(str(out), str(world.seedsDir), wave="1", out=lambda _: None)
    assert manifest["border_protocol"] == 1 and manifest["wave"] == "1"
    assert [c["case"] for c in manifest["cases"]] == [world.target]   # wave 1 only
    # R5-S10 (JA78): the export carries the sha256 of the report that opened wave 1's
    # third reads.
    from girder_janusm.rest import reportSha256

    assert manifest["anchoringReportSha256"] == reportSha256(
        json.loads(_report("1", [world.target])))
    assert len(manifest["anchoringReportSha256"]) == 64
    assert manifest["skippedReads"] == []
    row = manifest["cases"][0]
    records = row["readRecords"]
    assert len(records) == 2 and not any(r["third"] for r in records)
    assert all(r["reference"] for r in records)
    for rec in records:
        assert set(rec) >= {"reader", "seeded", "blank", "seconds", "attempts", "returns",
                            "crashes", "flagged", "flagReasons", "halfMaxOffsetsMm",
                            "border_protocol", "cadrads", "reference"}
        assert rec["border_protocol"] == 1 and rec["seeded"] and not rec["blank"]
        assert rec["offsetSign"] == "canonical"
    byFlag = {r["flagged"]: r for r in records}
    assert byFlag[True]["seconds"] == pytest.approx(2 * 61.5)      # both attempts
    assert byFlag[False]["seconds"] == pytest.approx(61.5)
    assert byFlag[True]["attempts"] == 2 and byFlag[True]["flagReasons"]
    assert byFlag[True]["returns"] == 1
    assert byFlag[True]["halfMaxOffsetsMm"]["epicardial"] == pytest.approx(2.0, abs=0.4)
    assert byFlag[False]["attempts"] == 1
    assert abs(byFlag[False]["halfMaxOffsetsMm"]["endocardial"]) < 0.5
    assert {r["reader"] for r in records} == {str(world.people[k]["_id"])
                                              for k in ("anna", "bobby")}
    # The third read is exported apart, never as a reference read: no reads/ record is
    # a third read.
    assert row["thirdRead"] == f"third/{world.target}__third.nii.gz"
    assert row["thirdReadRecord"]["third"] and row["thirdReadRecord"]["reference"] is False
    assert all(p.startswith("reads/") for p in row["reads"])
    assert sorted(os.listdir(out / "reads")) == sorted(Path(p).name for p in row["reads"])
    assert not any("third" in name for name in os.listdir(out / "reads"))
    assert os.listdir(out / "third") == [f"{world.target}__third.nii.gz"]
    # Seed offsets are on by default.
    assert set(row["halfMaxOffsets"]["seed"]) == {"endocardial", "epicardial", "septal_rv"}

    report = anchoring.report_from_manifest(out / "manifest.json")
    assert report["cases"] == 1 and report["seededCases"] == 1
    assert report["borders"]["endocardial"]["interReadSeeded"] == pytest.approx(0.0)
    assert report["rows"][0]["thirdReadVsSeed"]["endocardial"] is not None
    assert "seedMedian" in report["halfMaxOffsets"]["endocardial"]

    bare = export(str(world.tmp / "wave1-bare"), str(world.seedsDir), wave="1",
                  seedOffsets=False, out=lambda _: None)
    assert "seed" not in bare["cases"][0]["halfMaxOffsets"]


def test_r4s21_export_refuses_an_empty_wave(world):
    from girder_janusm.export import ExportRefused, export

    for wave in ("", "  ", "no-such-wave"):
        with pytest.raises(ExportRefused, match="REFUSED"):
            export(str(world.tmp / "empty"), str(world.seedsDir), wave=wave,
                   out=lambda _: None)
    assert not (world.tmp / "empty").exists()


def test_r4s21_export_skips_and_lists_reads_not_under_border_protocol_1(world):
    from girder_janusm.export import export
    from girder_janusm.models import JanusMCase, JanusMRead

    case = JanusMCase().findOne({"name": world.target})
    read = JanusMRead().findOne({"caseId": case["_id"], "state": "accepted",
                                 "third": False, "flagged": False})
    JanusMRead().collection.update_one({"_id": read["_id"]},
                                       {"$unset": {"border_protocol": ""}})
    try:
        manifest = export(str(world.tmp / "wave1-old"), str(world.seedsDir), wave="1",
                          seedOffsets=False, out=lambda _: None)
    finally:
        JanusMRead().collection.update_one({"_id": read["_id"]},
                                           {"$set": {"border_protocol": 1}})
    assert manifest["cases"] == []          # one protocol-1 read left: not a double read
    assert manifest["skippedReads"] == [{"case": world.target, "read": str(read["_id"]),
                                         "border_protocol": None}]


# ============================================== Round 5, Group D (#232; JA76-JA79)


def test_r5s7_a_blank_case_with_no_check_seed_is_refused_and_alerted(world, caplog):
    """JA76: ``check.py`` refuses a blank read whose case has no ``checkSeedFileId``
    before checking (never fitting it to the read), alerts the PM, and counts a crash,
    not a return. The reader is not told why."""
    import logging

    from girder_janusm.check import checkRead
    from girder_janusm.models import JanusMCase, JanusMRead

    api = _api()
    case = JanusMCase().findOne({"name": world.noCheckSeed})
    assert case["blank"] and case["checkSeedFileId"]
    JanusMCase().collection.update_one({"_id": case["_id"]},
                                       {"$set": {"checkSeedFileId": None}})
    lena = _reader("lena")
    got = _take(api, lena, world.noCheckSeed)
    assert got["hasSeed"] is False
    _submit(api, world, lena, got["readId"], world.truth)
    with caplog.at_level(logging.ERROR, logger="girder_janusm.check"):
        checkRead(JanusMRead().load(got["readId"], force=True))
    stored = JanusMRead().load(got["readId"], force=True)
    assert stored["state"] == "returned" and not stored["flagged"]
    assert (stored["crashes"], stored["returns"], stored["attempts"]) == (1, 0, 1)
    assert stored["check"]["couldNotBeChecked"]
    assert "mitral" not in stored["check"]          # never checked, never fitted to the read
    alerts = [r for r in caplog.records if r.levelno == logging.ERROR
              and "COULD NOT BE CHECKED" in r.getMessage()
              and world.noCheckSeed in r.getMessage()]
    assert alerts and "checkSeedFileId" in alerts[0].getMessage()
    _as(lena)
    seen = json.dumps(api.listMine(), default=str)
    assert "check seed" not in seen.lower() and "checkSeed" not in seen
    world.noCheckSeedRead = got["readId"]


def test_r5s7_backfill_sets_the_check_seed_and_it_is_still_never_served(world):
    from girder.models.file import File
    from girder.models.folder import Folder
    from girder.models.item import Item
    from girder_janusm import populate
    from girder_janusm.models import JanusMCase

    lines = []
    dry = populate.backfillCheckSeeds(world.admin, str(world.seedsDir), dryRun=True,
                                      out=lines.append)
    assert dry == {"attach": 1, "cases": [world.noCheckSeed]}
    assert not JanusMCase().findOne({"name": world.noCheckSeed})["checkSeedFileId"]
    populate.main(["--backfill-check-seeds", "--seeds-dir", str(world.seedsDir)])
    case = JanusMCase().findOne({"name": world.noCheckSeed})
    assert case["checkSeedFileId"] and case["seedFileId"] is None
    item = Item().load(File().load(case["checkSeedFileId"], force=True)["itemId"], force=True)
    assert Folder().load(item["folderId"], force=True)["name"] == "check-seeds"
    # Nothing left to backfill; the seed is still never served (404).
    assert populate.backfillCheckSeeds(world.admin, str(world.seedsDir),
                                       out=lambda _: None)["attach"] == 0
    api = _api()
    _as(_user("lena"))
    assert _refusal(api.downloadSeed, readId=world.noCheckSeedRead).code == 404


def test_r5s8_an_unparseable_ct_header_refuses_lesion_points_and_moves_no_counter(world,
                                                                                 caplog):
    """JA77: 409 ct_bounds_unavailable for a form with a point; the read stays open and
    no counter moves; the PM is alerted. A form without points is accepted."""
    import logging

    from girder.models.folder import Folder
    from girder_janusm.models import JanusMCase, JanusMRead

    from janusm_reads import protocol

    case = JanusMCase().findOne({"name": world.noBounds})
    junkFolder = Folder().createFolder(world.admin, "not-a-ct", parentType="user",
                                       creator=world.admin, reuseExisting=True)
    junk = world.tmp / "not-a-ct.nii.gz"
    junk.write_bytes(b"this is not a NIfTI header" * 40)
    junkFile = _upload(junk, junkFolder, world.admin)
    JanusMCase().collection.update_one(
        {"_id": case["_id"]},
        {"$set": {"ctFileId": junkFile["_id"]}, "$unset": {"ctWorldBounds": ""}})
    try:
        api = _api()
        max_ = _reader("maxine")
        got = _take(api, max_, world.noBounds)
        before = JanusMRead().load(got["readId"], force=True)
        with caplog.at_level(logging.ERROR, logger="girder_janusm.rest"):
            refused = _refusal(_submit, api, world, max_, got["readId"], world.truth,
                               points={"LAD": [1.5, 2.0, 30.0]})
        assert refused.code == 409
        assert refused.extra["code"] == protocol.ERR_CT_BOUNDS == "ct_bounds_unavailable"
        after = JanusMRead().load(got["readId"], force=True)
        assert after["state"] == before["state"] == "assigned"
        for counter in ("attempts", "returns", "crashes", "seconds"):
            assert after[counter] == before[counter], counter
        assert after["fileId"] is None and after["lesionPoints"] == {}
        assert any(r.levelno == logging.ERROR and world.noBounds in r.getMessage()
                   for r in caplog.records)
        # The same read without lesion points is accepted for checking.
        done = _submit(api, world, max_, got["readId"], world.truth)
        assert done["state"] == "submitted"
        assert JanusMRead().load(got["readId"], force=True)["attempts"] == 1
    finally:
        JanusMCase().collection.update_one({"_id": case["_id"]},
                                           {"$set": {"ctFileId": case["ctFileId"]}})


def test_r5s9_a_case_with_an_accepted_read_in_wave_1_never_moves_to_wave_2(world):
    from girder_janusm.models import JanusMCase

    from janusm_reads import protocol

    api = _api()
    _as(world.admin)
    target = JanusMCase().findOne({"name": world.target})
    assert target["wave"] == "1" and target["acceptedCount"] == 2
    refused = _refusal(api.adminWave, wave="2", cases=json.dumps([world.target]))
    assert refused.code == 409 and refused.extra["code"] == protocol.ERR_WAVE_FROZEN
    assert JanusMCase().findOne({"name": world.target})["wave"] == "1"   # nothing moved
    assert api.adminWave(wave="1", cases=json.dumps([world.target]))["moved"] == []


def test_r5s9_an_unread_case_moves(world, caplog):
    import logging

    from girder_janusm.models import JanusMCase

    api = _api()
    _as(world.admin)
    with caplog.at_level(logging.WARNING, logger="girder_janusm.rest"):
        assert api.adminWave(wave="w9", cases=json.dumps([world.unreadMover]))["moved"] == [
            world.unreadMover]
        assert api.adminWave(wave="w8", cases=json.dumps([world.unreadMover]))["moved"] == [
            world.unreadMover]
    assert JanusMCase().findOne({"name": world.unreadMover})["wave"] == "w8"
    logged = [r.getMessage() for r in caplog.records if world.unreadMover in r.getMessage()]
    assert any("'w9' -> 'w8' by admin" in m for m in logged), logged


def test_r5s9_a_mixed_list_is_refused_and_nothing_moves(world):
    from girder_janusm.models import JanusMCase

    api = _api()
    _as(world.admin)
    names = [world.unreadMover, world.target]
    before = {c["name"]: c["wave"] for c in JanusMCase().find({"name": {"$in": names}})}
    assert _refusal(api.adminWave, wave="w7", cases=json.dumps(names)).code == 409
    after = {c["name"]: c["wave"] for c in JanusMCase().find({"name": {"$in": names}})}
    assert after == before == {world.unreadMover: "w8", world.target: "1"}
    # A case with a third read wanted (and none accepted) is frozen too.
    JanusMCase().collection.update_one({"name": world.unreadMover},
                                       {"$set": {"thirdReadWanted": True}})
    try:
        assert _refusal(api.adminWave, wave="w7",
                        cases=json.dumps([world.unreadMover])).code == 409
    finally:
        JanusMCase().collection.update_one({"name": world.unreadMover},
                                           {"$set": {"thirdReadWanted": False}})


def test_r5s10_a_flagged_report_whose_rows_do_not_flag_is_refused(world):
    """JA78: rule2.flagged is recomputed from the report's seeded rows."""
    from girder_janusm.models import JanusMCase, JanusMWave

    from janusm_reads import readset

    api = _api()
    six = world.sets["decision"][3:9]
    _as(world.admin)
    api.adminWave(wave="w6", cases=json.dumps(six))
    JanusMCase().collection.update_many({"name": {"$in": six}}, {"$set": {"acceptedCount": 2}})
    try:
        drawn = readset.third_read_cases("w6", six)
        # flagged: true, but 2 of 12 reads change < 5 %: the rows do not flag.
        rows = json.loads(_report("w6", six))
        for i, row in enumerate(rows["rows"]):
            row["changedShare"] = [0.01, 0.2] if i < 2 else [0.2, 0.2]
        refused = _refusal(api.adminThirdReads, wave="w6", report=json.dumps(rows),
                           cases=json.dumps(drawn))
        assert refused.code == 400 and "its seeded rows give False" in str(refused)
        # Exactly 5 % is not following either.
        exact = _report("w6", six, flagged=True, shares=[0.05, 0.05])
        assert _refusal(api.adminThirdReads, wave="w6", report=exact,
                        cases=json.dumps(drawn)).code == 400
        assert not JanusMCase().collection.count_documents(
            {"name": {"$in": six}, "thirdReadWanted": True})
        assert JanusMWave().reportHash("w6") is None      # nothing stored on a refusal
    finally:
        JanusMCase().collection.update_many({"name": {"$in": six}},
                                            {"$set": {"acceptedCount": 0, "wave": None}})


def test_r5s10_a_second_different_report_for_a_wave_is_refused(world):
    from girder_janusm.models import JanusMWave
    from girder_janusm.rest import reportSha256

    api = _api()
    one = json.dumps([world.target])
    _as(world.admin)
    held = JanusMWave().reportHash("1")
    assert held == reportSha256(json.loads(_report("1", [world.target])))
    other = _report("1", [world.target], shares=[0.02, 0.03])     # still flags; another report
    refused = _refusal(api.adminThirdReads, wave="1", report=other, cases=one)
    assert refused.code == 400 and "already has an anchoring report" in str(refused)
    assert JanusMWave().reportHash("1") == held
    # The same report again is not refused.
    again = api.adminThirdReads(wave="1", report=_report("1", [world.target]), cases=one)
    assert again["alreadyOpen"] == [world.target]


def test_r5s11_r4s17_a_plane_less_read_after_a_genuine_return(world, caplog):
    """R4-S17 in the Mongo job (JA79): a genuine failure (returns 1), then a plane-less
    submission -> returned, unflagged, returns 1, crashes 1, and the PM's "COULD NOT BE
    CHECKED" ERROR log."""
    import logging

    from girder_janusm.check import runOnce
    from girder_janusm.models import JanusMCase, JanusMRead

    from janusm_reads import phantom

    api = _api()
    nora = _reader("nora")
    got = _take(api, nora, world.afterReturn)
    _submit(api, world, nora, got["readId"], phantom.move_border(
        world.truth, world.spacing, "epicardial", 2.0))
    runOnce(out=lambda _: None)
    stored = JanusMRead().load(got["readId"], force=True)
    assert stored["state"] == "returned" and (stored["returns"], stored["crashes"]) == (1, 0)

    # The case's reference loses its mitral gap: the next check has no plane to fit.
    case = JanusMCase().findOne({"name": world.afterReturn})
    planeless = JanusMCase().findOne({"name": world.planeless})
    JanusMCase().collection.update_one({"_id": case["_id"]},
                                       {"$set": {"seedFileId": planeless["seedFileId"]}})
    try:
        _submit(api, world, nora, got["readId"], world.truth)   # its own gap would fit
        with caplog.at_level(logging.ERROR, logger="girder_janusm.check"):
            runOnce(out=lambda _: None)
    finally:
        JanusMCase().collection.update_one({"_id": case["_id"]},
                                           {"$set": {"seedFileId": case["seedFileId"]}})
    stored = JanusMRead().load(got["readId"], force=True)
    assert stored["state"] == "returned" and not stored["flagged"]
    assert (stored["returns"], stored["crashes"], stored["attempts"]) == (1, 1, 2)
    assert stored["check"]["couldNotBeChecked"]
    assert stored["check"]["mitral"]["checked"] is False
    assert stored["check"]["mitral"]["source"] is None             # never the read
    assert any(r.levelno == logging.ERROR and "COULD NOT BE CHECKED" in r.getMessage()
               and world.afterReturn in r.getMessage() for r in caplog.records)


def test_r5s11_s21_export_excludes_a_competing_wave_with_accepted_reads(world):
    from girder_janusm.export import export
    from girder_janusm.models import JanusMCase, JanusMRead

    api = _api()
    _as(world.admin)
    assert api.adminWave(wave="2", cases=json.dumps([world.competing]))["moved"] == [
        world.competing]
    competing = JanusMCase().findOne({"name": world.competing})
    target = JanusMCase().findOne({"name": world.target})
    for read in JanusMRead().find({"caseId": target["_id"], "state": "accepted",
                                   "third": False}):
        copy = {k: v for k, v in read.items() if k != "_id"}
        copy["caseId"] = competing["_id"]
        JanusMRead().collection.insert_one(copy)
    JanusMCase().collection.update_one({"_id": competing["_id"]},
                                       {"$set": {"acceptedCount": 2}})
    # Wave 2 is a real double-read wave ...
    two = export(str(world.tmp / "wave2"), str(world.seedsDir), wave="2",
                 seedOffsets=False, out=lambda _: None)
    assert [c["case"] for c in two["cases"]] == [world.competing]
    # ... and --wave 1 excludes it.
    one = export(str(world.tmp / "wave1-again"), str(world.seedsDir), wave="1",
                 seedOffsets=False, out=lambda _: None)
    assert [c["case"] for c in one["cases"]] == [world.target]
    assert not any(world.competing in name
                   for name in os.listdir(world.tmp / "wave1-again" / "reads"))
    # And a read case never changes wave.
    assert _refusal(api.adminWave, wave="1", cases=json.dumps([world.competing])).code == 409


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
