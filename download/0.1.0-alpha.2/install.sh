#!/bin/sh
set -eu

VERSION=0.1.0-alpha.2
ROOT=https://lennertvhoy.github.io/StatePort-Site
RELEASE="$ROOT/download/$VERSION"
INDEX_SHA=9cd33eb7d93b5c70bec9f260824ce45877323ec85993a8b2824411e9b2e43000
INSTALLER_SHA=beea6a856e7459c103c1dc59afd4b6b34b67d5df2ea5110d2b8e05ebc404e1f0
BUNDLE_SHA=31ab4e44f276c370607ab6c90c6af224d96329a9283c6fa60a616d05addf7bbb
COSIGN_SHA=f7622ed3cf22e55e1ae6377c080979ff77a22da9981c11df222a2e444991e7cf
KEY_ID=stateport-alpha-private-2026-08
KEY_FP=sha256:23c965bfec8e56f3075ae3bdcf4b08ef28060522d89261a31fa7d361e05553d8

fail() { printf 'StatePort install: %s\n' "$*" >&2; exit 1; }
[ "$(uname -s)" = Linux ] || fail 'Linux is required.'
case "$(uname -m)" in x86_64|amd64) ;; *) fail 'This candidate is AMD64 only.' ;; esac
[ "$(id -u)" -ne 0 ] || fail 'Run as your normal user, not root.'
. /etc/os-release 2>/dev/null || fail 'Cannot read /etc/os-release.'
[ "${ID:-}" = ubuntu ] && [ "${VERSION_ID:-}" = 24.04 ] || fail 'The signed alpha.2 target is Ubuntu 24.04. Other distributions need the next capability-based signed target; this script will not bypass the release contract.'
command -v curl >/dev/null && command -v sha256sum >/dev/null || fail 'curl and sha256sum are required.'

missing=0
command -v python3 >/dev/null || missing=1
command -v podman >/dev/null || missing=1
python3 -c 'import sys; raise SystemExit(sys.version_info < (3,12))' 2>/dev/null || missing=1
if [ "$missing" -eq 1 ]; then
  printf 'Install required Ubuntu packages now? [y/N] ' >/dev/tty
  IFS= read -r answer </dev/tty || answer=
  case "$answer" in y|Y|yes|YES)
    command -v sudo >/dev/null || fail 'sudo is required to install prerequisites.'
    sudo env DEBIAN_FRONTEND=noninteractive apt-get update
    sudo env DEBIAN_FRONTEND=noninteractive apt-get install -y python3 python3-venv podman uidmap slirp4netns fuse-overlayfs dbus-user-session
    ;; *) fail 'Prerequisite installation declined.' ;; esac
fi

umask 077
tmp=$(mktemp -d "${TMPDIR:-/tmp}/stateport-install.XXXXXX") || fail 'Cannot create a private temporary directory.'
trap 'rm -rf "$tmp"' EXIT HUP INT TERM
get() { curl -fsSL --proto '=https' --tlsv1.2 --retry 3 -o "$2" "$1"; }
check() { printf '%s  %s\n' "$1" "$2" | sha256sum -c --status || fail "Checksum failed: $2"; }

printf 'Downloading and verifying StatePort %s...\n' "$VERSION"
get "$RELEASE/stateport-installer" "$tmp/installer"; check "$INSTALLER_SHA" "$tmp/installer"
get "$RELEASE/release-index.sigstore.json" "$tmp/release-index.sigstore.json"; check "$BUNDLE_SHA" "$tmp/release-index.sigstore.json"
get "$ROOT/assets/stateport-alpha-release.pub" "$tmp/release.pub"
get "https://github.com/sigstore/cosign/releases/download/v3.1.2/cosign-linux-amd64" "$tmp/cosign"; check "$COSIGN_SHA" "$tmp/cosign"
chmod 700 "$tmp/installer" "$tmp/cosign"

if [ "${STATEPORT_INSTALL_YES:-0}" != 1 ]; then
  printf 'Install the signed alpha candidate for this user? Type install: ' >/dev/tty
  IFS= read -r answer </dev/tty || answer=
  [ "$answer" = install ] || fail 'Installation not confirmed.'
fi

python3 "$tmp/installer" \
  --release-index "$RELEASE/release-index.json" --release-index-sha256 "$INDEX_SHA" \
  --bundle-root "$tmp" --trust-public-key "$tmp/release.pub" --trust-key-id "$KEY_ID" \
  --trust-key-fingerprint "$KEY_FP" --updater-wheel "$RELEASE/stateport-updater" \
  --compose "$RELEASE/compose.yaml" --source-archive "$RELEASE/stateport-source.tar" \
  --release-notes "$RELEASE/release-notes.md" --known-limitations "$RELEASE/known-limitations.md" \
  --channel alpha --cosign "$tmp/cosign" --installer-path "$tmp/installer" --yes
