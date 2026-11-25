"""Girder's minimum upload chunk size set to 0 (``segqueue14-deploy.sh upload-chunks``).

Why: the module uploads in 768 KiB chunks (under janus's 1 MiB nginx limit) and
Girder refuses any non-final chunk under ``core.upload_minimum_chunk_size`` (5 MiB by
default) with HTTP 400 "Chunk is smaller than the minimum size.".

Here: the step's wiring (deploy script, workflow, DEPLOY.md), its refusals before
Girder, and -- against a real Girder on a scratch MongoDB (``needs_mongo``, through
``test_segqueue_server14``'s fixture; CI's server job, which refuses skips) -- dry
run, apply, re-apply, restore, and the refusal when an assetstore is not a
filesystem one. That Girder's check and the real client agree is checked over real
HTTP by ``tests/segqueue14_upload_chunks_e2e.py`` in CI's acceptance job.

    SEGQUEUE_TEST_MONGO=mongodb://localhost:27099 \
        pytest tests/test_segqueue_server14_upload_chunks.py
"""

import importlib.util
import json
import re
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import test_segqueue_server14 as base  # noqa: E402  (puts src/ and server/ on the path)

# By file, not through the package: girder_segqueue14/__init__ imports Girder, which
# the plain test job does not install. upload_chunks.py imports Girder only when it runs.
_spec = importlib.util.spec_from_file_location(
    "girder_segqueue14_upload_chunks", REPO / "server" / "girder_segqueue14" / "upload_chunks.py")
upload_chunks = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(upload_chunks)

girder_db = base.girder_db

SCRIPT = REPO / "deploy" / "segqueue14-deploy.sh"
WORKFLOW = REPO / ".github" / "workflows" / "segqueue14-janus.yml"
DEPLOY_MD = REPO / "server" / "girder_segqueue14" / "DEPLOY.md"
CI = REPO / ".github" / "workflows" / "ci.yml"
KEY = "core.upload_minimum_chunk_size"
GIRDER_DEFAULT = 5 * 1024 * 1024


# ------------------------------------------------------------------ the step


def test_only_the_one_setting_and_zero():
    assert upload_chunks.KEY == KEY
    assert upload_chunks.WANTED == 0


def test_deploy_script_runs_the_tool_with_only_apply():
    text = SCRIPT.read_text()
    assert re.search(r'^\s+upload-chunks\) shift; upload_chunks "\$@" ;;$', text, re.M)
    body = text[text.index("upload_chunks() {"):]
    body = body[:body.index("\n}\n")]
    assert "-m girder_segqueue14.upload_chunks" in body
    assert 'die "upload-chunks: takes only --apply"' in body
    # Like branding: never restarts Girder, installs anything or restores.
    for word in ("restart_girder", "pip install", "systemctl", "--restore"):
        assert word not in body, word
    # The usage text (printed for an unknown step) still reaches the new step.
    usage = int(re.search(r"\*\) sed -n '2,(\d+)p'", text).group(1))
    assert "upload-chunks [--apply]" in "\n".join(text.splitlines()[1:usage])


def test_install_does_not_run_it_so_the_docs_say_run_once():
    text = SCRIPT.read_text()
    body = text[text.index("\ninstall() {"):]
    body = body[:body.index("\n}\n")]
    assert "upload_chunks" not in body
    assert "install does not run it" in text
    assert "**`install` does not run it**" in DEPLOY_MD.read_text()


def test_workflow_offers_the_step():
    import yaml

    wf = yaml.safe_load(WORKFLOW.read_text())
    on = wf.get("on", wf.get(True))
    options = on["workflow_dispatch"]["inputs"]["command"]["options"]
    assert "upload-chunks" in options and "upload-chunks --apply" in options


def test_deploy_md_documents_it():
    text = DEPLOY_MD.read_text()
    for needle in ("upload-chunks --apply", KEY, "Chunk is smaller than the minimum size",
                   "filesystem", "--restore=", "nginx stays at 1 MiB"):
        assert needle in text, needle


def test_ci_runs_the_real_client_check_and_this_file():
    text = CI.read_text()
    assert "tests/segqueue14_upload_chunks_e2e.py" in text
    assert "tests/test_segqueue_server14_upload_chunks.py" in text


@pytest.mark.parametrize("raw", [
    "not json", "[]", "{}", '{"core.brand_name": null}',
    '{"core.upload_minimum_chunk_size": -1}', '{"core.upload_minimum_chunk_size": "5"}',
    '{"core.upload_minimum_chunk_size": true}',
    '{"core.upload_minimum_chunk_size": 0, "core.brand_name": null}',
])
def test_restore_refuses_before_girder(raw):
    with pytest.raises(upload_chunks.Refused):
        upload_chunks.restore(raw)


def test_refuses_another_girder_major(monkeypatch):
    monkeypatch.setattr(upload_chunks, "girderVersion", lambda: "3.2.18")
    with pytest.raises(upload_chunks.Refused, match="not Girder 5"):
        upload_chunks.checkGirder()
    assert upload_chunks.main([]) == 2


def test_refuses_any_assetstore_that_is_not_filesystem(monkeypatch):
    monkeypatch.setattr(upload_chunks, "assetstores", lambda: [("fs", 0), ("bucket", 2)])
    with pytest.raises(upload_chunks.Refused, match=r"'bucket' \(type 2\)"):
        upload_chunks.checkAssetstores()
    monkeypatch.setattr(upload_chunks, "assetstores", lambda: [])
    with pytest.raises(upload_chunks.Refused, match="no assetstore"):
        upload_chunks.checkAssetstores()
    monkeypatch.setattr(upload_chunks, "assetstores", lambda: [("fs", 0), ("fs2", 0)])
    assert upload_chunks.checkAssetstores() == [("fs", 0), ("fs2", 0)]


# ------------------------------------------------------------------ real MongoDB


def _stored():
    from girder.models.setting import Setting

    doc = Setting().findOne({"key": KEY})
    return None if doc is None else doc["value"]


def _others():
    from girder.models.setting import Setting

    return sorted((d["key"], json.dumps(d["value"], sort_keys=True, default=str))
                  for d in Setting().find({"key": {"$ne": KEY}}))


@pytest.fixture()
def clean_setting(girder_db):
    from girder.models.setting import Setting

    Setting().unset(KEY)
    Setting().set("core.contact_email_address", "admin@example.org")
    yield
    Setting().unset(KEY)
    Setting().unset("core.contact_email_address")


@pytest.mark.needs_mongo
def test_dry_run_changes_nothing(clean_setting, capsys):
    from girder.models.setting import Setting

    assert Setting().get(KEY) == GIRDER_DEFAULT  # Girder 5's default, the cause
    before = _others()
    assert upload_chunks.configure(apply=False) == {KEY: None}
    out = capsys.readouterr().out
    assert _stored() is None and _others() == before
    assert (f"{KEY}: current {GIRDER_DEFAULT} (not stored: Girder's default) -> new 0"
            in out)
    assert "(filesystem)" in out
    assert "dry run: nothing changed" in out


@pytest.mark.needs_mongo
def test_apply_reapply_and_restore(clean_setting, capsys):
    from girder.models.setting import Setting

    before = _others()
    assert upload_chunks.main(["--apply"]) == 0
    out = capsys.readouterr().out
    assert Setting().get(KEY) == 0 and _stored() == 0
    assert _others() == before
    assert f"{KEY} set to 0" in out
    line = next(x for x in out.splitlines() if "to put the old value back" in x)
    restore_json = line.split("--restore='", 1)[1].rstrip("'")
    assert json.loads(restore_json) == {KEY: None}

    # Again: nothing to do, nothing written.
    stamp = Setting().findOne({"key": KEY})
    assert upload_chunks.main(["--apply"]) == 0
    out = capsys.readouterr().out
    assert "already 0; nothing to change" in out and "set to" not in out
    assert Setting().findOne({"key": KEY}) == stamp

    # Back to Girder's default, with exactly what the apply printed.
    assert upload_chunks.main([f"--restore={restore_json}"]) == 0
    assert _stored() is None and Setting().get(KEY) == GIRDER_DEFAULT

    # A hand-set value comes back as stored.
    Setting().set(KEY, 1024)
    upload_chunks.main(["--apply"])
    out = capsys.readouterr().out
    assert f"{KEY}: current 1024 (stored) -> new 0" in out
    assert upload_chunks.main([f"--restore={json.dumps({KEY: 1024})}"]) == 0
    assert _stored() == 1024
    assert _others() == before


@pytest.mark.needs_mongo
def test_refuses_with_an_s3_assetstore(clean_setting, capsys):
    from girder.models.assetstore import Assetstore

    # Inserted raw: Girder's own save would try to reach the bucket.
    inserted = Assetstore().collection.insert_one(
        {"name": "s3-bucket", "type": 2, "bucket": "x", "prefix": "", "current": False})
    try:
        assert upload_chunks.main(["--apply"]) == 2
        out = capsys.readouterr().out
        assert "REFUSED" in out and "'s3-bucket' (type 2)" in out
        assert _stored() is None
    finally:
        Assetstore().collection.delete_one({"_id": inserted.inserted_id})
    assert upload_chunks.main(["--apply"]) == 0
    assert _stored() == 0
