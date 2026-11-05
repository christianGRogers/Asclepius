#!/bin/bash
# The backup steps of the "SegQueue14 on janus" workflow (D42, issue #283), run on
# the GitHub runner. Each step reaches janus the way the other deploy steps do
# (password via sshpass -e, sudo via stdin) and runs segqueue14-deploy.sh there,
# which hands over to deploy/backup/segqueue-backup.sh.
#
#   backup-install       janus: restic, an SSH key, the repository password ->
#                        backup server: authorise that key (SFTP only, if it can) ->
#                        janus: find the route that works, pin the host key,
#                        open/create the repository, start the timers, first backup
#   backup-status        janus: read-only report; fails if the newest snapshot is > 2 h old
#   backup-restore-test  janus: restore into a scratch folder + scratch Mongo and check
#   backup-off           janus: stop and disable the timers (keeps every snapshot)
#
# Environment (from secrets): HOST PORT USERNAME SSHPASS SFTP_PORT
#   RESTIC_PASSWORD_SECRET (install only), LAN_ADDRESS (optional host:port),
#   SFTP_KNOWN_HOSTS (optional: the backup server's known_hosts line(s)).
# Never prints a password; GitHub masks the secrets in anything else that is printed.
set -euo pipefail

STEP="${1:?step}"
KH="$HOME/.ssh/known_hosts"            # janus's, written by the workflow's trust step
KH_BACKUP="$HOME/.ssh/known_hosts_backup"
SSH_OPTS=(-o BatchMode=no -o ConnectTimeout=20 -o StrictHostKeyChecking=yes)

say() { printf '[backup] %s\n' "$*"; }
die() { printf '::error::%s\n' "$*"; exit 1; }

# Run segqueue14-deploy.sh <args> on janus as root, after updating the server's clone.
on_janus() {
    local args="$*"
    cat > remote.sh <<EOF
set -uo pipefail
SQ14_USER='${USERNAME}'
home=\$(getent passwd "\$SQ14_USER" | cut -d: -f6)
src="\$home/Asclepius-sq14"
if [ -d "\$src/.git" ]; then
  runuser -u "\$SQ14_USER" -- env HOME="\$home" git -C "\$src" fetch -q origin main \
    && runuser -u "\$SQ14_USER" -- env HOME="\$home" git -C "\$src" checkout -q -B main origin/main \
    || echo "[sq14] could not update \$src; using what is there"
fi
script="\$src/deploy/segqueue14-deploy.sh"
[ -f "\$script" ] || { echo "[sq14] no \$script on the server"; exit 1; }
cd "\$home" && SQ14_USER="\$SQ14_USER" bash "\$script" ${args}
EOF
    local b64
    b64=$(base64 -w0 < remote.sh)
    printf '%s\n' "$SSHPASS" | sshpass -e ssh "${SSH_OPTS[@]}" -o UserKnownHostsFile="$KH" \
        -p "${PORT:-22}" "${USERNAME}@${HOST}" \
        "sudo -S -p '' bash -c 'echo $b64 | base64 -d | bash'"
}

# Write stdin to a file in the deploy user's home on janus (mode 600, no sudo, nothing
# in argv): how the repository password reaches janus.
put_on_janus() {   # put_on_janus <file name in home>
    sshpass -e ssh "${SSH_OPTS[@]}" -o UserKnownHostsFile="$KH" -p "${PORT:-22}" \
        "${USERNAME}@${HOST}" "umask 077 && cat > ~/$1"
}

# Run a script on the backup server as SSH_USERNAME (no sudo).
on_backup() {   # stdin: the script
    local b64
    b64=$(base64 -w0)
    sshpass -e ssh "${SSH_OPTS[@]}" -o UserKnownHostsFile="$KH_BACKUP" -p "$SFTP_PORT" \
        "${USERNAME}@${HOST}" "echo $b64 | base64 -d | sh"
}

install() {
    [ -n "${SFTP_PORT:-}" ] || die "secret SSH_PORT_SFTP_SERVER is not set: the backup server's SSH port"
    [ -n "${RESTIC_PASSWORD_SECRET:-}" ] || die "secret BACKUP_RESTIC_PASSWORD is not set. Create it (a long random password, also kept in your password manager): without it the backups could not be read once janus is gone. Nothing was installed."

    say "1/4 janus: restic, the backup SSH key, the repository password"
    printf '%s' "$RESTIC_PASSWORD_SECRET" | put_on_janus .segqueue-backup-restic-password.new
    on_janus backup-prepare | tee prepare.txt
    local pubkey
    pubkey=$(sed -n 's/^PUBKEY //p' prepare.txt | tail -1)
    [[ "$pubkey" =~ ^ssh-ed25519\ [A-Za-z0-9+/=]+\ [^\ ]+$ ]] || die "janus did not report its backup key"

    say "2/4 the backup server's host key"
    if [ -n "${SFTP_KNOWN_HOSTS:-}" ]; then
        printf '%s\n' "$SFTP_KNOWN_HOSTS" > "$KH_BACKUP"
    else
        ssh-keyscan -p "$SFTP_PORT" "$HOST" 2>/dev/null | grep -v '^#' > "$KH_BACKUP" || true
        echo ":warning: no SSH_KNOWN_HOSTS_SFTP_SERVER secret; trusted the backup server's host key as offered to the runner (janus pins the same key)." >> "$GITHUB_STEP_SUMMARY"
    fi
    chmod 600 "$KH_BACKUP"
    [ -s "$KH_BACKUP" ] || die "could not read the backup server's host key on port SSH_PORT_SFTP_SERVER"
    ssh-keygen -lf "$KH_BACKUP" | sed 's/^/[backup]   host key: /'

    say "3/4 backup server: authorise janus's backup key (SFTP only where the server allows)"
    on_backup <<EOF
set -eu
key='$pubkey'
body=\$(echo "\$key" | cut -d' ' -f2)
comment=\$(echo "\$key" | cut -d' ' -f3)
umask 077
mkdir -p "\$HOME/.ssh"
touch "\$HOME/.ssh/authorized_keys"
sftp=''
for p in /usr/lib/openssh/sftp-server /usr/libexec/openssh/sftp-server /usr/lib/ssh/sftp-server /usr/libexec/sftp-server /usr/lib/sftp-server; do
  if [ -x "\$p" ]; then sftp=\$p; break; fi
done
if [ -n "\$sftp" ]; then opts="restrict,command=\"\$sftp\""; else opts="restrict"; fi
# Replace any earlier line for this key (same key body, or the same comment).
awk -v b="\$body" -v c="\$comment" '{ keep=1; for (i=1;i<=NF;i++) { if (\$i==b) keep=0 } if (\$NF==c) keep=0; if (keep) print }' \
  "\$HOME/.ssh/authorized_keys" > "\$HOME/.ssh/authorized_keys.new"
echo "\$opts \$key" >> "\$HOME/.ssh/authorized_keys.new"
mv "\$HOME/.ssh/authorized_keys.new" "\$HOME/.ssh/authorized_keys"
chmod 600 "\$HOME/.ssh/authorized_keys"
if [ -n "\$sftp" ]; then echo "[backup]   key authorised, limited to SFTP (\$sftp)"; else echo "[backup]   key authorised with 'restrict' (no shell forwarding/pty); no sftp-server binary found to limit it to SFTP only"; fi
EOF

    say "4/4 janus: find the route to the backup server, pin its key, repository, timers, first backup"
    local routes=()
    [ -n "${LAN_ADDRESS:-}" ] && routes+=(--route "$LAN_ADDRESS")
    routes+=(--route "$HOST:$SFTP_PORT")
    on_janus backup-finish --user "$USERNAME" "${routes[@]}" \
        --hostkeys-b64 "$(base64 -w0 < "$KH_BACKUP")"
}

case "$STEP" in
    backup-install) install ;;
    backup-status) on_janus backup-status ;;
    backup-restore-test) on_janus backup-restore-test ;;
    backup-off) on_janus backup-off ;;
    *) die "unknown backup step $STEP" ;;
esac
