"""The Bradensbay branding of Girder's web UI (``segqueue14-deploy.sh branding``).

The values are checked against the repository: the brand name as the logo files spell
it and the banner colour as the navy of ``bradensbay-*.svg``. The deploy script and the
workflow carry the step with no arguments (the workflow's allow-list itself is tested
in ``test_segqueue14_janus_workflow.py``).

Applying, re-applying and restoring run against a real Girder on a scratch MongoDB
(``needs_mongo``, through ``test_segqueue_server14``'s fixture; CI's server job, which
refuses skips):

    SEGQUEUE_TEST_MONGO=mongodb://localhost:27099 pytest tests/test_segqueue_server14_branding.py
"""

import importlib.util
import json
import re
import sys
from collections import Counter
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import test_segqueue_server14 as base  # noqa: E402  (puts src/ and server/ on the path)

# By file, not through the package: girder_segqueue14/__init__ imports Girder, which
# the plain test job does not install. branding.py imports Girder only when it runs.
_spec = importlib.util.spec_from_file_location(
    "girder_segqueue14_branding", REPO / "server" / "girder_segqueue14" / "branding.py")
branding = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(branding)

girder_db = base.girder_db

LOGOS = sorted((REPO / "slicer/SegQueue/Resources/Logo").glob("bradensbay-*.svg"))
SCRIPT = REPO / "deploy" / "segqueue14-deploy.sh"
WORKFLOW = REPO / ".github" / "workflows" / "segqueue14-janus.yml"
DEPLOY_MD = REPO / "server" / "girder_segqueue14" / "DEPLOY.md"


# ------------------------------------------------------------------ the values


def _fills(svg: Path):
    return [c.upper() for c in re.findall(r'fill="(#[0-9A-Fa-f]{6})"', svg.read_text())]


def test_there_are_logo_files():
    assert len(LOGOS) >= 4, LOGOS


def test_banner_colour_is_the_navy_of_the_logos():
    # The navy fills every non-reversed mark and wordmark; the reversed ones are drawn
    # for a navy ground and stroke it instead.
    assert branding.BANNER_COLOR == "#0A2540"
    for svg in LOGOS:
        text = svg.read_text().upper()
        if "reversed" in svg.name and "-mark" not in svg.name:
            assert "#FFFFFF" in text, svg.name
        else:
            assert branding.BANNER_COLOR in _fills(svg), svg.name


def test_banner_colour_is_the_dark_brand_colour():
    colours = Counter(c for svg in LOGOS for c in _fills(svg) if c != "#FFFFFF")
    assert set(colours) == {"#0A2540", "#16BFB2"}, colours

    def luminance(hex_):
        r, g, b = (int(hex_[i:i + 2], 16) / 255 for i in (1, 3, 5))
        return 0.2126 * r + 0.7152 * g + 0.0722 * b

    # The darker of the two, so Girder's header keeps white text, as with its default.
    assert branding.BANNER_COLOR == min(colours, key=luminance)


def test_banner_colour_passes_girders_rule():
    # girder.settings.SettingValidator._validateBannerColor
    assert re.match(r"^#[0-9A-Fa-f]{6}$", branding.BANNER_COLOR)


def test_brand_name_is_the_one_in_the_repository():
    labels = {m for svg in LOGOS for m in re.findall(r'aria-label="([^"]*)"', svg.read_text())}
    assert labels == {branding.BRAND_NAME} == {"Bradensbay"}
    readme = (REPO / "slicer" / "SegQueue" / "README.md").read_text()
    assert 'alt="Bradensbay"' in readme


def test_only_the_two_settings():
    assert branding.WANTED == {"core.brand_name": "Bradensbay", "core.banner_color": "#0A2540"}


# ------------------------------------------------------------------ the step


def test_deploy_script_runs_the_tool_with_only_apply():
    text = SCRIPT.read_text()
    assert re.search(r"^\s+branding\) shift; branding \"\$@\" ;;$", text, re.M)
    body = text[text.index("branding() {"):]
    body = body[:body.index("\n}\n")]
    assert "-m girder_segqueue14.branding" in body
    assert 'die "branding: takes only --apply"' in body
    # The step never restarts Girder or installs anything.
    for word in ("restart_girder", "pip install", "systemctl", "--restore"):
        assert word not in body, word


def test_workflow_offers_the_step():
    import yaml

    wf = yaml.safe_load(WORKFLOW.read_text())
    on = wf.get("on", wf.get(True))
    options = on["workflow_dispatch"]["inputs"]["command"]["options"]
    assert "branding" in options and "branding --apply" in options


def test_deploy_md_documents_it():
    text = DEPLOY_MD.read_text()
    for needle in ("branding --apply", "core.brand_name", "core.banner_color",
                   "#0A2540", "Bradensbay", "--restore="):
        assert needle in text, needle


def test_restore_refuses_other_keys_before_girder():
    for raw in ("not json", "[]", "{}", '{"core.smtp_host": "x"}',
                '{"core.brand_name": 5}', '{"core.brand_name": "x", "core.privacy_notice": null}'):
        with pytest.raises(branding.Refused):
            branding.restore(raw)


def test_refuses_another_girder_major(monkeypatch):
    monkeypatch.setattr(branding, "girderVersion", lambda: "3.2.18")
    with pytest.raises(branding.Refused, match="not Girder 5"):
        branding.checkGirder()
    assert branding.main([]) == 2


# ------------------------------------------------------------------ real MongoDB


def _others():
    """Every setting this step does not own, as stored."""
    from girder.models.setting import Setting

    return sorted((d["key"], json.dumps(d["value"], sort_keys=True, default=str))
                  for d in Setting().find({"key": {"$nin": list(branding.WANTED)}}))


def _stored(key):
    from girder.models.setting import Setting

    doc = Setting().findOne({"key": key})
    return None if doc is None else doc["value"]


@pytest.fixture()
def clean_settings(girder_db):
    from girder.models.setting import Setting

    for key in branding.WANTED:
        Setting().unset(key)
    # Another setting, to prove the step leaves it alone.
    Setting().set("core.contact_email_address", "admin@example.org")
    yield
    for key in [*branding.WANTED, "core.contact_email_address"]:
        Setting().unset(key)


@pytest.mark.needs_mongo
def test_dry_run_changes_nothing(clean_settings, capsys):
    before = _others()
    old = branding.brand(apply=False)
    out = capsys.readouterr().out
    assert old == {"core.banner_color": None, "core.brand_name": None}
    assert _stored("core.brand_name") is None and _stored("core.banner_color") is None
    assert _others() == before
    # Current and new value of each setting, and that nothing changed.
    default = "(not stored: Girder's default)"
    assert f"core.brand_name: current 'Girder' {default} -> new 'Bradensbay'" in out
    assert f"core.banner_color: current '#3F3B3B' {default} -> new '#0A2540'" in out
    assert "dry run: nothing changed" in out


@pytest.mark.needs_mongo
def test_apply_reapply_and_restore(clean_settings, capsys):
    from girder.models.setting import Setting

    # An earlier hand-set banner colour, to see it restored as stored.
    Setting().set("core.banner_color", "#123456")
    before = _others()

    assert branding.main(["--apply"]) == 0
    out = capsys.readouterr().out
    assert Setting().get("core.brand_name") == "Bradensbay"
    assert Setting().get("core.banner_color") == "#0A2540"
    assert _others() == before
    old = {"core.banner_color": "#123456", "core.brand_name": None}
    assert "core.banner_color: current '#123456' (stored) -> new '#0A2540'" in out
    line = next(x for x in out.splitlines() if "to put the old values back" in x)
    restore_json = line.split("--restore='", 1)[1].rstrip("'")
    assert json.loads(restore_json) == old

    # What Girder hands its web client.
    from girder.api.v1.system import System

    public = System().getPublicSettings()
    assert public["core.brand_name"] == "Bradensbay"
    assert public["core.banner_color"] == "#0A2540"

    # Again: nothing to do, nothing written.
    stamp = [Setting().findOne({"key": k}) for k in branding.WANTED]
    assert branding.main(["--apply"]) == 0
    out = capsys.readouterr().out
    assert "already Bradensbay-branded; nothing to change" in out
    assert "-> unchanged" in out and "set to" not in out
    assert [Setting().findOne({"key": k}) for k in branding.WANTED] == stamp

    # And back, with exactly what the apply printed.
    assert branding.main([f"--restore={restore_json}"]) == 0
    assert _stored("core.brand_name") is None
    assert Setting().get("core.brand_name") == "Girder"
    assert _stored("core.banner_color") == "#123456"
    assert _others() == before


@pytest.mark.needs_mongo
def test_girder_still_validates(clean_settings, monkeypatch):
    from girder.exceptions import ValidationException

    monkeypatch.setitem(branding.WANTED, "core.banner_color", "navy")
    with pytest.raises(ValidationException):
        branding.brand(apply=True)
    # Checked before anything is written: the valid brand name was not stored either.
    assert _stored("core.brand_name") is None and _stored("core.banner_color") is None
