#!/bin/bash
# Copy Slicer.app out of a downloaded .dmg and export SLICER for later steps.
#   install-slicer-macos.sh <dmg> <dest-dir>
set -euo pipefail
dmg=$1
dest=$2
mount=$(mktemp -d)
# `yes` answers the licence prompt some Slicer images show on attach.
(yes || true) | hdiutil attach "$dmg" -nobrowse -readonly -mountpoint "$mount" >/dev/null
app=$(find "$mount" -maxdepth 1 -name '*.app' | head -n 1)
test -n "$app" || { echo "no .app in $dmg"; ls -la "$mount"; exit 1; }
mkdir -p "$dest"
cp -R "$app" "$dest/"
hdiutil detach "$mount" >/dev/null
# A downloaded app carries com.apple.quarantine; Gatekeeper would stop it.
xattr -cr "$dest/$(basename "$app")" || true
slicer="$dest/$(basename "$app")/Contents/MacOS/Slicer"
"$slicer" --version || true
echo "SLICER=$slicer" >> "$GITHUB_ENV"
