#!/bin/bash
# TotalSegmentator's own venv for benchmark-seed (D43, issues #286 and #290). Run as
# the deploy user by segqueue14-deploy.sh; it writes only inside VENV.
#
#   bash totalseg-venv.sh check   PY VENV VERSION   # 0 if VENV is usable as it is
#   bash totalseg-venv.sh install PY VENV VERSION   # (re)create VENV, install TotalSegmentator
#
# PY is the live venv's Python, used only to create VENV; nothing is installed into
# its own venv. Janus has no python3.X-venv, so `PY -m venv` cannot seed pip
# (no ensurepip). The routes, first that works:
#   1. `PY -m venv --without-pip`, then PY's pip (>= 22.3, `--python`) installs pip into VENV
#   2. `PY -m venv` (where ensurepip exists)
#   3. uv or virtualenv, only if already on PATH
# A VENV that fails `check` (half made, no pip, wrong or no TotalSegmentator) is
# recreated with --clear.
set -uo pipefail

say() { printf '[sq14] %s\n' "$*"; }
die() { printf '[sq14] ERROR: %s\n' "$*" >&2; exit 1; }

[ $# -eq 4 ] || die "usage: totalseg-venv.sh check|install PY VENV VERSION"
STEP="$1" PY="$2" VENV="$3" VERSION="$4"
case "$VENV" in
    /*/*) ;;
    *) die "refusing venv path '$VENV' (absolute, at least two levels deep)" ;;
esac
[ "$VENV" != "${HOME%/}" ] || die "refusing venv path '$VENV' (the home directory)"
VPY="$VENV/bin/python"

healthy() {
    [ -x "$VPY" ] && [ -x "$VENV/bin/TotalSegmentator" ] || return 1
    "$VPY" -m pip --version >/dev/null 2>&1 || return 1
    "$VPY" - "$VERSION" >/dev/null 2>&1 <<'PYEOF'
import sys
from importlib.metadata import version
sys.exit(version('TotalSegmentator') != sys.argv[1])
PYEOF
}

has_pip() { [ -x "$VPY" ] && "$VPY" -m pip --version >/dev/null 2>&1; }

make_venv() {
    say "creating $VENV (venv without ensurepip, pip from $PY)"
    if "$PY" -m venv --clear --without-pip "$VENV" \
        && "$PY" -m pip --python "$VPY" install -q pip && has_pip; then
        return 0
    fi
    say "that did not work; trying '$PY -m venv'"
    if "$PY" -m venv --clear "$VENV" && has_pip; then
        return 0
    fi
    if command -v uv >/dev/null; then
        say "trying uv venv"
        if uv venv -q --clear --seed --python "$PY" "$VENV" && has_pip; then
            return 0
        fi
    fi
    if command -v virtualenv >/dev/null; then
        say "trying virtualenv"
        if virtualenv -q --clear -p "$PY" "$VENV" && has_pip; then
            return 0
        fi
    fi
    local pyver
    pyver=$("$PY" -c 'import sys; print("%d.%d" % sys.version_info[:2])' 2>/dev/null || echo 3)
    die "cannot make a venv with pip at $VENV: the lead runs 'sudo apt install python${pyver}-venv' on janus and re-runs benchmark-seed --apply, or makes the seed elsewhere and uploads it with 'segqueue14-benchmark seed --seed-file' (DEPLOY.md, D43)"
}

case "$STEP" in
    check) healthy ;;
    install)
        if healthy; then
            say "TotalSegmentator $VERSION is already installed at $VENV"
            exit 0
        fi
        [ -e "$VENV" ] && say "$VENV is incomplete; recreating it"
        make_venv
        "$VPY" -m pip install -q --upgrade pip || die "could not upgrade pip in $VENV"
        "$VPY" -m pip install -q \
            --extra-index-url https://download.pytorch.org/whl/cpu "TotalSegmentator==$VERSION" \
            || die "could not install TotalSegmentator $VERSION; see DEPLOY.md (D43) for the seed made elsewhere"
        healthy || die "TotalSegmentator $VERSION installed but $VENV still fails its check"
        say "TotalSegmentator $VERSION installed at $VENV"
        ;;
    *) die "unknown step '$STEP' (check or install)" ;;
esac
