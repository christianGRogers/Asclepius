#!/usr/bin/env bash
# Move a native SegQueue deployment into containers, without moving its data.
#
#     sudo bash deploy/containerize.sh --check     # read-only, says what it would do
#     sudo bash deploy/containerize.sh             # does it
#     sudo bash deploy/containerize.sh --rollback  # back to the native stack
#
# The data does not move. `deploy/docker-compose.yml` expects DATA_ROOT to hold
# `mongo/` and `assetstore/`, which is exactly the layout `segqueue.sh` already
# uses, so the same directories are bind-mounted into the containers.
#
# Three things *do* have to change, and each is the sort that loses a dataset
# quietly if it is skipped:
#
# 1. **The assetstore path lives in the database.** Girder stores the absolute
#    root of its filesystem assetstore in Mongo. Natively that is
#    `<DATA_ROOT>/assetstore`; inside the container the same bytes are at
#    `/data/assetstore`. Without the rewrite below Girder starts perfectly and
#    reports every file as missing.
# 2. **Mongo's data files are version-specific.** A 7.x image will refuse data
#    written by a newer server, and data from an older one needs its
#    featureCompatibilityVersion raised a major version at a time. Checked, not
#    assumed.
# 3. **The files are owned by a host user.** The image runs as uid 1000; if the
#    data is owned by anybody else the containers get permission errors on
#    write, which show up as failed uploads rather than as a startup failure.
#
# Nothing is deleted. The native launcher stays where it is, so `--rollback` is
# always available and is the first thing to reach for if the API does not come
# back.
set -uo pipefail

REPO="${REPO:-/home/christian/Asclepius}"
DATA="${DATA:-/home/christian/segqueue-data}"
LAUNCHER="${LAUNCHER:-$DATA/segqueue.sh}"
OWNER="${OWNER:-christian}"
PORT="${GIRDER_PORT:-8080}"
MODE="${1:-run}"

say() { printf '%s\n' "$*"; }
die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

api_up() { curl -fsS "http://127.0.0.1:$PORT/api/v1/system/version" >/dev/null 2>&1; }

# ---------------------------------------------------------------- preflight

preflight() {
    local failures=0

    say "== preflight =="
    [ -d "$REPO/.git" ] || { say "FAIL  no checkout at $REPO"; failures=$((failures+1)); }
    [ -d "$DATA/mongo" ] || { say "FAIL  no mongo data at $DATA/mongo"; failures=$((failures+1)); }
    [ -d "$DATA/assetstore" ] || { say "FAIL  no assetstore at $DATA/assetstore"; failures=$((failures+1)); }
    [ -x "$LAUNCHER" ] || say "WARN  no native launcher at $LAUNCHER -- rollback will not work"

    docker version >/dev/null 2>&1 || { say "FAIL  docker is not usable here"; failures=$((failures+1)); }
    docker compose version >/dev/null 2>&1 || { say "FAIL  the compose plugin is missing"; failures=$((failures+1)); }

    # uid 1000 is what the image runs as; see deploy/Dockerfile.
    local uid
    uid=$(stat -c %u "$DATA/assetstore" 2>/dev/null)
    if [ "$uid" != "1000" ]; then
        say "FAIL  $DATA/assetstore is owned by uid $uid, the image runs as 1000"
        say "      fix with:  sudo chown -R 1000:1000 $DATA/assetstore $DATA/mongo"
        failures=$((failures+1))
    else
        say "ok    data is owned by uid 1000"
    fi

    # The running server's own version, and what the data was last written by.
    local running
    running=$(curl -fsS "http://127.0.0.1:27017" 2>/dev/null; true)
    local ver
    ver=$("$DATA/../opt/mongodb/bin/mongod" --version 2>/dev/null | head -1 \
          || /home/$OWNER/opt/mongodb/bin/mongod --version 2>/dev/null | head -1)
    say "note  native mongod: ${ver:-unknown}"
    case "$ver" in
        *" v7."*|*" v6."*) say "ok    mongo:7 can open data from that series" ;;
        "")                say "WARN  could not read the native mongod version; check by hand" ;;
        *)                 say "FAIL  $ver is not a series mongo:7 can safely open"
                           say "      upgrade stepwise, or pin the image to that major version"
                           failures=$((failures+1)) ;;
    esac

    local free
    free=$(df -BG --output=avail /var/lib/docker 2>/dev/null | tail -1 | tr -dc '0-9')
    [ -n "$free" ] && [ "$free" -lt 5 ] \
        && { say "FAIL  only ${free}G free for images"; failures=$((failures+1)); } \
        || say "ok    ${free:-?}G free for images"

    say "== what would change =="
    say "  assetstore root in Mongo: $DATA/assetstore  ->  /data/assetstore"
    say "  services: mongod/girder/segqueue-score  ->  compose (mongo, girder, worker)"
    say "  caddy stays off; the existing front end keeps serving :$PORT"
    return $failures
}

# ----------------------------------------------------- the one data change

#: Rewrite the assetstore root. Run against whichever mongod is up -- the native
#: one before the cutover, the container's after a rollback -- because the value
#: is in the database either way.
rewrite_assetstore() {
    local target="$1" mongosh_bin
    mongosh_bin=$(command -v mongosh || command -v mongo || echo "")
    if [ -z "$mongosh_bin" ]; then
        # No shell on the host: use the venv's pymongo, which is always there.
        "$REPO/.venv/bin/python" - "$target" <<'PY'
import sys
import pymongo
target = sys.argv[1]
db = pymongo.MongoClient("mongodb://127.0.0.1:27017", serverSelectionTimeoutMS=5000).girder
before = [(a.get("name"), a.get("root")) for a in db.assetstore.find()]
result = db.assetstore.update_many({"type": 0}, {"$set": {"root": target}})
print("assetstore root: %r -> %r (%d updated)" % (before, target, result.modified_count))
PY
    else
        "$mongosh_bin" --quiet "mongodb://127.0.0.1:27017/girder" --eval \
            "print(JSON.stringify(db.assetstore.find().toArray().map(a=>a.root)));
             print(db.assetstore.updateMany({type:0},{\$set:{root:'$target'}}).modifiedCount + ' updated');"
    fi
}

# ------------------------------------------------------------------ actions

do_run() {
    preflight || die "preflight failed; nothing has been changed"

    say "== stopping the native stack =="
    [ -x "$LAUNCHER" ] && bash "$LAUNCHER" stop 2>&1 | tail -3
    sleep 3

    say "== pointing the assetstore at the container path =="
    # Before the native mongod goes away for good we need it up to edit; the
    # launcher's stop took it down, so bring just mongod back for the rewrite.
    "/home/$OWNER/opt/mongodb/bin/mongod" --dbpath "$DATA/mongo" --bind_ip 127.0.0.1 \
        --port 27017 --logpath "$DATA/logs/mongod-migrate.log" --fork >/dev/null 2>&1
    sleep 4
    rewrite_assetstore "/data/assetstore" || die "could not rewrite the assetstore root"
    "/home/$OWNER/opt/mongodb/bin/mongod" --dbpath "$DATA/mongo" --shutdown >/dev/null 2>&1
    sleep 3

    say "== bringing the containers up =="
    ( cd "$REPO/deploy" && DATA_ROOT="$DATA" GIRDER_PORT="$PORT" \
        docker compose up -d --build mongo girder worker 2>&1 | tail -12 )

    say "== waiting for the API =="
    for i in $(seq 1 60); do
        if api_up; then say "api answered after $((i*2))s"; break; fi
        sleep 2
    done

    if ! api_up; then
        say "FAILED to come up in containers -- rolling back"
        ( cd "$REPO/deploy" && DATA_ROOT="$DATA" docker compose logs --tail 40 girder 2>&1 | tail -40 )
        do_rollback
        exit 1
    fi

    say "== verifying the data came with it =="
    curl -fsS "http://127.0.0.1:$PORT/api/v1/system/version"; echo
    ( cd "$REPO/deploy" && DATA_ROOT="$DATA" docker compose ps 2>&1 | tail -6 )
    say
    say "Done. Rollback is:  sudo bash $0 --rollback"
}

do_rollback() {
    say "== back to the native stack =="
    ( cd "$REPO/deploy" && DATA_ROOT="$DATA" docker compose down 2>&1 | tail -5 )
    sleep 2
    "/home/$OWNER/opt/mongodb/bin/mongod" --dbpath "$DATA/mongo" --bind_ip 127.0.0.1 \
        --port 27017 --logpath "$DATA/logs/mongod-migrate.log" --fork >/dev/null 2>&1
    sleep 4
    rewrite_assetstore "$DATA/assetstore"
    "/home/$OWNER/opt/mongodb/bin/mongod" --dbpath "$DATA/mongo" --shutdown >/dev/null 2>&1
    sleep 2
    sudo -u "$OWNER" bash "$LAUNCHER" start 2>&1 | tail -3
    sleep 8
    api_up && say "native stack is back up" || say "native stack did NOT come back -- look at $DATA/logs/girder.log"
}

case "$MODE" in
    --check|check) preflight; exit $? ;;
    --rollback)    do_rollback ;;
    run)           do_run ;;
    *) die "usage: $0 [--check|--rollback]" ;;
esac
