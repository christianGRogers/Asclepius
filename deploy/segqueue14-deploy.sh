#!/bin/bash
# Deploy SegQueue14 beside the live SegQueue on janus (D17, D23). Run on the server as
# the user that owns ~/Asclepius (christian). Each step checks itself and stops on a
# problem; re-running is safe.
#
#   bash segqueue14-deploy.sh install     # backup, install the plugin, restart Girder, check both load
#   bash segqueue14-deploy.sh populate    # dry run of the 675-volume pool (changes nothing)
#   bash segqueue14-deploy.sh populate --apply   # create the pool cases that have a seed
#   bash segqueue14-deploy.sh worker      # install and start the SegQueue14 scoring worker
#   bash segqueue14-deploy.sh status
#   bash segqueue14-deploy.sh off         # rollback switch: /segqueue14 off, live untouched
#
# What it never does: check out a branch in ~/Asclepius, reinstall the live plugin
# (server/), or write to the live SegQueue's data. The branch is cloned separately into
# ~/Asclepius-sq14, and only the shared package (repository root, --no-deps) and the
# girder-segqueue14 plugin are installed into the live venv.
set -euo pipefail

LIVE="${LIVE:-$HOME/Asclepius}"
SRC="${SRC:-$HOME/Asclepius-sq14}"
BRANCH="${BRANCH:-claude/segqueue14}"
# The live checkout's own remote, so the server's existing GitHub credentials apply.
REPO_URL="${REPO_URL:-$(git -C "$LIVE" remote get-url origin 2>/dev/null || echo https://github.com/christianGRogers/Asclepius.git)}"
PY="$LIVE/.venv/bin/python"
export GIRDER_MONGO_URI="${GIRDER_MONGO_URI:-mongodb://127.0.0.1:27017/girder}"
POOL_LIST="$SRC/configs/segqueue14/pool-2026-10.txt"

say() { printf '[sq14] %s\n' "$*"; }
die() { printf '[sq14] ERROR: %s\n' "$*" >&2; exit 1; }
[ -x "$PY" ] || die "no venv at $LIVE/.venv (set LIVE=...)"

fetch_branch() {
    if [ -d "$SRC/.git" ]; then
        git -C "$SRC" fetch -q origin "$BRANCH"
        git -C "$SRC" checkout -q -B "$BRANCH" "origin/$BRANCH"
    else
        git clone -q --branch "$BRANCH" "$REPO_URL" "$SRC"
    fi
    say "branch $BRANCH at $(git -C "$SRC" log -1 --format='%h %s' | cut -c1-70)"
}

plugins_loaded() {
    # Never fails: an empty or unreadable journal must not abort the script (set -e).
    { sudo journalctl -u segqueue-girder --since "-3min" --no-pager 2>/dev/null \
        | grep -oE 'Loaded plugin "[a-z0-9]*"|SegQueue14[^"]*' | sort -u; } || true
}

why_not_loaded() {
    say "why SegQueue14 did not load (Girder's log, last 3 minutes):"
    { sudo journalctl -u segqueue-girder --since "-3min" --no-pager 2>/dev/null \
        | grep -iE -A25 'segqueue14|Traceback' | tail -60; } || true
    say "and the plugin loaded by hand, with errors raised:"
    SEGQUEUE14_STRICT=1 "$PY" -c "
import girder_segqueue14 as p
class Root: pass
p.mount({'apiRoot': Root()})
print('[sq14] mount() by hand: OK -- so Girder did not call it (plugin not registered?)')
" 2>&1 | tail -30 || true
    "$PY" -c "
from importlib.metadata import entry_points
print('[sq14] girder.plugin entry points:', sorted(e.name for e in entry_points(group='girder.plugin')))"
}

install() {
    mkdir -p "$HOME/segqueue-data"
    local backup
    backup="$HOME/segqueue-data/pre-sq14-$(date +%Y%m%d-%H%M).archive.gz"
    if command -v mongodump >/dev/null 2>&1; then
        say "backup -> $backup"
        mongodump --uri "$GIRDER_MONGO_URI" --archive="$backup" --gzip --quiet || die "mongodump failed; nothing installed"
    else
        # No MongoDB database tools here: dump with the venv's pymongo instead, in
        # mongodump's directory layout (girder/<collection>.bson + .metadata.json),
        # which `mongorestore --dir <dir>` restores. Only metadata lives in Mongo;
        # the files themselves are in the assetstore on disk and are not touched.
        backup="${backup%.archive.gz}"
        say "backup (pymongo, mongodump layout) -> $backup.tar.gz"
        "$PY" - "$backup" <<'PYEOF' || die "backup failed; nothing installed"
import json, os, sys
from bson import encode
from bson.json_util import dumps
from pymongo import MongoClient
out = sys.argv[1]
client = MongoClient(os.environ['GIRDER_MONGO_URI'])
db = client.get_default_database()
target = os.path.join(out, db.name)
os.makedirs(target, exist_ok=True)
total = 0
for name in sorted(db.list_collection_names()):
    n = 0
    with open(os.path.join(target, name + '.bson'), 'wb') as handle:
        for doc in db[name].find({}):
            handle.write(encode(doc)); n += 1
    indexes = [dict(v, key=dict(v['key']), name=k) for k, v in db[name].index_information().items()]
    with open(os.path.join(target, name + '.metadata.json'), 'w') as handle:
        handle.write(dumps({'indexes': indexes, 'collectionName': name}))
    total += n
print(f'[sq14] dumped {total} documents from {len(db.list_collection_names())} collections of {db.name}')
PYEOF
        tar czf "$backup.tar.gz" -C "$(dirname "$backup")" "$(basename "$backup")" && rm -rf "$backup" \
            || die "could not pack the backup; nothing installed"
        say "restore, if ever needed: tar xzf $backup.tar.gz && mongorestore --drop --dir $(basename "$backup")"
    fi
    fetch_branch
    say "installing the shared package (repository root, --no-deps) and girder-segqueue14"
    "$PY" -m pip install -q --no-deps "$SRC"
    "$PY" -m pip install -q "$SRC/server/girder_segqueue14[scoring]"
    "$PY" -c "import girder_segqueue14, segqueue14, segqueue; print('[sq14] import ok: segqueue14 protocol', segqueue14.PROTOCOL_VERSION)"
    say "restarting Girder (a few seconds of downtime for the live SegQueue too)"
    sudo systemctl restart segqueue-girder
    for _ in $(seq 1 30); do
        code=$(curl -s -o /dev/null -w '%{http_code}' localhost:8080/api/v1/segqueue/project || true)
        [ "$code" = "401" ] && break
        sleep 2
    done
    live=$(curl -s -o /dev/null -w '%{http_code}' localhost:8080/api/v1/segqueue/project || true)
    new=$(curl -s -o /dev/null -w '%{http_code}' localhost:8080/api/v1/segqueue14/project || true)
    say "live /segqueue/project -> $live (want 401); /segqueue14/project -> $new (want 401)"
    plugins_loaded | sed 's/^/[sq14]   /'
    [ "$live" = "401" ] || die "the LIVE SegQueue is not answering as before -- run: bash $0 off"
    if [ "$new" != "401" ]; then
        why_not_loaded
        die "SegQueue14 did not load (the live SegQueue is fine). Send the lines above."
    fi
    say "installed. Next: bash $0 populate"
}

populate() {
    [ -f "$POOL_LIST" ] || fetch_branch
    local bin="$LIVE/.venv/bin/segqueue14-populate"
    if [ "${1:-}" = "--apply" ]; then
        say "creating the pool cases that have a seed (hashes each CT once; can take a while)"
        "$bin" --pool-list "$POOL_LIST" --require-seed
        say "done. Re-run 'populate --apply' as more seeds land; it only adds the new ones."
    else
        "$bin" --pool-list "$POOL_LIST" --require-seed --dry-run
        say "dry run only. If it reads right (not found 0): bash $0 populate --apply"
    fi
}

worker() {
    sudo cp "$SRC/server/girder_segqueue14/segqueue14-worker.service" /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable --now segqueue14-worker
    sleep 3
    systemctl is-active segqueue14-worker && systemctl is-active segqueue-worker \
        && say "both workers running"
}

status() {
    plugins_loaded | sed 's/^/[sq14]   /' || true
    for u in segqueue-girder segqueue-worker segqueue14-worker; do
        say "$u: $(systemctl is-active $u 2>/dev/null || true)"
    done
    "$PY" - <<'PYEOF'
import os
from pymongo import MongoClient
db = MongoClient(os.environ['GIRDER_MONGO_URI']).get_default_database()
c = db['segqueue14_case']
print('[sq14] cases', c.count_documents({}), '| with seed', c.count_documents({'seedFileId': {'$ne': None}}),
      '| imagecas', c.count_documents({'name': {'$regex': '^imagecas_'}}),
      '| assignments', db['segqueue14_assignment'].count_documents({}),
      '| live cases (unchanged)', db['segqueue_case'].count_documents({}))
PYEOF
}

off() {
    sudo systemctl stop segqueue14-worker 2>/dev/null || true
    sudo mkdir -p /etc/systemd/system/segqueue-girder.service.d
    printf '[Service]\nEnvironment=SEGQUEUE14_DISABLE=1\n' | sudo tee /etc/systemd/system/segqueue-girder.service.d/segqueue14-off.conf >/dev/null
    sudo systemctl daemon-reload && sudo systemctl restart segqueue-girder
    say "SegQueue14 switched off (its data is kept). To switch it back on:"
    say "  sudo rm /etc/systemd/system/segqueue-girder.service.d/segqueue14-off.conf && sudo systemctl daemon-reload && sudo systemctl restart segqueue-girder"
}

case "${1:-}" in
    install) install ;;
    diagnose) why_not_loaded ;;
    populate) shift; populate "$@" ;;
    worker) worker ;;
    status) status ;;
    off) off ;;
    *) sed -n '2,12p' "$0"; exit 1 ;;
esac
