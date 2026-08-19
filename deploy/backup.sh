#!/bin/sh
# Nightly backup: a consistent Mongo dump plus the assetstore, into restic.
#
# Run from cron on the host, not in a container:
#   0 2 * * *  /srv/segqueue/deploy/backup.sh >> /var/log/segqueue-backup.log 2>&1
#
# The ordering matters. `mongodump` first, into the same tree restic is about to
# read, so the metadata snapshot is never newer than the files it describes. The
# other way round produces a backup that references submissions it does not
# contain -- which looks fine until the day you restore it.
set -eu

: "${DATA_ROOT:=/srv/segqueue}"
: "${RESTIC_REPOSITORY:?set RESTIC_REPOSITORY, e.g. /mnt/backup/segqueue or sftp:nas:/segqueue}"
: "${RESTIC_PASSWORD_FILE:?set RESTIC_PASSWORD_FILE}"
: "${COMPOSE_DIR:=$(dirname "$0")}"

DUMP_DIR="${DATA_ROOT}/dump"
mkdir -p "${DUMP_DIR}"

echo "== $(date -Is) dumping database"
docker compose -f "${COMPOSE_DIR}/docker-compose.yml" exec -T mongo \
    mongodump --archive --gzip --db=girder > "${DUMP_DIR}/girder.archive.gz.tmp"
mv "${DUMP_DIR}/girder.archive.gz.tmp" "${DUMP_DIR}/girder.archive.gz"

echo "== $(date -Is) backing up"
restic backup \
    --tag segqueue \
    --exclude "${DATA_ROOT}/mongo" \
    "${DUMP_DIR}" "${DATA_ROOT}/assetstore"

# Keep enough history to survive a mistake noticed late -- a bad bulk reassign,
# say, or a retired case that should not have been. Restic's forget is cheap;
# discovering you only have last night's copy is not.
echo "== $(date -Is) pruning"
restic forget --tag segqueue --prune \
    --keep-daily 14 --keep-weekly 8 --keep-monthly 12

echo "== $(date -Is) verifying"
restic check --read-data-subset=1%

echo "== $(date -Is) done"
