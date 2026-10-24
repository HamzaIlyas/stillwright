#!/usr/bin/env sh
# Puts the `sw` binary on PATH. Uses an existing one when found; otherwise downloads the
# release for this OS/CPU from GitHub, checks its SHA-256, and installs it for the user.
set -eu
REPO="HamzaIlyas/stillwright"
if command -v sw >/dev/null 2>&1; then
  echo "sw already installed: $(command -v sw)"
  exit 0
fi
if [ "${SW_FROM_SOURCE:-}" = "1" ] && command -v cargo >/dev/null 2>&1; then
  cargo install stillwright --locked
  exit 0
fi
echo "Installing sw from the latest GitHub release of $REPO..."
curl --proto '=https' --tlsv1.2 -LsSf "https://github.com/$REPO/releases/latest/download/stillwright-installer.sh" | sh
echo "Done. Open a new shell if 'sw' is not found yet."
