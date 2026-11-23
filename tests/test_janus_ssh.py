"""Janus through the gateway: the workflows' wiring and deploy/janus-ssh.sh, with stubs.

The end-to-end proof, against two real sshd, is tests/test_janus_ssh_e2e.py (CI job
``janus-ssh``). These need nothing but bash: ``ssh``, ``sshpass``, ``ssh-keyscan`` and
``ssh-keygen`` are stubs that record what they were asked to do.
"""

import re
import shutil
import subprocess
import time
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = [ROOT / ".github/workflows/segqueue14-janus.yml",
             ROOT / ".github/workflows/server-ssh.yml"]
HELPER = ROOT / "deploy/janus-ssh.sh"
BACKUP = ROOT / "deploy/backup/workflow-backup.sh"

pytestmark = pytest.mark.skipif(not shutil.which("bash"), reason="no bash")


def _steps(workflow):
    wf = yaml.safe_load(workflow.read_text())
    return next(iter(wf["jobs"].values()))["steps"]


def _step(workflow, name):
    return next(s for s in _steps(workflow) if s.get("name", "").startswith(name))


def _secret_vars(step):
    return {k: re.search(r"secrets\.(\w+)", v).group(1)
            for k, v in (step.get("env") or {}).items()
            if isinstance(v, str) and "secrets." in v}


# --- the workflows -----------------------------------------------------------------

@pytest.mark.parametrize("workflow", WORKFLOWS, ids=lambda p: p.name)
def test_trust_step_wires_both_hops(workflow):
    step = _step(workflow, "Trust the host keys")
    assert "bash deploy/janus-ssh.sh trust" in step["run"]
    assert _secret_vars(step) == {
        "GATEWAY_HOST": "GATEWAY_HOST", "HOST": "SSH_HOST", "GATEWAY_PORT": "GATEWAY_PORT",
        "MAIN_SERVER_LAN": "MAIN_SERVER_LAN", "PORT": "SSH_PORT", "USERNAME": "SSH_USERNAME",
        "SSHPASS": "SSH_PASSWORD", "KNOWN": "SSH_KNOWN_HOSTS",
        "KNOWN_GATEWAY": "SSH_KNOWN_HOSTS_GATEWAY"}


@pytest.mark.parametrize("workflow", WORKFLOWS, ids=lambda p: p.name)
def test_no_direct_ssh_to_janus_is_left(workflow):
    # Every connection to janus goes through the helper: no step runs ssh,
    # sshpass or ssh-keyscan itself (the old ones failed at ssh-keyscan).
    for step in _steps(workflow):
        run = "\n".join(ln for ln in step.get("run", "").splitlines() if "apt-get" not in ln)
        assert not re.search(r"\b(sshpass|ssh-keyscan)\b", run), step["name"]
        assert not re.search(r"(^|[|;&]\s*)ssh\s", run, re.M), step["name"]
    assert re.search(r'janus-ssh\.sh"? run', workflow.read_text())


@pytest.mark.parametrize("workflow", WORKFLOWS, ids=lambda p: p.name)
def test_secrets_check_names_the_gateway_secrets(workflow, tmp_path):
    step = _step(workflow, "Check the secrets are set")
    env = {"PATH": "/usr/bin:/bin", "GITHUB_STEP_SUMMARY": str(tmp_path / "s"),
           **{k: "" for k in step["env"]}, "HOST": "h", "USERNAME": "u", "PASSWORD": "p"}
    done = subprocess.run(["bash", "-c", step["run"]], env=env, capture_output=True, text=True)
    assert done.returncode != 0
    assert "GATEWAY_PORT" in done.stdout and "MAIN_SERVER_LAN" in done.stdout
    ok = subprocess.run(["bash", "-c", step["run"]], capture_output=True, text=True,
                        env={**env, "GATEWAY_PORT": "1", "MAIN_SERVER_LAN": "10.0.0.1",
                             "CMD": "status"})
    assert ok.returncode == 0, ok.stdout + ok.stderr


# echo/printf as a command (not inside a quoted remote command such as "echo $b64 | ...").
ECHO = re.compile(r"(^|[;&|(]|\bthen|\bdo|\|\||&&)\s*(echo|printf)\b")


@pytest.mark.parametrize("workflow", WORKFLOWS, ids=lambda p: p.name)
def test_no_secret_is_echoed(workflow):
    # A secret reaches echo/printf only as the sudo password piped into the
    # connection's stdin, never to the log, the summary or the step outputs.
    for step in _steps(workflow):
        names = _secret_vars(step)
        lines = step.get("run", "").splitlines()
        for i, line in enumerate(lines):
            if not ECHO.search(line) or "cat >" in line:
                continue
            used = [v for v in names if re.search(rf"\$\{{?{v}\b", line)]
            if not used:
                continue
            nxt = lines[i + 1] if i + 1 < len(lines) else ""
            piped = line.rstrip().endswith("\\") and nxt.lstrip().startswith("|") \
                or "| bash deploy/janus-ssh.sh run" in line
            assert used == ["SSHPASS"] and line.strip().startswith("printf '%s\\n' \"$SSHPASS\"") \
                and piped, f"{workflow.name} / {step['name']}: {line.strip()}"
            assert "GITHUB_" not in line


def test_helper_prints_no_secret():
    # In the helper, every echo/printf of a secret-bearing variable writes to a file.
    secret = re.compile(r"\$\{?(SSHPASS|JANUS_SSHPASS|USERNAME|GATEWAY_HOST|HOST|GATEWAY_PORT|"
                        r"MAIN_SERVER_LAN|PORT|KNOWN|KNOWN_GATEWAY|gw_host|port|GW_\w+)\b")
    for path in (HELPER, BACKUP):
        for line in path.read_text().splitlines():
            if ECHO.search(line) and secret.search(line) and not line.lstrip().startswith("#"):
                assert re.search(r'> "\$(GW_ENV|KH_GW|KH_JANUS|KH_BACKUP)"', line) \
                    or "| awk" in line or "::add-mask::" in line \
                    or line.strip().startswith("printf '%s\\n' \"$SSHPASS\" | bash"), \
                    f"{path.name}: {line.strip()}"


def test_backup_janus_leg_uses_the_helper():
    text = BACKUP.read_text()
    on_janus = text[text.index("on_janus() {"):text.index("on_backup() {")]
    assert 'bash "$JANUS_SSH" run' in on_janus and "sshpass" not in on_janus
    # The runner -> backup server leg and janus's own route are unchanged.
    on_backup = text[text.index("on_backup() {"):text.index("install() {")]
    assert '-p "$SFTP_PORT"' in on_backup and '"${USERNAME}@${HOST}"' in on_backup
    assert 'routes+=(--route "$HOST:$SFTP_PORT")' in text


# --- the helper, with stubs ----------------------------------------------------------

STUB = r"""#!/bin/bash
# Record argv and whether SSHPASS/JANUS_SSHPASS were set (never their value).
printf '%s|pass=%s|jpass=%s|%s\n' "$(basename "$0")" "${SSHPASS:+set}" \
  "${JANUS_SSHPASS:+set}" "$*" >> "$STUB_LOG"
case "$(basename "$0")" in
  ssh-keyscan) [ -n "${STUB_NO_GW_KEY:-}" ] || echo "|1|aaa=|bbb= ssh-ed25519 AAAAgateway" ;;
  ssh-keygen) echo "256 SHA256:stub host (ED25519)" ;;
  sshpass) shift; exec "$@" ;;
  ssh)
    # A gateway hop that outlives the session, holding whatever stderr it inherited.
    if [ -n "${STUB_LINGER:-}" ] && [[ " $* " == *" -W "* ]]; then
      echo "gateway hop noise" >&2
      sleep "$STUB_LINGER" </dev/null >/dev/null & echo $! > "$STUB_LOG.linger"
    fi
    for a in "$@"; do case "$a" in
      UserKnownHostsFile=*known_hosts_janus) kh=${a#UserKnownHostsFile=} ;;
      StrictHostKeyChecking=accept-new) accept=1 ;;
    esac; done
    # The host-key-only probe records janus's key; logins succeed unless told not to.
    if [ -n "${accept:-}" ] && [ -z "${STUB_NO_JANUS_KEY:-}" ]; then
      kh=$(sed -n 's/^  UserKnownHostsFile //p' "$JANUS_SSH_DIR/janus.conf")
      echo "janus ssh-ed25519 AAAAjanus" >> "$kh"
      exit 255
    fi
    exit "${STUB_SSH_RC:-0}" ;;
esac
"""

SECRETS = {"HOST": "gw.secret.example", "GATEWAY_PORT": "40022", "MAIN_SERVER_LAN": "192.0.2.77",
           "PORT": "", "USERNAME": "deployer", "SSHPASS": "s3cret-pass-value"}


@pytest.fixture
def stubbed(tmp_path):
    bin_ = tmp_path / "bin"
    bin_.mkdir()
    for name in ("ssh", "sshpass", "ssh-keyscan", "ssh-keygen"):
        (bin_ / name).write_text(STUB)
        (bin_ / name).chmod(0o755)

    def run(*args, **env):
        full = {"PATH": f"{bin_}:/usr/bin:/bin", "HOME": str(tmp_path),
                "JANUS_SSH_DIR": str(tmp_path / "ssh"), "STUB_LOG": str(tmp_path / "log"),
                "GITHUB_STEP_SUMMARY": str(tmp_path / "summary"), **SECRETS, **env}
        done = subprocess.run(["bash", str(HELPER), *args], env=full, capture_output=True,
                              text=True, timeout=30)
        log = (tmp_path / "log").read_text() if (tmp_path / "log").exists() else ""
        return done, log
    run.dir = tmp_path / "ssh"
    return run


def test_trust_writes_a_strict_jump(stubbed):
    done, log = stubbed("trust")
    assert done.returncode == 0, done.stdout + done.stderr
    conf = (stubbed.dir / "janus.conf").read_text()
    assert "HostName 192.0.2.77" in conf and "Port 22\n" in conf
    assert "HostKeyAlias janus" in conf and "StrictHostKeyChecking yes" in conf
    assert re.search(
        r'ProxyCommand bash ".*/deploy/janus-ssh.sh" proxy ".*janus-gateway.env" %h %p', conf)
    gw_env = (stubbed.dir / "janus-gateway.env").read_text()
    assert "GW_HOST=gw.secret.example" in gw_env and "GW_PORT=40022" in gw_env
    assert (stubbed.dir / "known_hosts_janus").read_text() == "janus ssh-ed25519 AAAAjanus\n"
    assert "ssh-keyscan|" in log and "-p 40022 -H gw.secret.example" in log
    # The gateway login is checked strictly against the gateway's own known_hosts.
    gw_login = next(ln for ln in log.splitlines() if ln.startswith("ssh|")
                    and "deployer@gw.secret.example true" in ln)
    assert "StrictHostKeyChecking=yes" in gw_login and "known_hosts_gateway" in gw_login
    # The final check logs in through the config (proxy and all) with the password.
    assert any(ln.startswith("sshpass|pass=set|jpass=set|-e ssh -F") and ln.endswith("janus true")
               for ln in log.splitlines())
    assert SECRETS["SSHPASS"] not in log  # never on a command line
    for value in SECRETS.values():
        if value:
            assert value not in done.stdout + done.stderr
    assert "both hops verified" in done.stdout


def test_gateway_host_overrides_ssh_host(stubbed):
    done, log = stubbed("trust", GATEWAY_HOST="gateway.other.example")
    assert done.returncode == 0, done.stderr
    assert "GW_HOST=gateway.other.example" in (stubbed.dir / "janus-gateway.env").read_text()
    assert "gw.secret.example" not in log


def test_known_hosts_secret_is_refiled_under_the_alias(stubbed):
    known = ("# a comment\n[janus.example]:2222 ssh-ed25519 AAAAone\n"
             "|1|salt=|hash= ecdsa-sha2-nistp256 AAAAtwo\n@cert-authority * ssh-rsa AAAAca\n")
    done, log = stubbed("trust", KNOWN=known, KNOWN_GATEWAY="[gw]:1 ssh-ed25519 AAAAgw")
    assert done.returncode == 0, done.stderr
    assert (stubbed.dir / "known_hosts_janus").read_text() == \
        "janus ssh-ed25519 AAAAone\njanus ecdsa-sha2-nistp256 AAAAtwo\n"
    assert (stubbed.dir / "known_hosts_gateway").read_text() == "[gw]:1 ssh-ed25519 AAAAgw\n"
    assert "ssh-keyscan" not in log and "accept-new" not in log


@pytest.mark.parametrize("env,message", [
    ({"GATEWAY_PORT": ""}, "gateway hop: secret GATEWAY_PORT is not set"),
    ({"GATEWAY_PORT": "22;id"}, "gateway hop: secret GATEWAY_PORT is not set, or not a port"),
    ({"MAIN_SERVER_LAN": ""}, "main-server hop: secret MAIN_SERVER_LAN is not set"),
    ({"MAIN_SERVER_LAN": "10.0.0.1\n  ProxyCommand x"}, "main-server hop: secret MAIN_SERVER_LAN"),
    ({"HOST": ""}, "gateway hop: neither GATEWAY_HOST nor SSH_HOST is set"),
    ({"PORT": "x"}, "main-server hop: secret SSH_PORT is not a port number"),
    ({"STUB_NO_GW_KEY": "1"}, "gateway hop: no host key from the gateway"),
    ({"STUB_SSH_RC": "255"}, "gateway hop: could not log in to the gateway"),
    ({"STUB_NO_JANUS_KEY": "1"}, "main-server hop: no host key from janus"),
    ({"KNOWN": "# only a comment"}, "main-server hop: SSH_KNOWN_HOSTS is set but holds no"),
])
def test_trust_fails_naming_the_hop(stubbed, env, message):
    done, _ = stubbed("trust", **env)
    assert done.returncode != 0
    assert message in done.stderr, done.stderr
    for value in SECRETS.values():
        if value:
            assert value not in done.stdout + done.stderr


def test_run_needs_trust_and_passes_stdin(stubbed):
    done, _ = stubbed("run", "true")
    assert done.returncode != 0 and "run 'janus-ssh.sh trust' first" in done.stderr
    assert stubbed("trust")[0].returncode == 0
    done, log = stubbed("run", "sudo -S -p '' bash -c 'echo eA== | base64 -d | bash'")
    assert done.returncode == 0
    last = log.strip().splitlines()[-2]   # sshpass, then the ssh it runs
    assert last.startswith("sshpass|pass=set|jpass=set|-e ssh -F ")
    assert last.endswith("janus sudo -S -p '' bash -c 'echo eA== | base64 -d | bash'")


def test_proxy_runs_its_own_sshpass_for_the_gateway(stubbed):
    assert stubbed("trust")[0].returncode == 0
    done, log = stubbed("proxy", str(stubbed.dir / "janus-gateway.env"), "192.0.2.77", "22",
                        SSHPASS="", JANUS_SSHPASS="s3cret-pass-value")
    assert done.returncode == 0, done.stderr
    lines = log.strip().splitlines()
    assert lines[-2].startswith("sshpass|pass=set|")
    assert "-e ssh -q -F none" in lines[-2]
    assert "StrictHostKeyChecking=yes" in lines[-1] and "known_hosts_gateway" in lines[-1]
    assert lines[-1].endswith("-p 40022 -W 192.0.2.77:22 deployer@gw.secret.example")


def test_a_lingering_gateway_hop_does_not_hold_the_output(stubbed, tmp_path):
    # ssh SIGHUPs its ProxyCommand and exits without waiting, so the gateway hop can
    # outlive a finished remote command. It must not hold the session's stderr: a caller
    # reading the output to EOF would hang after the command returned (#352/#353).
    assert stubbed("trust")[0].returncode == 0
    t0 = time.monotonic()
    try:
        done, _ = stubbed("proxy", str(stubbed.dir / "janus-gateway.env"), "192.0.2.77", "22",
                          STUB_LINGER="60")
    finally:
        linger = tmp_path / "log.linger"
        if linger.exists():
            subprocess.run(["kill", linger.read_text().strip()], check=False)
    assert done.returncode == 0, done.stderr
    assert time.monotonic() - t0 < 20
    assert "gateway hop noise" not in done.stderr
