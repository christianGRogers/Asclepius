#!/bin/bash
# Hourly backup of janus to the lead's backup server (D42, issue #283): the Girder
# database and every submission / revision file, into a restic repository over SFTP.
# CT volumes are not backed up (they are kept elsewhere); see segqueue_backup.py.
#
# Run by systemd (deploy/systemd/segqueue-backup*.{service,timer}), as root:
#   segqueue-backup.sh run            hourly: dump, back up, forget (skips if one is running)
#   segqueue-backup.sh check          daily: prune, restic check on a 1% sample
# Run from the "SegQueue14 on janus" workflow, through segqueue14-deploy.sh:
#   segqueue-backup.sh status         read-only: newest snapshot's age and size; fails if > 2 h
#   segqueue-backup.sh restore-test   restores the newest snapshot into a scratch folder and a
#                                     scratch Mongo (port 27199), checks every submission's file
#                                     and checksum, deletes the scratch copy. Live data untouched.
#   segqueue-backup.sh install-prepare   restic, the SSH key, the password from the workflow
#   segqueue-backup.sh install-finish --user U --route HOST:PORT [--route ...] --hostkeys-b64 B64
#                                     pick the route that works, pin the host key, init/open
#                                     the repository, install and start the timers, first backup
#   segqueue-backup.sh off            stop and disable the timers; keeps the repository, key,
#                                     password and every snapshot
#
# Never touches Girder or Mongo beyond reading them: no restart, no lock, no write.
# Never prints the repository password. Settings: /etc/segqueue-backup/backup.env (written
# by install-finish), then backup.local.env for overrides the install leaves alone.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONF_DIR="${BACKUP_CONF_DIR:-/etc/segqueue-backup}"
BACKUP_ENV="${BACKUP_ENV:-$CONF_DIR/backup.env}"
# shellcheck disable=SC1090
[ -r "$BACKUP_ENV" ] && . "$BACKUP_ENV"
# shellcheck disable=SC1090
[ -r "$CONF_DIR/backup.local.env" ] && . "$CONF_DIR/backup.local.env"

: "${BACKUP_STATE:=/var/lib/segqueue-backup}"
: "${BACKUP_LIB:=$HERE}"
: "${BACKUP_PYTHON:=python3}"
: "${GIRDER_MONGO_URI:=mongodb://127.0.0.1:27017/girder}"
: "${BACKUP_TAG:=segqueue14}"
: "${BACKUP_MIN_FREE_MB:=5120}"           # refuse to start below this much free disk
: "${BACKUP_GUARD_PATHS:=$BACKUP_STATE}"  # whose disks the floor applies to
: "${BACKUP_LIMIT_UPLOAD_KIB:=20480}"     # restic's bandwidth caps, KiB/s
: "${BACKUP_LIMIT_DOWNLOAD_KIB:=20480}"
: "${BACKUP_MAX_EXTRA_MB:=50}"            # largest seed/prelabel/reference file included
: "${BACKUP_MAX_AGE_HOURS:=2}"
: "${BACKUP_KEEP:=--keep-hourly 48 --keep-daily 14 --keep-weekly 8 --keep-monthly 12}"
: "${BACKUP_SCRATCH_PORT:=27199}"
: "${BACKUP_MONGOD:=}"                    # mongod for the restore drill's scratch database
: "${BACKUP_SCRATCH_MONGO:=}"             # or an existing scratch server (tests)
: "${BACKUP_SFTP_COMMAND:=}"
: "${RESTIC_BIN:=restic}"
: "${RESTIC_PASSWORD_FILE:=$CONF_DIR/restic-password}"
export GIRDER_MONGO_URI RESTIC_PASSWORD_FILE
[ -n "${RESTIC_REPOSITORY:-}" ] && export RESTIC_REPOSITORY
[ -n "${RESTIC_CACHE_DIR:-}" ] && export RESTIC_CACHE_DIR && mkdir -p "$RESTIC_CACHE_DIR" 2>/dev/null

DUMP="$BACKUP_STATE/dump"
LOCK="$BACKUP_STATE/run.lock"
UNITS=(segqueue-backup.service segqueue-backup.timer segqueue-backup-check.service
       segqueue-backup-check.timer)
LIB_DEST="${BACKUP_LIB_DEST:-/usr/local/lib/segqueue-backup}"
RESTIC_PIN_VERSION=0.17.3
declare -A RESTIC_PIN_SHA256=(
    [amd64]=5097faeda6aa13167aae6e36efdba636637f8741fed89bbf015678334632d4d3
    [arm64]=db27b803534d301cef30577468cf61cb2e242165b8cd6d8cd6efd7001be2e557
)

say() { printf '[backup] %s\n' "$*"; }
die() { printf '[backup] ERROR: %s\n' "$*" >&2; exit 1; }
py() { "$BACKUP_PYTHON" "$BACKUP_LIB/segqueue_backup.py" "$@"; }

restic_() {
    local args=(--limit-upload "$BACKUP_LIMIT_UPLOAD_KIB" --limit-download "$BACKUP_LIMIT_DOWNLOAD_KIB")
    [ -n "$BACKUP_SFTP_COMMAND" ] && args+=(-o "sftp.command=$BACKUP_SFTP_COMMAND")
    "$RESTIC_BIN" "${args[@]}" "$@"
}

need_repo() {
    [ -n "${RESTIC_REPOSITORY:-}" ] || die "no RESTIC_REPOSITORY: not installed? (run the backup-install step)"
    [ -r "$RESTIC_PASSWORD_FILE" ] || die "no readable password file $RESTIC_PASSWORD_FILE"
}

# One job at a time. `run` skips if another holds the lock; the others wait a while.
take_lock() {   # take_lock <wait seconds, 0 = do not wait>
    mkdir -p "$BACKUP_STATE" && chmod 700 "$BACKUP_STATE"
    exec 9>"$LOCK"
    if [ "$1" = 0 ]; then
        flock -n 9 && return 0
        say "skipped: another backup job is still running (lock $LOCK)"
        exit 0
    fi
    flock -w "$1" 9 || die "another backup job held the lock for $1 s; try again later"
}

guard() {
    # shellcheck disable=SC2086
    py guard --min-free-mb "$BACKUP_MIN_FREE_MB" $BACKUP_GUARD_PATHS
}

latest_id() {
    restic_ --no-lock snapshots --tag "$BACKUP_TAG" --latest 1 --json 2>/dev/null \
        | "$BACKUP_PYTHON" -c 'import json,sys; s=json.load(sys.stdin) or []; print(s[-1]["id"] if s else "")' \
        2>/dev/null || true
}

# ------------------------------------------------------------------ the hourly run

cmd_run() {
    take_lock 0
    need_repo
    guard || exit $?
    say "$(date -Is) dumping the database (read-only) and listing the files to back up"
    py dump --out "$DUMP" --max-extra-mb "$BACKUP_MAX_EXTRA_MB"
    local dump_rc=$?
    [ "$dump_rc" = 0 ] || [ "$dump_rc" = 2 ] || die "dump failed (exit $dump_rc); nothing backed up"

    # The previous snapshot as parent, so unchanged files are recognised by their
    # metadata rather than read again (the file list grows every hour, and restic
    # only finds a parent by itself when the list is identical).
    local parent args=(--tag "$BACKUP_TAG" --files-from-verbatim "$DUMP/files.txt")
    parent=$(latest_id)
    [ -n "$parent" ] && args+=(--parent "$parent")
    say "$(date -Is) backing up to the repository${parent:+ (parent $parent)}"
    restic_ backup "${args[@]}" "$DUMP"
    local rc=$?
    if [ "$rc" = 3 ]; then
        say "WARNING: restic could not read some files; the snapshot was saved without them"
        dump_rc=2
    elif [ "$rc" != 0 ]; then
        die "restic backup failed (exit $rc); the local dump is kept at $DUMP"
    fi
    say "$(date -Is) forgetting snapshots beyond the retention ($BACKUP_KEEP; pruned daily)"
    # shellcheck disable=SC2086
    restic_ forget --tag "$BACKUP_TAG" $BACKUP_KEEP >/dev/null || say "WARNING: forget failed"
    cp "$DUMP/manifest.json" "$BACKUP_STATE/last-manifest.json" 2>/dev/null || true
    rm -rf "$DUMP"
    say "$(date -Is) done"
    exit "$dump_rc"
}

cmd_check() {
    take_lock 1800
    need_repo
    say "$(date -Is) pruning ($BACKUP_KEEP)"
    # shellcheck disable=SC2086
    restic_ forget --tag "$BACKUP_TAG" $BACKUP_KEEP --prune || die "prune failed"
    say "$(date -Is) checking the repository, reading a 1% sample of the data"
    restic_ check --read-data-subset=1% || die "restic check found a problem"
    say "$(date -Is) check passed"
}

# ------------------------------------------------------------------ status

cmd_status() {
    if command -v systemctl >/dev/null 2>&1; then
        say "timers:"
        systemctl list-timers --all --no-pager 'segqueue-backup*' 2>/dev/null | sed 's/^/    /' || true
        say "last hourly run: $(systemctl show segqueue-backup.service -p Result -p ExecMainStatus \
            -p ExecMainExitTimestamp --no-pager 2>/dev/null | tr '\n' ' ')"
    fi
    need_repo
    local snaps rc
    snaps=$(restic_ --no-lock snapshots --tag "$BACKUP_TAG" --json) \
        || die "could not list the snapshots (repository unreachable?)"
    say "snapshots: $(printf '%s' "$snaps" | "$BACKUP_PYTHON" -c 'import json,sys; print(len(json.load(sys.stdin) or []))')"
    printf '%s' "$snaps" | py age --max-hours "$BACKUP_MAX_AGE_HOURS"
    rc=$?
    say "newest snapshot's contents: $(restic_ --no-lock stats latest --tag "$BACKUP_TAG" --mode restore-size 2>/dev/null \
        | grep -E 'Total (File Count|Size)' | xargs)"
    say "repository on the backup server: $(restic_ --no-lock stats --mode raw-data 2>/dev/null \
        | grep -E 'Total Size' | xargs)"
    if [ -r "$BACKUP_STATE/last-manifest.json" ]; then
        "$BACKUP_PYTHON" - "$BACKUP_STATE/last-manifest.json" <<'PYEOF'
import json, sys
m = json.load(open(sys.argv[1]))
kinds = {}
for f in m['files']:
    kinds[f['kind']] = kinds.get(f['kind'], 0) + 1
print('[backup] last run: %s; %d documents; files %s; CT excluded %d; missing %d'
      % (m['created'], m['documents'], kinds, m['excludedCt'], len(m['missing'])))
PYEOF
    fi
    if command -v journalctl >/dev/null 2>&1; then
        say "last log lines:"
        journalctl -u segqueue-backup.service -n 12 --no-pager 2>/dev/null | sed 's/^/    /' || true
    fi
    [ "$rc" = 0 ] || die "the newest snapshot is older than $BACKUP_MAX_AGE_HOURS h (or there is none)"
}

# ------------------------------------------------------------------ the restore drill

SCRATCH_PID=""
cleanup_scratch() {
    if [ -n "$SCRATCH_PID" ]; then
        kill "$SCRATCH_PID" 2>/dev/null
        for _ in $(seq 1 30); do kill -0 "$SCRATCH_PID" 2>/dev/null || break; sleep 1; done
    fi
    rm -rf "$BACKUP_STATE/restore-test"
}

cmd_restore_test() {
    take_lock 600
    need_repo
    guard || exit $?
    local scratch="$BACKUP_STATE/restore-test" scratch_uri="$BACKUP_SCRATCH_MONGO"
    trap cleanup_scratch EXIT
    rm -rf "$scratch" && mkdir -p "$scratch/files"
    say "$(date -Is) restoring the newest snapshot into $scratch (live data untouched)"
    restic_ restore latest --tag "$BACKUP_TAG" --target "$scratch/files" >/dev/null \
        || die "restic restore failed"
    local dump_copy="$scratch/files${DUMP}"
    [ -f "$dump_copy/manifest.json" ] || die "the snapshot holds no dump at $DUMP"

    if [ -z "$scratch_uri" ] && [ -n "$BACKUP_MONGOD" ] && [ -x "$BACKUP_MONGOD" ]; then
        mkdir -p "$scratch/db"
        say "starting a scratch mongod on 127.0.0.1:$BACKUP_SCRATCH_PORT"
        "$BACKUP_MONGOD" --dbpath "$scratch/db" --bind_ip 127.0.0.1 --port "$BACKUP_SCRATCH_PORT" \
            --wiredTigerCacheSizeGB 0.25 --logpath "$scratch/mongod.log" >/dev/null 2>&1 &
        SCRATCH_PID=$!
        scratch_uri="mongodb://127.0.0.1:$BACKUP_SCRATCH_PORT"
        "$BACKUP_PYTHON" -c "
import sys, time
from pymongo import MongoClient
for _ in range(60):
    try:
        MongoClient(sys.argv[1], serverSelectionTimeoutMS=1000).admin.command('ping'); sys.exit(0)
    except Exception:
        time.sleep(1)
sys.exit(1)" "$scratch_uri" || die "the scratch mongod did not start (see $scratch/mongod.log)"
    fi
    py verify --dump "$dump_copy" --restored "$scratch/files" \
        ${scratch_uri:+--scratch-mongo "$scratch_uri"} --live-uri "$GIRDER_MONGO_URI"
    local rc=$?
    say "$(date -Is) scratch copy removed"
    exit "$rc"
}

# ------------------------------------------------------------------ install / off

need_root() { [ "$(id -u)" = 0 ] || die "run as root"; }

restic_ok() {   # a restic new enough for --files-from-verbatim and the exit codes used here
    local v
    v=$("$RESTIC_BIN" version 2>/dev/null | awk '{print $2}')
    [ -n "$v" ] && [ "$(printf '%s\n0.14.0\n' "$v" | sort -V | head -1)" = 0.14.0 ]
}

install_restic() {
    if restic_ok; then say "restic: $("$RESTIC_BIN" version)"; return 0; fi
    local arch
    case "$(uname -m)" in x86_64) arch=amd64 ;; aarch64) arch=arm64 ;; *) die "no pinned restic for $(uname -m)" ;; esac
    local url="https://github.com/restic/restic/releases/download/v${RESTIC_PIN_VERSION}/restic_${RESTIC_PIN_VERSION}_linux_${arch}.bz2"
    local tmp
    tmp=$(mktemp -d)
    say "installing restic $RESTIC_PIN_VERSION from the official release (checksum pinned)"
    curl -fsSL -o "$tmp/restic.bz2" "$url" || die "could not download $url"
    echo "${RESTIC_PIN_SHA256[$arch]}  $tmp/restic.bz2" | sha256sum -c --quiet - \
        || die "the restic download does not match its pinned checksum; not installed"
    bunzip2 "$tmp/restic.bz2" && install -m 755 "$tmp/restic" /usr/local/bin/restic
    rm -rf "$tmp"
    RESTIC_BIN=/usr/local/bin/restic
    restic_ok || die "restic still not usable"
    say "restic: $("$RESTIC_BIN" version)"
}

cmd_install_prepare() {
    need_root
    local user_home="${USER_HOME:-}"
    [ -n "$user_home" ] || die "USER_HOME is not set (run through segqueue14-deploy.sh)"
    install_restic
    install -d -m 700 "$CONF_DIR" "$BACKUP_STATE"
    if [ ! -f "$CONF_DIR/id_ed25519" ]; then
        ssh-keygen -q -t ed25519 -N '' -C "segqueue-backup@$(hostname -s)" -f "$CONF_DIR/id_ed25519" \
            || die "ssh-keygen failed"
        say "generated the backup SSH key $CONF_DIR/id_ed25519"
    else
        say "the backup SSH key exists: $CONF_DIR/id_ed25519"
    fi
    local transit="$user_home/.segqueue-backup-restic-password.new"
    if [ -s "$transit" ]; then
        install -m 600 -o root -g root "$transit" "$CONF_DIR/restic-password.new"
        rm -f "$transit"
        say "received the repository password (checked against the repository in the next step)"
    elif [ ! -s "$CONF_DIR/restic-password" ]; then
        die "no repository password: the BACKUP_RESTIC_PASSWORD secret did not arrive"
    fi
    rm -f "$transit"
    printf 'PUBKEY %s\n' "$(cat "$CONF_DIR/id_ed25519.pub")"
}

ssh_config() {   # ssh_config host port user known_hosts
    cat <<EOF
Host segqueue-backup-target
    HostName $1
    Port $2
    User $3
    IdentityFile $CONF_DIR/id_ed25519
    IdentitiesOnly yes
    UserKnownHostsFile $4
    StrictHostKeyChecking yes
    BatchMode yes
    ConnectTimeout 15
    ServerAliveInterval 30
    ServerAliveCountMax 4
EOF
}

# Try one route: the host key must match one the GitHub runner saw, then SFTP must log in.
try_route() {   # try_route host port user expected_known_hosts_file
    local host=$1 port=$2 user=$3 expected=$4 scan kh="$CONF_DIR/known_hosts.try" cfg="$CONF_DIR/ssh_config.try"
    scan=$(ssh-keyscan -T 10 -p "$port" "$host" 2>/dev/null | grep -v '^#')
    [ -n "$scan" ] || { say "route $host:$port: no answer"; return 1; }
    : > "$kh"
    while read -r _ type key; do
        [ -n "$key" ] || continue
        if awk -v t="$type" -v k="$key" '$2==t && $3==k {f=1} END {exit !f}' "$expected"; then
            if [ "$port" = 22 ]; then echo "$host $type $key"; else echo "[$host]:$port $type $key"; fi >> "$kh"
        fi
    done <<< "$scan"
    if [ ! -s "$kh" ]; then
        say "route $host:$port: answers, but with a host key the GitHub runner did not see -- not trusted"
        return 1
    fi
    ssh_config "$host" "$port" "$user" "$kh" > "$cfg"
    if echo 'pwd' | sftp -q -F "$cfg" -b - segqueue-backup-target >/dev/null 2>&1; then
        mv "$kh" "$CONF_DIR/known_hosts"
        ssh_config "$host" "$port" "$user" "$CONF_DIR/known_hosts" > "$CONF_DIR/ssh_config"
        rm -f "$cfg"
        say "route $host:$port: works (host key pinned, SFTP login with the backup key)"
        return 0
    fi
    say "route $host:$port: host key matches, but SFTP login with the backup key failed"
    rm -f "$kh" "$cfg"
    return 1
}

# Open the repository with a password file: 0 opens, 10 no repository, 12 wrong password.
probe_repo() {   # probe_repo password_file
    local out rc
    out=$(RESTIC_PASSWORD_FILE="$1" restic_ --no-lock cat config 2>&1 >/dev/null)
    rc=$?
    [ "$rc" = 0 ] && return 0
    if [ "$rc" = 10 ] || grep -qiE 'does not exist|Is there a repository' <<< "$out"; then return 10; fi
    if [ "$rc" = 12 ] || grep -qiE 'wrong password|no key found' <<< "$out"; then return 12; fi
    say "restic: $(tail -n 3 <<< "$out" | tr '\n' ' ')"
    return 1
}

cmd_install_finish() {
    need_root
    local user="" repo_path="segqueue-backup" hostkeys_b64="" routes=()
    while [ $# -gt 0 ]; do
        case "$1" in
            --user) user=$2; shift 2 ;;
            --route) routes+=("$2"); shift 2 ;;
            --hostkeys-b64) hostkeys_b64=$2; shift 2 ;;
            --repo-path) repo_path=$2; shift 2 ;;
            *) die "unknown option $1" ;;
        esac
    done
    [ -n "$user" ] && [ -n "$hostkeys_b64" ] && [ ${#routes[@]} -gt 0 ] \
        || die "usage: install-finish --user U --route HOST:PORT [...] --hostkeys-b64 B64"
    restic_ok || RESTIC_BIN=/usr/local/bin/restic
    restic_ok || die "no usable restic; run install-prepare"
    [ -f "$CONF_DIR/id_ed25519" ] || die "no backup SSH key; run install-prepare"
    local user_home="${USER_HOME:-}"

    local expected="$CONF_DIR/known_hosts.expected" chosen=""
    printf '%s' "$hostkeys_b64" | base64 -d > "$expected" || die "bad --hostkeys-b64"
    for route in "${routes[@]}"; do
        if try_route "${route%:*}" "${route##*:}" "$user" "$expected"; then chosen=$route; break; fi
    done
    rm -f "$expected"
    if [ -z "$chosen" ]; then
        say "janus could not reach the backup server by any route tried: ${routes[*]}"
        say "WHAT THE LEAD MUST PROVIDE: the backup server's address as seen FROM JANUS"
        say "  (its LAN IP or name, and the SSH/SFTP port on the LAN) in the GitHub secret"
        say "  BACKUP_SFTP_LAN_ADDRESS, as host:port; then run backup-install again."
        say "  If a route above said 'login failed', the backup server's sshd must allow"
        say "  public-key logins for that account."
        die "no working route to the backup server; nothing installed"
    fi
    say "using route $chosen"

    RESTIC_REPOSITORY="sftp:segqueue-backup-target:$repo_path"
    BACKUP_SFTP_COMMAND="ssh -F $CONF_DIR/ssh_config segqueue-backup-target -s sftp"
    export RESTIC_REPOSITORY

    # The password: the new one from the secret if it came, else the one already here.
    local pw="$CONF_DIR/restic-password"
    [ -s "$CONF_DIR/restic-password.new" ] && pw="$CONF_DIR/restic-password.new"
    [ -s "$pw" ] || die "no repository password on janus; set BACKUP_RESTIC_PASSWORD and run backup-install"
    probe_repo "$pw"
    case $? in
        0) say "the repository on the backup server opens with the password" ;;
        10) say "no repository yet: creating one"
            RESTIC_PASSWORD_FILE="$pw" restic_ init >/dev/null || die "restic init failed" ;;
        12) rm -f "$CONF_DIR/restic-password.new"
            die "BACKUP_RESTIC_PASSWORD does not open the existing repository; the password on janus is unchanged. Put the original password back in the secret (it cannot be changed this way)." ;;
        *) die "could not open or create the repository" ;;
    esac
    [ "$pw" = "$CONF_DIR/restic-password.new" ] && mv "$pw" "$CONF_DIR/restic-password"
    chmod 600 "$CONF_DIR/restic-password"

    local venv_py="$user_home/Asclepius/.venv/bin/python" mongod_bin=""
    [ -x "$venv_py" ] || die "no live venv Python at $venv_py"
    for m in "$user_home/opt/mongodb/bin/mongod" "$(command -v mongod 2>/dev/null)"; do
        [ -n "$m" ] && [ -x "$m" ] && { mongod_bin=$m; break; }
    done
    install -d -m 755 "$LIB_DEST"
    install -m 755 "$HERE/segqueue-backup.sh" "$LIB_DEST/segqueue-backup.sh"
    install -m 644 "$HERE/segqueue_backup.py" "$LIB_DEST/segqueue_backup.py"
    umask 077
    cat > "$CONF_DIR/backup.env" <<EOF
# Written by segqueue-backup.sh install-finish; overrides go in backup.local.env.
# No secrets here: the password is in restic-password, the key in id_ed25519.
RESTIC_REPOSITORY='$RESTIC_REPOSITORY'
RESTIC_PASSWORD_FILE='$CONF_DIR/restic-password'
RESTIC_BIN='$(command -v "$RESTIC_BIN" || echo "$RESTIC_BIN")'
BACKUP_SFTP_COMMAND='$BACKUP_SFTP_COMMAND'
BACKUP_PYTHON='$venv_py'
BACKUP_MONGOD='$mongod_bin'
GIRDER_MONGO_URI='$GIRDER_MONGO_URI'
BACKUP_GUARD_PATHS='$BACKUP_STATE $user_home/segqueue-data'
RESTIC_CACHE_DIR='/var/cache/segqueue-backup'
EOF
    for unit in "${UNITS[@]}"; do
        install -m 644 "$HERE/../systemd/$unit" "/etc/systemd/system/$unit"
    done
    systemctl daemon-reload
    systemctl enable --now segqueue-backup.timer segqueue-backup-check.timer
    say "timers installed and started; taking the first backup now (small: no CT images)"
    systemctl start segqueue-backup.service || say "WARNING: the first run did not succeed; see below"
    journalctl -u segqueue-backup.service -n 15 --no-pager 2>/dev/null | sed 's/^/    /' || true
    BACKUP_LIB="$LIB_DEST" bash "$LIB_DEST/segqueue-backup.sh" status
}

cmd_off() {
    need_root
    systemctl disable --now segqueue-backup.timer segqueue-backup-check.timer 2>/dev/null || true
    if systemctl is-active --quiet segqueue-backup.service 2>/dev/null; then
        say "a backup run is in progress; it will finish on its own, and no further run starts"
    fi
    say "hourly backups are off. Kept: the repository and every snapshot on the backup server,"
    say "  $CONF_DIR (key, pinned host key, password) and $LIB_DEST. On again: backup-install."
}

case "${1:-}" in
    run) cmd_run ;;
    check) cmd_check ;;
    status) cmd_status ;;
    restore-test) cmd_restore_test ;;
    install-prepare) cmd_install_prepare ;;
    install-finish) shift; cmd_install_finish "$@" ;;
    off) cmd_off ;;
    *) sed -n '2,27p' "$0"; exit 1 ;;
esac
