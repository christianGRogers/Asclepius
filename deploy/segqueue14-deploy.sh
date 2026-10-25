#!/bin/bash
# Deploy SegQueue14 beside the live SegQueue on janus (D17, D23). Run on the server as
# the user that owns ~/Asclepius (christian), or as root with SQ14_USER=christian (the
# GitHub workflow does that). Each step checks itself and stops on a problem;
# re-running is safe.
#
#   bash segqueue14-deploy.sh install     # backup, install the plugin, restart Girder, check both load
#   bash segqueue14-deploy.sh populate    # dry run of the 675-volume pool (changes nothing)
#   bash segqueue14-deploy.sh populate --apply   # create the pool cases that have a seed
#   bash segqueue14-deploy.sh worker      # start the SegQueue14 scoring worker
#   bash segqueue14-deploy.sh status
#   bash segqueue14-deploy.sh diagnose    # why /segqueue14 is not answering
#   bash segqueue14-deploy.sh off         # rollback switch: /segqueue14 off, live untouched
#
# D36 (issue #124): one queue, one group pair, one collection. In this order; the
# destructive steps are dry runs without --apply and refuse on their preconditions:
#   bash segqueue14-deploy.sh backup                 # mongodump of girder (pre-d36-<time>)
#   bash segqueue14-deploy.sh retire-live            # uninstall the old girder_segqueue plugin, restart
#   bash segqueue14-deploy.sh restore-live           # rollback of retire-live: reinstall it, restart
#   bash segqueue14-deploy.sh retire-groups [--apply]    # delete segqueue-annotators / -reviewers
#   bash segqueue14-deploy.sh consolidate [--apply]      # SegQueue14 writes into SegQueue (installs main)
# CCTA-Pool and ImageCAS-X are out of scope: no step writes to them (status counts them).
#
# What it never does: check out a branch in ~/Asclepius, reinstall the old plugin
# (server/; only restore-live does, from that checkout), or write to the old
# SegQueue's data outside the D36 steps. `main` is cloned separately into
# ~/Asclepius-sq14, and only the shared package (repository root, --no-deps) and the
# girder-segqueue14 plugin are installed into the live venv.
#
# Girder runs either under systemd (segqueue-girder.service) or from the launcher
# ~/segqueue-data/segqueue.sh; the script asks which and restarts it the same way.
set -euo pipefail

export GIRDER_MONGO_URI="${GIRDER_MONGO_URI:-mongodb://127.0.0.1:27017/girder}"

# As root (the CI path), act for the deploy user: their home, their files.
SQ14_USER="${SQ14_USER:-}"
if [ "$(id -u)" = 0 ] && [ -n "$SQ14_USER" ]; then
    USER_HOME="$(getent passwd "$SQ14_USER" | cut -d: -f6)"
else
    SQ14_USER="$(id -un)"
    USER_HOME="$HOME"
fi
as_user() {
    if [ "$(id -u)" = 0 ] && [ "$SQ14_USER" != root ]; then
        runuser -u "$SQ14_USER" -- env HOME="$USER_HOME" GIRDER_MONGO_URI="$GIRDER_MONGO_URI" "$@"
    else
        "$@"
    fi
}
SUDO=""; [ "$(id -u)" = 0 ] || SUDO="sudo"

LIVE="${LIVE:-$USER_HOME/Asclepius}"
SRC="${SRC:-$USER_HOME/Asclepius-sq14}"
DATA="${DATA:-$USER_HOME/segqueue-data}"
LAUNCHER="$DATA/segqueue.sh"
BRANCH="${BRANCH:-main}"   # deploy the released code (CONTRIBUTING.md §4)
# The live checkout's own remote, so the server's existing GitHub credentials apply.
REPO_URL="${REPO_URL:-$(as_user git -C "$LIVE" remote get-url origin 2>/dev/null || echo https://github.com/christianGRogers/Asclepius.git)}"
PY="$LIVE/.venv/bin/python"
POOL_LIST="$SRC/configs/segqueue14/pool-2026-10.txt"

say() { printf '[sq14] %s\n' "$*"; }
die() { printf '[sq14] ERROR: %s\n' "$*" >&2; exit 1; }
[ -x "$PY" ] || die "no venv at $LIVE/.venv (set LIVE=...)"

fetch_branch() {
    if [ -d "$SRC/.git" ]; then
        as_user git -C "$SRC" fetch -q origin "$BRANCH"
        as_user git -C "$SRC" checkout -q -B "$BRANCH" "origin/$BRANCH"
    else
        as_user git clone -q --branch "$BRANCH" "$REPO_URL" "$SRC"
    fi
    say "branch $BRANCH at $(as_user git -C "$SRC" log -1 --format='%h %s' | cut -c1-70)"
}

# ------------------------------------------------------------ how Girder runs here

# Which Girder is serving: systemd's (its MainPID is a `girder serve`) or one the
# launcher started (a `girder serve` that is not systemd's MainPID). "active" alone
# is not enough -- a unit crash-looping on an occupied port reports active too.
systemd_pid() { systemctl show -p MainPID --value segqueue-girder 2>/dev/null || echo 0; }
launcher_girder() {
    local main pid
    main=$(systemd_pid)
    for pid in $(pgrep -f 'girder serve' || true); do
        [ "$pid" != "$main" ] && { echo "$pid"; return 0; }
    done
    return 1
}
under_systemd() { ! launcher_girder >/dev/null && systemctl is-active --quiet segqueue-girder 2>/dev/null; }

girder_log() {   # recent Girder output, wherever it goes
    if under_systemd; then
        $SUDO journalctl -u segqueue-girder --since "-5min" --no-pager 2>/dev/null || true
    fi
    if [ -f "$DATA/logs/girder.log" ]; then tail -n 400 "$DATA/logs/girder.log" || true; fi
}

restart_girder() {
    if launcher_girder >/dev/null && [ -f "$LAUNCHER" ]; then
        # The launcher runs this box. A systemd Girder or mongod beside it can only
        # crash-loop on the occupied port / locked dbpath -- and a mongod unit that
        # retries every 5 s could grab the dbpath while the launcher restarts its own.
        # Stop such units first, but only if they are not what is serving.
        local unit main
        for unit in segqueue-girder segqueue-mongod; do
            main=$(systemctl show -p MainPID --value "$unit" 2>/dev/null || echo 0)
            if [ "${main:-0}" != 0 ] && kill -0 "$main" 2>/dev/null; then
                if [ "$unit" = segqueue-mongod ] || [ "$main" = "$(launcher_girder)" ]; then
                    die "$unit (pid $main) is running alongside the launcher; not touching either -- run 'diagnose' and sort this out by hand"
                fi
            fi
            if [ "$(systemctl show -p ActiveState --value "$unit" 2>/dev/null)" != inactive ] \
                    && [ "$(systemctl show -p LoadState --value "$unit" 2>/dev/null)" = loaded ]; then
                say "stopping $unit.service (crash-looping beside the launcher's process)"
                $SUDO systemctl stop "$unit"
            fi
        done
        say "restarting Girder: $LAUNCHER restart (mongod, Girder and the live worker; ~10 s)"
        as_user bash "$LAUNCHER" restart
    elif under_systemd; then
        say "restarting Girder: systemctl restart segqueue-girder"
        $SUDO systemctl restart segqueue-girder
    elif [ -f "$LAUNCHER" ]; then
        say "restarting Girder: $LAUNCHER restart (also restarts the live worker)"
        as_user bash "$LAUNCHER" restart
    else
        die "Girder is neither the segqueue-girder service nor started by $LAUNCHER; restart it by hand"
    fi
}

code_of() { curl -s -o /dev/null -w '%{http_code}' "localhost:8080/api/v1/$1" || true; }

wait_for_girder() {
    # Girder itself, not a plugin route: the old /segqueue is gone after retire-live.
    for _ in $(seq 1 45); do
        [ "$(code_of system/version)" = 200 ] && return 0
        sleep 2
    done
    return 1
}

# The old 4-class plugin's distribution (server/), retired by D36.
old_installed() { as_user "$PY" -m pip show -q girder-segqueue >/dev/null 2>&1; }

# The D36 tool, run from the main checkout (newer than the installed plugin).
d36() { as_user env PYTHONPATH="$SRC/server" "$PY" -m girder_segqueue14.consolidate "$@"; }

plugins_loaded() {
    # Never fails: an empty or unreadable log must not abort the script (set -e).
    { girder_log | grep -oE 'Loaded plugin "?[a-z0-9_]*"?|SegQueue14 [a-z][^.]*' | sort | uniq -c | tail -8; } || true
}

why_not_loaded() {
    say "processes:"
    { pgrep -af 'girder serve|segqueue-score|segqueue14-score' | cut -c1-160; } || true
    say "segqueue-girder service: $(systemctl is-active segqueue-girder 2>/dev/null || true) (MainPID $(systemd_pid)); segqueue-mongod service: $(systemctl is-active segqueue-mongod 2>/dev/null || true); launcher: $([ -f "$LAUNCHER" ] && echo "$LAUNCHER" || echo none); launcher's girder: $(launcher_girder || echo none)"
    for p in $(pgrep -f 'girder serve' || true); do
        say "girder pid $p started $(ps -o lstart= -p "$p" 2>/dev/null | xargs) by $(ps -o user= -p "$p" | xargs); SEGQUEUE14_DISABLE set: $(tr '\0' '\n' < /proc/"$p"/environ 2>/dev/null | grep -c '^SEGQUEUE14_DISABLE=' || true)"
    done
    say "Girder's log about plugins / SegQueue14 / tracebacks:"
    { girder_log | grep -iE -B2 -A25 'segqueue14|Traceback|Loaded plugin' | tail -80; } || true
    say "the plugin loaded by hand, with errors raised:"
    as_user env SEGQUEUE14_STRICT=1 "$PY" -c "
import girder_segqueue14 as p
class Root: pass
p.mount({'apiRoot': Root()})
print('[sq14] mount() by hand: OK -- so the running Girder did not load it (not restarted, or another venv?)')
" 2>&1 | tail -30 || true
    as_user "$PY" -c "
from importlib.metadata import entry_points, version
print('[sq14] girder', version('girder'), '| girder.plugin entry points:', sorted(e.name for e in entry_points(group='girder.plugin')))"
}

# ------------------------------------------------------------ commands

backup() {
    as_user mkdir -p "$DATA"
    local backup
    backup="$DATA/${1:-pre-sq14}-$(date +%Y%m%d-%H%M)"
    if command -v mongodump >/dev/null 2>&1; then
        say "backup -> $backup.archive.gz"
        as_user mongodump --uri "$GIRDER_MONGO_URI" --archive="$backup.archive.gz" --gzip --quiet \
            || die "mongodump failed; nothing installed"
        return
    fi
    # No MongoDB database tools here: dump with the venv's pymongo, in mongodump's
    # directory layout (girder/<collection>.bson + .metadata.json), which
    # `mongorestore --dir <dir>` restores. Only metadata lives in Mongo; the files
    # themselves are in the assetstore on disk and are not touched.
    say "backup (pymongo, mongodump layout) -> $backup.tar.gz"
    as_user "$PY" - "$backup" <<'PYEOF' || die "backup failed; nothing installed"
import os, sys
from bson import encode
from bson.json_util import dumps
from pymongo import MongoClient
out = sys.argv[1]
db = MongoClient(os.environ['GIRDER_MONGO_URI']).get_default_database()
target = os.path.join(out, db.name)
os.makedirs(target, exist_ok=True)
total = 0
names = sorted(db.list_collection_names())
for name in names:
    with open(os.path.join(target, name + '.bson'), 'wb') as handle:
        for doc in db[name].find({}):
            handle.write(encode(doc)); total += 1
    indexes = [dict(v, key=dict(v['key']), name=k) for k, v in db[name].index_information().items()]
    with open(os.path.join(target, name + '.metadata.json'), 'w') as handle:
        handle.write(dumps({'indexes': indexes, 'collectionName': name}))
print(f'[sq14] dumped {total} documents from {len(names)} collections of {db.name}')
PYEOF
    as_user tar czf "$backup.tar.gz" -C "$(dirname "$backup")" "$(basename "$backup")" \
        || die "could not pack the backup; nothing installed"
    rm -rf "$backup"
    say "restore, if ever needed: tar xzf $backup.tar.gz && mongorestore --drop --dir $(basename "$backup")"
}

install() {
    backup
    fetch_branch
    say "installing the shared package (repository root, --no-deps) and girder-segqueue14"
    as_user "$PY" -m pip install -q --no-deps "$SRC"
    as_user "$PY" -m pip install -q "$SRC/server/girder_segqueue14[scoring]"
    as_user "$PY" -c "import girder_segqueue14, segqueue14, segqueue; print('[sq14] import ok: segqueue14 protocol', segqueue14.PROTOCOL_VERSION)"
    restart_girder
    wait_for_girder || true
    local live new
    live=$(code_of segqueue/project)
    new=$(code_of segqueue14/project)
    plugins_loaded
    if old_installed; then
        say "live /segqueue/project -> $live (want 401); /segqueue14/project -> $new (want 401)"
        [ "$live" = "401" ] || die "the LIVE SegQueue is not answering as before -- run: bash $0 off"
    else
        say "/segqueue14/project -> $new (want 401); old plugin retired (D36): /segqueue/project -> $live"
    fi
    if [ "$new" != "401" ]; then
        why_not_loaded
        die "SegQueue14 did not load (the live SegQueue is fine). See the lines above."
    fi
    # A running worker still has the old code (labels, protocol) in memory.
    if pgrep -f segqueue14-score >/dev/null; then
        say "restarting the SegQueue14 worker so it runs the new code"
        worker
    fi
    say "installed. Next: bash $0 populate"
}

populate() {
    [ -f "$POOL_LIST" ] || fetch_branch
    local bin="$LIVE/.venv/bin/segqueue14-populate"
    if [ "${1:-}" = "--apply" ]; then
        say "creating the pool cases that have a seed (hashes each CT once; can take a while)"
        as_user "$bin" --pool-list "$POOL_LIST" --require-seed
        say "done. Re-run 'populate --apply' as more seeds land; it only adds the new ones."
    else
        as_user "$bin" --pool-list "$POOL_LIST" --require-seed --dry-run
        say "dry run only. If it reads right (not found 0): bash $0 populate --apply"
    fi
}

stop_worker() {
    $SUDO systemctl stop segqueue14-worker 2>/dev/null || true
    pkill -f segqueue14-score 2>/dev/null || true
    for _ in 1 2 3 4 5; do pgrep -f segqueue14-score >/dev/null || return 0; sleep 1; done
    pkill -9 -f segqueue14-score 2>/dev/null || true
}

worker() {
    # (Re)start: a worker left over from an older install keeps the old code.
    stop_worker
    if under_systemd; then
        $SUDO cp "$SRC/server/girder_segqueue14/segqueue14-worker.service" /etc/systemd/system/
        $SUDO systemctl daemon-reload
        $SUDO systemctl enable --now segqueue14-worker
    elif [ "$(id -u)" = 0 ] && command -v systemd-run >/dev/null; then
        # Launcher-run box, from CI: a transient unit, fully detached from this SSH
        # session (a nohup'd child keeps the session open) and restarted if it dies.
        # Like the launcher's own processes it does not survive a reboot: after one,
        # run the `worker` step again.
        as_user mkdir -p "$DATA/logs"
        systemctl reset-failed segqueue14-worker 2>/dev/null || true
        systemd-run --unit segqueue14-worker --uid "$SQ14_USER" --gid "$(id -gn "$SQ14_USER")" \
            --working-directory "$LIVE" -p Restart=always -p RestartSec=10 \
            -E GIRDER_MONGO_URI="$GIRDER_MONGO_URI" -E GIRDER_SERVER_MODE=production \
            -p StandardOutput="append:$DATA/logs/worker14.log" -p StandardError="append:$DATA/logs/worker14.log" \
            "$LIVE/.venv/bin/segqueue14-score" --poll 30 --sweep 3600
    else
        # By hand, as the deploy user: the way the launcher starts the live worker.
        as_user mkdir -p "$DATA/logs"
        as_user bash -c "cd '$LIVE' && setsid nohup '$LIVE/.venv/bin/segqueue14-score' --poll 30 --sweep 3600 >> '$DATA/logs/worker14.log' 2>&1 < /dev/null &"
    fi
    sleep 3
    { pgrep -af 'segqueue-score|segqueue14-score' | cut -c1-120; } || true
}

status() {
    say "girder: $(pgrep -f 'girder serve' >/dev/null && echo up || echo down); /segqueue14/project -> $(code_of segqueue14/project); /segqueue14/stats -> $(code_of segqueue14/stats); old /segqueue/stats -> $(code_of segqueue/stats)"
    say "old plugin (girder-segqueue): $(old_installed && echo installed || echo 'not installed (retired, D36)')"
    { pgrep -af 'segqueue-score|segqueue14-score' | cut -c1-120; } || true
    as_user "$PY" - <<'PYEOF'
import os
from pymongo import MongoClient
db = MongoClient(os.environ['GIRDER_MONGO_URI']).get_default_database()
c = db['segqueue14_case']
print('[sq14] cases', c.count_documents({}), '| with seed', c.count_documents({'seedFileId': {'$ne': None}}),
      '| no approved read yet', c.count_documents({'approvedCount': {'$in': [0, None]}}),
      '| prelabelled', c.count_documents({'prelabelFileId': {'$ne': None}}),
      '| imagecas', c.count_documents({'name': {'$regex': '^imagecas_'}}),
      '| assignments', db['segqueue14_assignment'].count_documents({}),
      '| submissions', db['segqueue14_submission'].count_documents({}),
      '| old queue cases (kept)', db['segqueue_case'].count_documents({}))
stored = db['setting'].find_one({'key': 'segqueue14.project'})
print('[sq14] project setting:', 'stored (' + str(len((stored.get('value') or {}).get('segments') or [])) + ' segments)'
      if stored else 'default (from the code)')
print('[sq14] groups:', ', '.join(sorted(g['name'] for g in db['group'].find({'name': {'$regex': '^segqueue'}}))) or 'none')
for coll in sorted(db['collection'].find({}), key=lambda x: x['name']):
    top = sorted(f['name'] for f in db['folder'].find({'parentId': coll['_id'], 'parentCollection': 'collection'}))
    items = db['item'].count_documents({'baseParentType': 'collection', 'baseParentId': coll['_id']})
    print(f"[sq14] collection {coll['name']}: {items} items; {', '.join(top) or '(no folders)'}")
PYEOF
}

# ------------------------------------------------------------ D36 (issue #124)

recent_backup() {   # a D36 database dump from the last 24 h, or nothing
    as_user find "$DATA" -maxdepth 1 \( -name 'pre-d36-*.archive.gz' -o -name 'pre-d36-*.tar.gz' \) \
        -size +0 -mmin -1440 2>/dev/null | sort | tail -1
}

d36_backup() {
    status
    backup pre-d36
    say "backup done: $(recent_backup) ($(as_user du -h "$(recent_backup)" | cut -f1))"
}

retire_live() {
    local m
    m=$(recent_backup)
    [ -n "$m" ] || die "no D36 backup from the last 24 h in $DATA; run: bash $0 backup"
    say "backup: $m"
    if ! old_installed; then
        say "girder-segqueue is not installed: already retired"
    else
        say "stopping the old worker (segqueue-score), uninstalling girder-segqueue (its Mongo collections stay)"
        $SUDO systemctl stop segqueue-worker 2>/dev/null || true
        pkill -f 'bin/segqueue-score' 2>/dev/null || true
        as_user "$PY" -m pip uninstall -q -y girder-segqueue
        restart_girder
    fi
    wait_for_girder || die "Girder did not come back -- bash $0 diagnose; roll back: bash $0 restore-live"
    # The launcher starts segqueue-score too; with the package gone there is none.
    pkill -f 'bin/segqueue-score' 2>/dev/null || true
    local old new stats
    old=$(code_of segqueue/stats); new=$(code_of segqueue14/project); stats=$(code_of segqueue14/stats)
    plugins_loaded
    say "old /segqueue/stats -> $old (want 404); /segqueue14/project -> $new (want 401); /segqueue14/stats -> $stats (want 401)"
    [ "$old" = 404 ] || die "the old plugin still answers"
    [ "$new" = 401 ] || { why_not_loaded; die "SegQueue14 is not answering; roll back: bash $0 restore-live"; }
    status
    say "old queue retired. Next: bash $0 retire-groups"
}

restore_live() {
    say "reinstalling the old plugin from $LIVE/server (rollback of retire-live)"
    as_user "$PY" -m pip install -q "$LIVE/server[scoring]"
    restart_girder
    wait_for_girder || true
    say "old /segqueue/project -> $(code_of segqueue/project) (want 401); /segqueue14/project -> $(code_of segqueue14/project)"
}

retire_groups() {
    if old_installed; then die "girder-segqueue is installed; run retire-live first (its ensureGroups() recreates the groups)"; fi
    fetch_branch
    if [ "${1:-}" = "--apply" ]; then
        d36 groups --apply
    else
        d36 groups
        say "dry run. To delete: bash $0 retire-groups --apply"
    fi
}

consolidate() {
    if old_installed; then die "girder-segqueue is installed; run retire-live first"; fi
    fetch_branch
    grep -q '^COLLECTION_NAME = "SegQueue"$' "$SRC/server/girder_segqueue14/constants.py" \
        || die "main's SegQueue14 does not write into SegQueue yet; nothing done"
    if [ "${1:-}" != "--apply" ]; then
        d36 collection --phase move
        d36 collection --phase drop
        say "dry run. To apply: bash $0 consolidate --apply (moves, installs main, removes SegQueue14)"
        return
    fi
    d36 collection --phase move --apply || die "move refused or failed; nothing installed"
    install
    d36 collection --phase drop --apply || die "the SegQueue14 collection was not removed (see above)"
    status
}

off() {
    pkill -f segqueue14-score 2>/dev/null || true
    $SUDO systemctl stop segqueue14-worker 2>/dev/null || true
    if under_systemd; then
        $SUDO mkdir -p /etc/systemd/system/segqueue-girder.service.d
        printf '[Service]\nEnvironment=SEGQUEUE14_DISABLE=1\n' | $SUDO tee /etc/systemd/system/segqueue-girder.service.d/segqueue14-off.conf >/dev/null
        $SUDO systemctl daemon-reload && $SUDO systemctl restart segqueue-girder
        say "SegQueue14 switched off (its data is kept). Back on: remove segqueue14-off.conf, daemon-reload, restart"
    else
        # Launcher box: uninstalling the plugin is the switch (data is kept).
        as_user "$PY" -m pip uninstall -q -y girder-segqueue14
        restart_girder
        say "SegQueue14 uninstalled and Girder restarted (its data is kept). Back on: bash $0 install"
    fi
}

case "${1:-}" in
    install) install ;;
    diagnose) why_not_loaded ;;
    populate) shift; populate "$@" ;;
    worker) worker ;;
    status) status ;;
    off) off ;;
    backup) d36_backup ;;
    retire-live) retire_live ;;
    restore-live) restore_live ;;
    retire-groups) shift; retire_groups "$@" ;;
    consolidate) shift; consolidate "$@" ;;
    *) sed -n '2,25p' "$0"; exit 1 ;;
esac
