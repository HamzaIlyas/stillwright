#!/usr/bin/env sh
# Puts the `sw` binary on PATH (Linux and macOS; Windows users run the PowerShell line in
# the README). Uses an existing `sw` when found; otherwise downloads the installer for the
# pinned release below, so a run never executes whatever "latest" happens to be.
set -eu
REPO="HamzaIlyas/stillwright"
VERSION="0.1.5"
if command -v sw >/dev/null 2>&1; then
  echo "sw already installed: $(command -v sw)"
  exit 0
fi
if [ "${SW_FROM_SOURCE:-}" = "1" ] && command -v cargo >/dev/null 2>&1; then
  cargo install --git "https://github.com/$REPO" --tag "v$VERSION" --locked
  exit 0
fi
URL="https://github.com/$REPO/releases/download/v$VERSION/stillwright-installer.sh"
TMP="$(mktemp)"
trap 'rm -f "$TMP"' EXIT
echo "Downloading sw v$VERSION installer..."
if ! curl --proto '=https' --tlsv1.2 -fsSL "$URL" -o "$TMP"; then
  echo "download failed: $URL" >&2
  exit 1
fi
sh "$TMP"
command -v sw >/dev/null 2>&1 || echo "Installed. Open a new shell so 'sw' is on PATH."
