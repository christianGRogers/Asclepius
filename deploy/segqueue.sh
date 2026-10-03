#!/usr/bin/env bash
# Start/stop the SegQueue stack natively (no Docker on this box).
# Mirrors deploy/docker-compose.yml minus Caddy: mongod + girder + score worker.
set -euo pipefail

REPO=/home/christian/Asclepius
DATA=/home/christian/segqueue-data
MONGO=/home/christian/opt/mongodb/bin/mongod
export GIRDER_MONGO_URI="mongodb://127.0.0.1:27017/girder"
export GIRDER_SERVER_MODE=production

start() {
    "$MONGO" --dbpath "$DATA/mongo" --bind_ip 127.0.0.1 --port 27017 \
        --wiredTigerCacheSizeGB 2 --logpath "$DATA/logs/mongod.log" --fork
    # setsid+nohup: otherwise these die with the shell that started them,
    # the way the first girder process did. mongod --fork already detaches.
    setsid nohup "$REPO/.venv/bin/girder" serve --mode production -H 0.0.0.0 -p 8080 \
        >> "$DATA/logs/girder.log" 2>&1 < /dev/null &
    setsid nohup "$REPO/.venv/bin/segqueue-score" --poll 30 --sweep 3600 \
        >> "$DATA/logs/worker.log" 2>&1 < /dev/null &
    echo "starting; http://localhost:8080"
}

stop() {
    pkill -f segqueue-score || true
    pkill -f "girder serve" || true
    "$MONGO" --dbpath "$DATA/mongo" --shutdown || true
    echo "stopped"
}

status() {
    pgrep -f "mongod --dbpath $DATA/mongo" >/dev/null && echo "mongod    up" || echo "mongod    down"
    pgrep -f "girder serve"                >/dev/null && echo "girder    up" || echo "girder    down"
    pgrep -f segqueue-score                >/dev/null && echo "worker    up" || echo "worker    down"
    curl -fsS http://127.0.0.1:8080/api/v1/system/version 2>/dev/null && echo || echo "api unreachable"
}

case "${1:-status}" in
    start) start ;; stop) stop ;; restart) stop; sleep 2; start ;; status) status ;;
    *) echo "usage: $0 {start|stop|restart|status}" >&2; exit 1 ;;
esac
