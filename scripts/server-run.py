#!/usr/bin/env python3
"""Run a command on the SegQueue server, reading credentials from .secrets/server.env.

    python scripts/server-run.py 'docker ps --format "{{.Names}}\\t{{.Status}}"'
    python scripts/server-run.py --sudo 'docker logs --tail 80 girder'
    python scripts/server-run.py --script deploy.sh --sudo

Exists because the deploy account needs a password for both ssh and sudo, and
every way of supplying one from a shell on Windows puts it in `argv`, where any
other process on the machine can read it. paramiko takes it as a string, and
sudo gets it on the child's stdin.

**Nothing here prints a secret.** The password is never echoed, never logged, and
never passed as an argument -- not to ssh, not to sudo. If you see one in this
script's output, that is a bug worth reporting.

Credentials come from `.secrets/server.env`, which `.gitignore` excludes; see
`.secrets/server.env.example`.
"""

import argparse
import pathlib
import shlex
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
ENV_FILE = REPO / ".secrets" / "server.env"


def load_env(path=ENV_FILE):
    """Parse the KEY=value file. Values are taken literally, quotes stripped."""
    if not path.exists():
        raise SystemExit(
            f"{path} does not exist.\n\n"
            f"  cp {path.parent.name}/server.env.example {path.parent.name}/server.env\n"
            "then fill it in. It is gitignored.")
    env = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def connect(env):
    try:
        import paramiko
    except ImportError:
        raise SystemExit("paramiko is not installed:  pip install paramiko") from None

    host = env.get("SSH_HOST")
    user = env.get("SSH_USERNAME")
    if not host or not user:
        raise SystemExit("SSH_HOST and SSH_USERNAME must be set in .secrets/server.env")

    client = paramiko.SSHClient()
    client.load_system_host_keys()
    # Record an unknown host key rather than refuse, because this is a first
    # contact with a machine whose key we have no other way to learn -- but
    # AutoAddPolicy means the *first* connection is trusted blindly. If you have
    # the fingerprint from the console, check it against the one printed below.
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    key_path = env.get("SSH_KEY_PATH") or None
    client.connect(
        hostname=host,
        port=int(env.get("SSH_PORT") or 22),
        username=user,
        password=(env.get("SSH_PASSWORD") or None) if not key_path else None,
        key_filename=key_path,
        look_for_keys=bool(key_path),
        allow_agent=bool(key_path),
        timeout=30,
    )
    transport = client.get_transport()
    key = transport.get_remote_server_key()
    print(f"# connected to {user}@{host} "
          f"({key.get_name()} {key.get_fingerprint().hex()[:16]}...)", file=sys.stderr)
    return client


def run(client, command, env, use_sudo=False, timeout=600):
    """Run one command, streaming its output. Returns the exit status."""
    if use_sudo:
        # `-S` reads the password from stdin and `-p ''` suppresses the prompt,
        # so the password never appears in the command line or the output.
        command = "sudo -S -p '' bash -c " + shlex.quote(command)

    stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
    if use_sudo:
        secret = env.get("SUDO_PASSWORD") or env.get("SSH_PASSWORD") or ""
        if secret:
            stdin.write(secret + "\n")
            stdin.flush()
    stdin.channel.shutdown_write()

    out = stdout.read().decode("utf-8", "replace")
    err = stderr.read().decode("utf-8", "replace")
    status = stdout.channel.recv_exit_status()
    if out:
        sys.stdout.write(out if out.endswith("\n") else out + "\n")
    if err.strip():
        sys.stderr.write(err if err.endswith("\n") else err + "\n")
    return status


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", nargs="?", help="Shell command to run.")
    parser.add_argument("--script", help="Run this local file as a shell script instead.")
    parser.add_argument("--sudo", action="store_true", help="Run it as root.")
    parser.add_argument("--timeout", type=int, default=600)
    args = parser.parse_args(argv)

    if not args.command and not args.script:
        parser.error("give a command, or --script FILE")

    env = load_env()
    command = args.command
    if args.script:
        body = pathlib.Path(args.script).read_text(encoding="utf-8")
        # Through base64 so quoting in the script cannot be mangled on the way.
        import base64
        encoded = base64.b64encode(body.encode()).decode()
        command = f"echo {encoded} | base64 -d | bash"

    try:
        client = connect(env)
    except SystemExit:
        raise
    except Exception as exc:
        # A bad host or a refused password should read as one line, not as a
        # paramiko traceback: the fix is always in server.env either way.
        raise SystemExit(
            f"Could not connect to {env.get('SSH_USERNAME')}@{env.get('SSH_HOST')}:"
            f"{env.get('SSH_PORT') or 22} -- {type(exc).__name__}: {exc}" \
            "\nCheck .secrets/server.env.") from None
    try:
        return run(client, command, env, use_sudo=args.sudo, timeout=args.timeout)
    finally:
        client.close()


if __name__ == "__main__":
    sys.exit(main())
