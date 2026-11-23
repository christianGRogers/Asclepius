#!/usr/bin/env bash
# Reach janus (the main server) from a GitHub runner through the gateway server.
#
# Janus's SSH port is closed to the outside (since 2026-11-20). The runner logs in to the
# gateway, and the gateway forwards the connection to janus's LAN address (`ssh -W`, as
# a ProxyCommand). Both hops use password auth through sshpass: the gateway hop runs its
# own `sshpass -e` inside the ProxyCommand, because one sshpass answers one prompt. The
# final session's stdin still reaches the remote command, so `sudo -S` works as before.
#
#   janus-ssh.sh trust        pin both host keys, write the ssh config, log in through
#                             both hops once; fails naming the hop that failed
#   janus-ssh.sh run CMD...   run CMD on janus (stdin passed through), after `trust`
#   janus-ssh.sh proxy ENV H P   the ProxyCommand (internal)
#
# Environment (from secrets; never printed):
#   USERNAME, SSHPASS         SSH_USERNAME, SSH_PASSWORD: the same on both servers
#   GATEWAY_HOST              optional GATEWAY_HOST secret; empty = HOST (SSH_HOST)
#   GATEWAY_PORT              the gateway's SSH port (required)
#   MAIN_SERVER_LAN           janus's address as seen from the gateway (required)
#   PORT                      janus's sshd port on that address (SSH_PORT; default 22)
#   KNOWN                     optional SSH_KNOWN_HOSTS: janus's known_hosts line(s), under
#                             any host name (the old public entry works: same keys)
#   KNOWN_GATEWAY             optional SSH_KNOWN_HOSTS_GATEWAY: the gateway's line(s)
#   JANUS_SSH_DIR             where the files go (default ~/.ssh)
#
# Without KNOWN_GATEWAY the gateway's key is taken from ssh-keyscan; without KNOWN janus's
# key is the one it offers through the (already verified) gateway. Either way every later
# connection checks both keys strictly (StrictHostKeyChecking=yes).
set -euo pipefail

DIR="${JANUS_SSH_DIR:-$HOME/.ssh}"
CONF="$DIR/janus.conf"
GW_ENV="$DIR/janus-gateway.env"
KH_GW="$DIR/known_hosts_gateway"
KH_JANUS="$DIR/known_hosts_janus"
ALIAS=janus
SELF="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/$(basename "${BASH_SOURCE[0]}")"
HOP_OPTS=(-o BatchMode=no -o ConnectTimeout=20 -o StrictHostKeyChecking=yes
          -o GlobalKnownHostsFile=/dev/null -o CheckHostIP=no -o UpdateHostKeys=no
          -o ServerAliveInterval=30)

say() { printf '[janus-ssh] %s\n' "$*"; }
die() { printf '::error::%s\n' "$*" >&2; exit 1; }
summary() { [ -n "${GITHUB_STEP_SUMMARY:-}" ] && printf '%s\n' "$*" >> "$GITHUB_STEP_SUMMARY" || true; }

# The gateway hop. Its own sshpass: the outer one has already answered janus's prompt.
gateway_ssh() {   # gateway_ssh CMD: run CMD on the gateway
    # shellcheck disable=SC1090
    . "$GW_ENV"
    SSHPASS="${JANUS_SSHPASS:-${SSHPASS:-}}" sshpass -e ssh -F none "${HOP_OPTS[@]}" \
        -o UserKnownHostsFile="$KH_GW" -p "$GW_PORT" "$GW_USER@$GW_HOST" "$@"
}

proxy() {   # proxy <env file> <host> <port>
    GW_ENV="$1"
    # shellcheck disable=SC1090
    . "$GW_ENV"
    export SSHPASS="${JANUS_SSHPASS:-${SSHPASS:-}}"
    # -q: the gateway's diagnostics would name addresses; `trust` reports per hop instead.
    # 2>/dev/null: ssh does not wait for its ProxyCommand when the session ends (it sends
    # SIGHUP and exits), so this hop can outlive the finished remote command. If it held
    # the session's stderr, as it would by inheritance, a caller reading the output to
    # EOF (`| tee`, captured output) would hang after the command had already returned
    # (#352/#353). Its stdin/stdout are ssh's own pipe, which nothing else reads.
    exec sshpass -e ssh -q -F none "${HOP_OPTS[@]}" -o UserKnownHostsFile="$KH_GW" \
        -p "$GW_PORT" -W "$2:$3" "$GW_USER@$GW_HOST" 2>/dev/null
}

# Mask what ssh may print in place of a secret (the gateway's resolved addresses).
mask_addresses() {
    [ "${GITHUB_ACTIONS:-}" = true ] || return 0
    local ip
    for ip in $(getent ahosts "$1" 2>/dev/null | awk '{print $1}' | sort -u); do
        [ "$ip" = "$1" ] || echo "::add-mask::$ip"
    done
}

why() {   # sshpass/ssh exit code -> words, no addresses
    case "$1" in
        5) echo "the password was refused" ;;
        6) echo "the host key is not known" ;;
        255) echo "no connection, or the host key did not match" ;;
        *) echo "exit $1" ;;
    esac
}

trust() {
    local gw_host="${GATEWAY_HOST:-${HOST:-}}" port="${PORT:-}"
    port="${port:-22}"
    [ -n "${USERNAME:-}" ] || die "secret SSH_USERNAME is not set"
    [ -n "${SSHPASS:-}" ] || die "secret SSH_PASSWORD is not set"
    [ -n "$gw_host" ] || die "gateway hop: neither GATEWAY_HOST nor SSH_HOST is set"
    [[ "$gw_host" =~ ^[A-Za-z0-9.:-]+$ ]] || die "gateway hop: GATEWAY_HOST (or SSH_HOST) is not a host name or address"
    [[ "${GATEWAY_PORT:-}" =~ ^[0-9]{1,5}$ ]] || die "gateway hop: secret GATEWAY_PORT is not set, or not a port number"
    [[ "${MAIN_SERVER_LAN:-}" =~ ^[A-Za-z0-9.:-]+$ ]] || die "main-server hop: secret MAIN_SERVER_LAN is not set, or not an address"
    [[ "$port" =~ ^[0-9]{1,5}$ ]] || die "main-server hop: secret SSH_PORT is not a port number"
    [[ "$USERNAME" =~ ^[A-Za-z0-9._-]+$ ]] || die "secret SSH_USERNAME holds characters an ssh config cannot take"
    mask_addresses "$gw_host"

    mkdir -p "$DIR" && chmod 700 "$DIR"
    umask 077
    printf 'GW_HOST=%q\nGW_PORT=%q\nGW_USER=%q\nKH_GW=%q\n' \
        "$gw_host" "$GATEWAY_PORT" "$USERNAME" "$KH_GW" > "$GW_ENV"
    cat > "$CONF" <<EOF
Host $ALIAS
  HostName $MAIN_SERVER_LAN
  Port $port
  User $USERNAME
  HostKeyAlias $ALIAS
  UserKnownHostsFile $KH_JANUS
  GlobalKnownHostsFile /dev/null
  StrictHostKeyChecking yes
  CheckHostIP no
  UpdateHostKeys no
  BatchMode no
  ConnectTimeout 20
  ServerAliveInterval 30
  ProxyCommand bash "$SELF" proxy "$GW_ENV" %h %p
EOF

    say "1/4 gateway hop: host key"
    if [ -n "${KNOWN_GATEWAY:-}" ]; then
        printf '%s\n' "$KNOWN_GATEWAY" > "$KH_GW"
        say "    pinned from SSH_KNOWN_HOSTS_GATEWAY"
    else
        ssh-keyscan -T 15 -p "$GATEWAY_PORT" -H "$gw_host" 2>/dev/null | grep -v '^#' > "$KH_GW" || true
        summary ":warning: no SSH_KNOWN_HOSTS_GATEWAY secret; accepted the gateway's host key as offered."
    fi
    [ -s "$KH_GW" ] || die "gateway hop: no host key from the gateway (GATEWAY_HOST or SSH_HOST, port GATEWAY_PORT): is that port open to GitHub's runners?"
    ssh-keygen -lf "$KH_GW" 2>/dev/null | awk '{print "[janus-ssh]     gateway key " $1 " " $2 " " $NF}' \
        || die "gateway hop: the gateway's known_hosts holds no valid key (check SSH_KNOWN_HOSTS_GATEWAY)"

    say "2/4 gateway hop: log in"
    local rc=0
    gateway_ssh true </dev/null >/dev/null 2>&1 || rc=$?
    [ "$rc" -eq 0 ] || die "gateway hop: could not log in to the gateway as SSH_USERNAME: $(why "$rc")"

    say "3/4 main-server hop: host key (through the gateway)"
    if [ -n "${KNOWN:-}" ]; then
        # The same keys janus offered on its old public port: re-file them under the alias.
        printf '%s\n' "$KNOWN" | awk -v a="$ALIAS" '!/^[[:space:]]*(#|$)/ && $1 !~ /^@/ && NF >= 3 {print a, $2, $3}' > "$KH_JANUS"
        [ -s "$KH_JANUS" ] || die "main-server hop: SSH_KNOWN_HOSTS is set but holds no known_hosts line"
        say "    pinned from SSH_KNOWN_HOSTS"
    else
        : > "$KH_JANUS"
        # Host key exchange only: accept-new records the key, then every login method is
        # off, so this never authenticates.
        JANUS_SSHPASS="$SSHPASS" ssh -F "$CONF" -o StrictHostKeyChecking=accept-new -o BatchMode=yes \
            -o PubkeyAuthentication=no -o PasswordAuthentication=no -o KbdInteractiveAuthentication=no \
            -o GSSAPIAuthentication=no -o HostbasedAuthentication=no -o IdentityAgent=none \
            "$ALIAS" true </dev/null >/dev/null 2>&1 || true
        summary ":warning: no SSH_KNOWN_HOSTS secret; accepted janus's host key as offered through the gateway."
    fi
    [ -s "$KH_JANUS" ] || die "main-server hop: no host key from janus at MAIN_SERVER_LAN, port SSH_PORT, through the gateway (the gateway refused to forward, or nothing listens there)"
    ssh-keygen -lf "$KH_JANUS" 2>/dev/null | awk '{print "[janus-ssh]     janus key " $1 " " $2 " " $NF}' \
        || die "main-server hop: janus's known_hosts holds no valid key (check SSH_KNOWN_HOSTS)"

    say "4/4 main-server hop: log in through the gateway"
    rc=0
    run true </dev/null >/dev/null 2>&1 || rc=$?
    [ "$rc" -eq 0 ] || die "main-server hop: could not log in to janus through the gateway: $(why "$rc")"
    say "both hops verified"
}

run() {
    [ -f "$CONF" ] || die "janus-ssh.sh run: no $CONF; run 'janus-ssh.sh trust' first"
    [ -n "${SSHPASS:-}" ] || die "SSHPASS (secret SSH_PASSWORD) is not set"
    local rc=0
    JANUS_SSHPASS="$SSHPASS" sshpass -e ssh -F "$CONF" "$ALIAS" "$@" || rc=$?
    if [ "$rc" -eq 255 ]; then
        printf '::error::ssh to janus through the gateway failed (exit 255); the trust step checks each hop\n' >&2
    fi
    return "$rc"
}

case "${1:-}" in
    trust) trust ;;
    run) shift; run "$@" ;;
    proxy) shift; proxy "$@" ;;
    *) die "usage: janus-ssh.sh trust | run CMD..." ;;
esac
