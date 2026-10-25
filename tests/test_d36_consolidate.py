"""D36 (issue #124): the janus consolidation tool, girder_segqueue14.consolidate.

The steps -- deleting the old groups, archiving the old queue's folders and dropping
the empty SegQueue14 collection -- run against a real Girder on a scratch MongoDB
(``needs_mongo``, as test_segqueue_server14.py):

    SEGQUEUE_TEST_MONGO=mongodb://localhost:27099 pytest tests/test_d36_consolidate.py
"""

import io
import os
import sys
import uuid
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
for extra in (REPO / "src", REPO / "server"):
    if str(extra) not in sys.path:
        sys.path.append(str(extra))

MONGO_ENV = "SEGQUEUE_TEST_MONGO"
TOOL = REPO / "server" / "girder_segqueue14" / "consolidate.py"
SCRIPT = REPO / "deploy" / "segqueue14-deploy.sh"
#: Out of scope for D36: no step may change them.
UNTOUCHED = ("CCTA-Pool", "ImageCAS-X")


def test_no_d36_code_path_names_the_untouched_collections():
    """The tool works only on SegQueue and SegQueue14; CCTA-Pool and ImageCAS-X
    appear in it as prose at most, never as a name it looks up."""
    source = TOOL.read_text()
    for name in UNTOUCHED:
        assert f"'{name}'" not in source and f'"{name}"' not in source
    assert "pool-migrate" not in SCRIPT.read_text()


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
    # Girder binds its database on first import, so the URI is set before
    # anything from Girder is imported, unless another server test bound it.
    created = None
    if "girder.models" not in sys.modules:
        created = f"segqueue14_test_{uuid.uuid4().hex[:8]}"
        os.environ["GIRDER_MONGO_URI"] = f"{uri.rstrip('/')}/{created}"
    pytest.importorskip("girder")
    from girder_segqueue14.models import Case14

    bound = Case14().collection.database.name
    if not bound.startswith(("segqueue14_test_", "segqueue_test_")):
        pytest.fail(f"girder is bound to {bound!r}, which is not a scratch test database")
    from girder.models.assetstore import Assetstore

    root = tmp_path_factory.mktemp("assetstore")
    os.environ.setdefault("GIRDER_FILESYSTEMASSETSTORE_RESERVED_MBYTES", "16")
    if Assetstore().findOne() is None:
        Assetstore().createFilesystemAssetstore(name="test", root=str(root))
    yield bound
    if created:
        client.drop_database(created)


def _put(folder, user, name, data: bytes):
    from girder.models.upload import Upload

    return Upload().uploadFromFile(io.BytesIO(data), size=len(data), name=name,
                                   parentType="folder", parent=folder, user=user)


def _snapshot(name):
    """Every folder, item and file document under a collection, with its bytes."""
    from girder.models.collection import Collection
    from girder.models.file import File
    from girder.models.folder import Folder
    from girder.models.item import Item

    coll = Collection().findOne({"name": name})
    folders = sorted((str(f["_id"]), f["name"], str(f["parentId"]))
                     for f in Folder().find({"baseParentId": coll["_id"]}))
    items = sorted((str(i["_id"]), i["name"], str(i["folderId"]))
                   for i in Item().find({"baseParentId": coll["_id"]}))
    files = sorted((str(f["_id"]), f["name"], f["sha512"],
                    b"".join(File().download(f, headers=False)()))
                   for i in Item().find({"baseParentId": coll["_id"]})
                   for f in Item().childFiles(i))
    return folders, items, files


@pytest.fixture
def janus(girder_db, monkeypatch):
    """A miniature janus before D36: the old queue's folders in SegQueue, the
    empty SegQueue14 collection, both group pairs, and CCTA-Pool and ImageCAS-X
    beside them."""
    from girder.models.collection import Collection
    from girder.models.file import File
    from girder.models.folder import Folder
    from girder.models.group import Group
    from girder.models.item import Item
    from girder.models.user import User
    from girder_segqueue14 import consolidate
    from girder_segqueue14.models import Case14, Submission14

    monkeypatch.setattr(consolidate, "oldPluginInstalled", lambda: False)
    for model in (User, Group, Collection, Folder, Item, File, Case14, Submission14):
        model().collection.delete_many({})
    admin = User().createUser("admin", "password1", "A", "Dmin", "admin@example.org",
                              admin=True)
    aaron = User().createUser("aaron", "password1", "Aa", "Ron", "aaron@example.org")
    old = User().createUser("oldie", "password1", "Ol", "Die", "oldie@example.org")
    groups = {n: Group().createGroup(n, creator=admin, public=False)
              for n in ("segqueue-annotators", "segqueue-reviewers",
                        "segqueue14-annotators", "segqueue14-reviewers")}
    for group in groups.values():
        Group().addUser(group, aaron)
    Group().addUser(groups["segqueue-annotators"], old)

    live = Collection().createCollection("SegQueue", creator=admin, public=False)
    cases = Folder().createFolder(live, "cases", parentType="collection", creator=admin)
    _put(cases, admin, "ImageCHD__1001.nii.gz", b"CT" * 500)
    for name in ("gold", "incoming", "submissions"):
        f = Folder().createFolder(live, name, parentType="collection", creator=admin)
        _put(f, admin, f"{name}-thing.nii.gz", name.encode() * 10)
    s14 = Collection().createCollection("SegQueue14", creator=admin, public=False)
    Folder().createFolder(s14, "incoming", parentType="collection", creator=admin)
    for name in UNTOUCHED:
        coll = Collection().createCollection(name, creator=admin, public=False)
        ds = Folder().createFolder(coll, "ImageCHD", parentType="collection", creator=admin)
        case = Folder().createFolder(ds, "1001", parentType="folder", creator=admin)
        _put(case, admin, "ct.nii.gz", b"CT" * 500)
        _put(case, admin, "label.nii.gz", name.encode() * 50)
        Folder().createFolder(coll, "_trash", parentType="collection", creator=admin)

    w = type("Janus", (), {})()
    w.tool, w.admin, w.live, w.aaron, w.oldie = consolidate, admin, live, aaron, old
    return w


@pytest.mark.needs_mongo
def test_groups_refused_while_old_plugin_installed_then_deleted(janus, monkeypatch):
    from girder.models.group import Group
    from girder.models.user import User

    monkeypatch.setattr(janus.tool, "oldPluginInstalled", lambda: True)
    with pytest.raises(SystemExit, match="retire-live"):
        janus.tool.retireGroups(apply=True)
    monkeypatch.setattr(janus.tool, "oldPluginInstalled", lambda: False)
    janus.tool.retireGroups()
    assert Group().findOne({"name": "segqueue-annotators"}) is not None
    janus.tool.retireGroups(apply=True)
    names = {g["name"] for g in Group().find({"name": {"$regex": "^segqueue"}})}
    assert names == {"segqueue14-annotators", "segqueue14-reviewers"}
    assert len(User().load(janus.aaron["_id"], force=True)["groups"]) == 2
    assert User().load(janus.oldie["_id"], force=True)["groups"] == []
    janus.tool.retireGroups(apply=True)                                # idempotent


@pytest.mark.needs_mongo
def test_collection_move_and_drop(janus):
    from girder.models.collection import Collection
    from girder.models.folder import Folder
    from girder.models.item import Item

    janus.tool.consolidateCollection("move")
    assert janus.tool._child(janus.live, "collection", "gold") is not None
    janus.tool.consolidateCollection("move", apply=True)
    archive = janus.tool._child(janus.live, "collection", "_archive-4class")
    moved = {f["name"]: f for f in Folder().find({"parentId": archive["_id"]})}
    assert set(moved) == {"gold", "incoming", "submissions"}
    assert Item().findOne({"folderId": moved["gold"]["_id"]})["name"] == "gold-thing.nii.gz"
    for name in ("gold", "incoming", "submissions"):
        assert janus.tool._child(janus.live, "collection", name) is None
    janus.tool.consolidateCollection("move", apply=True)              # idempotent
    janus.tool.consolidateCollection("drop")
    assert Collection().findOne({"name": "SegQueue14"}) is not None
    janus.tool.consolidateCollection("drop", apply=True)
    assert Collection().findOne({"name": "SegQueue14"}) is None
    # SegQueue14 now writes into SegQueue, in fresh folders of its own.
    from girder_segqueue14.utils import incomingFolder, rootCollection, submissionsFolder

    assert rootCollection()["_id"] == janus.live["_id"]
    for folder in (incomingFolder(janus.admin), submissionsFolder(janus.admin)):
        assert folder["parentId"] == janus.live["_id"]
        assert Item().findOne({"folderId": folder["_id"]}) is None


@pytest.mark.needs_mongo
def test_collection_steps_refused_once_segqueue14_wrote(janus):
    from girder_segqueue14.models import Case14, Submission14

    Submission14().collection.insert_one({"caseId": None, "authorRole": "annotator"})
    with pytest.raises(SystemExit, match="1 submissions"):
        janus.tool.consolidateCollection("move", apply=True)
    Submission14().collection.delete_many({})
    Case14().collection.insert_one({"name": "x", "prelabelFileId": None,
                                    "prelabelVersion": "icx4-v1"})
    with pytest.raises(SystemExit, match="1 prelabelled cases"):
        janus.tool.consolidateCollection("drop", apply=True)
    assert janus.tool._child(janus.live, "collection", "gold") is not None


@pytest.mark.needs_mongo
def test_drop_refused_while_segqueue14_holds_an_item(janus):
    from girder.models.collection import Collection

    s14 = Collection().findOne({"name": "SegQueue14"})
    incoming = janus.tool._child(s14, "collection", "incoming")
    _put(incoming, janus.admin, "upload.nii.gz", b"x" * 10)
    with pytest.raises(SystemExit, match="holds 1 items"):
        janus.tool.consolidateCollection("drop", apply=True)
    assert Collection().findOne({"name": "SegQueue14"}) is not None


@pytest.mark.needs_mongo
def test_every_step_leaves_ccta_pool_and_imagecas_x_as_they_were(janus):
    before = {name: _snapshot(name) for name in UNTOUCHED}
    janus.tool.retireGroups(apply=True)
    janus.tool.consolidateCollection("move", apply=True)
    janus.tool.consolidateCollection("drop", apply=True)
    assert {name: _snapshot(name) for name in UNTOUCHED} == before
