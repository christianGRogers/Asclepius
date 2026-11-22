"""Janus through the gateway, end to end, with two real sshd (deploy/janus-ssh.sh).

Two network namespaces stand in for the two servers: ``gw`` (the gateway, reachable
from the runner) and ``lan`` (janus, reachable only from ``gw``; ``gw`` does not route).
Both sshd take password logins for one test user who has password ``sudo``. The
workflows' own step scripts are run from their YAML, as Actions would, and must:

* log in through both hops with the password through sshpass, both host keys pinned;
* get the sudo password to ``sudo -S`` on janus through stdin, and run the base64
  script as root (the deploy step, the server-ssh helper, the backup step's janus leg);
* refuse, naming the hop, when either pinned key is wrong;
* print none of the secret values.

Needs root, ``ip``, ``sshd``, ``sshpass`` and ``sudo``; runs only with
``JANUS_SSH_E2E=1`` (the CI job ``janus-ssh`` sets it).
"""

import os
import secrets
import shutil
import subprocess
import time
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
SQ14 = ROOT / ".github/workflows/segqueue14-janus.yml"
SERVER_SSH = ROOT / ".github/workflows/server-ssh.yml"
SSHD = shutil.which("sshd") or "/usr/sbin/sshd"

pytestmark = pytest.mark.skipif(
    os.environ.get("JANUS_SSH_E2E") != "1" or os.geteuid() != 0
    or not all(shutil.which(t) for t in ("ip", "sshpass", "ssh", "sudo", "useradd"))
    or not os.path.exists(SSHD),
    reason="needs JANUS_SSH_E2E=1, root, ip, sshd, sshpass and sudo")

USER = "sq14jump"
GW_PUBLIC, GW_LAN, JANUS_LAN = "10.231.0.2", "10.231.1.1", "10.231.1.2"
GW_PORT = "2201"


def _sh(*cmd, check=True, **kw):
    return subprocess.run(cmd, check=check, capture_output=True, text=True, **kw)


def _step(workflow, name):
    wf = yaml.safe_load(workflow.read_text())
    job = next(iter(wf["jobs"].values()))
    return next(s for s in job["steps"] if s.get("name", "").startswith(name))["run"]


def _wait_port(ns, host, port):
    for _ in range(50):
        if _sh("ip", "netns", "exec", ns, "bash", "-c",
               f"exec 3<>/dev/tcp/{host}/{port}", check=False).returncode == 0:
            return
        time.sleep(0.2)
    raise RuntimeError(f"sshd in {ns} did not come up")


@pytest.fixture(scope="module")
def servers(tmp_path_factory):
    base = tmp_path_factory.mktemp("jump")
    password = "pw-" + secrets.token_hex(12)
    procs = []
    _sh("useradd", "-m", "-s", "/bin/bash", USER, check=False)
    _sh("chpasswd", input=f"{USER}:{password}\n")
    sudoers = Path(f"/etc/sudoers.d/{USER}")
    sudoers.write_text(f"{USER} ALL=(ALL) ALL\n")
    sudoers.chmod(0o440)
    home = Path(_sh("getent", "passwd", USER).stdout.split(":")[5])
    stub = home / "Asclepius-sq14/deploy/segqueue14-deploy.sh"
    stub.parent.mkdir(parents=True, exist_ok=True)
    # Stands in for the deploy script: who runs it, and with what.
    stub.write_text('echo "STUB uid=$(id -u) user=$SQ14_USER args=$*"\n')
    Path("/run/sshd").mkdir(exist_ok=True)

    for ns in ("gw", "lan"):
        _sh("ip", "netns", "del", ns, check=False)
        _sh("ip", "netns", "add", ns)
        _sh("ip", "netns", "exec", ns, "ip", "link", "set", "lo", "up")
    _sh("ip", "link", "del", "sqj-h", check=False)
    _sh("ip", "link", "add", "sqj-h", "type", "veth", "peer", "name", "sqj-g0")
    _sh("ip", "link", "set", "sqj-g0", "netns", "gw")
    _sh("ip", "addr", "add", "10.231.0.1/30", "dev", "sqj-h")
    _sh("ip", "link", "set", "sqj-h", "up")
    _sh("ip", "netns", "exec", "gw", "ip", "addr", "add", f"{GW_PUBLIC}/30", "dev", "sqj-g0")
    _sh("ip", "netns", "exec", "gw", "ip", "link", "set", "sqj-g0", "up")
    _sh("ip", "netns", "exec", "gw", "ip", "link", "add", "sqj-g1", "type", "veth",
        "peer", "name", "sqj-l")
    _sh("ip", "netns", "exec", "gw", "ip", "link", "set", "sqj-l", "netns", "lan")
    _sh("ip", "netns", "exec", "gw", "ip", "addr", "add", f"{GW_LAN}/30", "dev", "sqj-g1")
    _sh("ip", "netns", "exec", "gw", "ip", "link", "set", "sqj-g1", "up")
    _sh("ip", "netns", "exec", "lan", "ip", "addr", "add", f"{JANUS_LAN}/30", "dev", "sqj-l")
    _sh("ip", "netns", "exec", "lan", "ip", "link", "set", "sqj-l", "up")
    _sh("ip", "netns", "exec", "gw", "sysctl", "-qw", "net.ipv4.ip_forward=0")

    keys = {}
    for ns, listen in (("gw", f"{GW_PUBLIC}:{GW_PORT}"), ("lan", f"{JANUS_LAN}:22")):
        d = base / ns
        d.mkdir()
        _sh("ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(d / "hostkey"))
        keys[ns] = (d / "hostkey.pub").read_text().split()[:2]
        (d / "sshd_config").write_text(
            f"ListenAddress {listen}\nHostKey {d}/hostkey\nPidFile {d}/sshd.pid\n"
            "PasswordAuthentication yes\nKbdInteractiveAuthentication no\n"
            "PubkeyAuthentication no\nUsePAM no\nPermitRootLogin no\n"
            f"AllowUsers {USER}\nAllowTcpForwarding yes\nStrictModes no\n")
        procs.append(subprocess.Popen(
            ["ip", "netns", "exec", ns, SSHD, "-D", "-e", "-f", str(d / "sshd_config")],
            stdout=open(d / "log", "w"), stderr=subprocess.STDOUT))
    _wait_port("gw", GW_PUBLIC, GW_PORT)
    _wait_port("lan", JANUS_LAN, 22)

    yield {"password": password, "keys": keys, "base": base}

    for p in procs:
        p.terminate()
    for ns in ("gw", "lan"):
        _sh("ip", "netns", "del", ns, check=False)
    _sh("ip", "link", "del", "sqj-h", check=False)
    sudoers.unlink(missing_ok=True)
    _sh("userdel", "-r", USER, check=False)


def _env(servers, tmp_path, **extra):
    home = tmp_path / "home"
    home.mkdir(exist_ok=True)
    env = {
        "PATH": os.environ["PATH"], "HOME": str(home), "RUNNER_TEMP": str(tmp_path),
        "GITHUB_WORKSPACE": str(ROOT),
        "GITHUB_STEP_SUMMARY": str(tmp_path / "summary"),
        "GITHUB_OUTPUT": str(tmp_path / "output"),
        "GATEWAY_HOST": "", "HOST": GW_PUBLIC, "GATEWAY_PORT": GW_PORT,
        "MAIN_SERVER_LAN": JANUS_LAN, "PORT": "", "USERNAME": USER,
        "SSHPASS": servers["password"], "KNOWN": "", "KNOWN_GATEWAY": "",
    }
    env.update(extra)
    return env


def _run(script, env, stdin=None):
    return subprocess.run(["bash", "-e", "-c", script], cwd=ROOT, env=env, input=stdin,
                          capture_output=True, text=True, timeout=120)


def _no_secret(servers, tmp_path, *outputs):
    summary = tmp_path / "summary"
    text = "".join(outputs) + (summary.read_text() if summary.exists() else "")
    for value in (servers["password"], JANUS_LAN, GW_PUBLIC):
        assert value not in text, f"a secret value was printed:\n{text}"


def test_janus_is_not_reachable_directly(servers):
    # The premise: only the gateway reaches janus's address.
    r = _sh("ssh-keyscan", "-T", "3", JANUS_LAN, check=False)
    assert not r.stdout.strip()


def test_deploy_step_through_the_gateway(servers, tmp_path):
    env = _env(servers, tmp_path)
    trust = _run(_step(SQ14, "Trust the host keys"), env)
    assert trust.returncode == 0, trust.stdout + trust.stderr
    assert "both hops verified" in trust.stdout
    # Janus's key, pinned under the alias, is the lan sshd's own.
    pinned = (Path(env["HOME"]) / ".ssh/known_hosts_janus").read_text().split()
    assert pinned == ["janus", *servers["keys"]["lan"]]

    run = _run(_step(SQ14, "Run the step on janus"), {**env, "CMD": "status"})
    assert run.returncode == 0, run.stdout + run.stderr
    # sudo -S got the password through stdin; the script ran as root for the user.
    assert f"STUB uid=0 user={USER} args=status" in run.stdout
    _no_secret(servers, tmp_path, trust.stdout, trust.stderr, run.stdout, run.stderr)


def test_backup_step_janus_leg(servers, tmp_path):
    env = _env(servers, tmp_path)
    assert _run(_step(SQ14, "Trust the host keys"), env).returncode == 0
    run = _run(_step(SQ14, "Run the backup step"),
               {**env, "CMD": "backup-status", "SFTP_PORT": "1", "SFTP_KNOWN_HOSTS": "",
                "LAN_ADDRESS": ""})
    assert run.returncode == 0, run.stdout + run.stderr
    assert f"STUB uid=0 user={USER} args=backup-status" in run.stdout


def test_server_ssh_helpers(servers, tmp_path):
    env = _env(servers, tmp_path)
    trust = _run(_step(SERVER_SSH, "Trust the host keys"), env)
    assert trust.returncode == 0, trust.stdout + trust.stderr
    assert _run(_step(SERVER_SSH, "Write the ssh helper"), env).returncode == 0
    root = subprocess.run([str(tmp_path / "remote-root")], input="echo ROOT=$(id -u)\n",
                          env=env, capture_output=True, text=True, timeout=60)
    assert root.returncode == 0, root.stderr
    assert root.stdout.strip().endswith("ROOT=0")
    plain = subprocess.run([str(tmp_path / "remote"), "id -un"], env=env,
                           capture_output=True, text=True, timeout=60)
    assert plain.stdout.strip() == USER
    _no_secret(servers, tmp_path, trust.stdout, trust.stderr, root.stdout, root.stderr)


def test_pinned_keys_from_the_secrets(servers, tmp_path):
    # SSH_KNOWN_HOSTS as it was: janus's keys under its old public name and port.
    known = f"[janus.example]:2222 {' '.join(servers['keys']['lan'])}"
    known_gw = f"[{GW_PUBLIC}]:{GW_PORT} {' '.join(servers['keys']['gw'])}"
    env = _env(servers, tmp_path, KNOWN=known, KNOWN_GATEWAY=known_gw)
    trust = _run(_step(SQ14, "Trust the host keys"), env)
    assert trust.returncode == 0, trust.stdout + trust.stderr
    assert "pinned from SSH_KNOWN_HOSTS_GATEWAY" in trust.stdout
    assert "pinned from SSH_KNOWN_HOSTS" in trust.stdout
    summary = tmp_path / "summary"
    assert not summary.exists() or "warning" not in summary.read_text()


def _other_key(tmp_path):
    _sh("ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(tmp_path / "other"))
    return (tmp_path / "other.pub").read_text().split()[:2]


def test_wrong_janus_key_names_the_main_hop(servers, tmp_path):
    env = _env(servers, tmp_path, KNOWN="janus " + " ".join(_other_key(tmp_path)))
    trust = _run(_step(SQ14, "Trust the host keys"), env)
    assert trust.returncode != 0
    assert "main-server hop: could not log in" in trust.stderr
    _no_secret(servers, tmp_path, trust.stdout, trust.stderr)


def test_wrong_gateway_key_names_the_gateway_hop(servers, tmp_path):
    bad = f"[{GW_PUBLIC}]:{GW_PORT} " + " ".join(_other_key(tmp_path))
    env = _env(servers, tmp_path, KNOWN_GATEWAY=bad)
    trust = _run(_step(SQ14, "Trust the host keys"), env)
    assert trust.returncode != 0
    assert "gateway hop: could not log in" in trust.stderr


def test_wrong_password_names_the_gateway_hop(servers, tmp_path):
    env = _env(servers, tmp_path, SSHPASS="not-the-password")
    trust = _run(_step(SQ14, "Trust the host keys"), env)
    assert trust.returncode != 0
    assert "gateway hop: could not log in" in trust.stderr
    assert "password was refused" in trust.stderr


def test_nothing_on_the_lan_address_names_the_main_hop(servers, tmp_path):
    env = _env(servers, tmp_path, PORT="2299")
    trust = _run(_step(SQ14, "Trust the host keys"), env)
    assert trust.returncode != 0
    assert "main-server hop: no host key" in trust.stderr
