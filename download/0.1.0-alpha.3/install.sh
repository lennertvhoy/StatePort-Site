#!/bin/sh
# StatePort v0.1.0-alpha.3 capability-gated one-command bootstrap.
# The signed installer performs evaluate_linux_host against the portable
# linux-amd64-rootless-podman-quadlet contract and records the support tier.
set -eu

VERSION="0.1.0-alpha.3"
SITE_ROOT="https://lennertvhoy.github.io/StatePort-Site"
RELEASE_ROOT="$SITE_ROOT/download/$VERSION"
CAPABILITY_TARGET="linux-amd64-rootless-podman-quadlet"
COSIGN_VERSION="v3.1.2"
COSIGN_URL="https://github.com/sigstore/cosign/releases/download/$COSIGN_VERSION/cosign-linux-amd64"

INSTALLER_SHA256="33874d373c8949209f81895b4481747fb97f2ab570ddd26e76258c4a2c02e6ab"
RELEASE_INDEX_SHA256="d02709a250369b96c7bf5c39659d9080ff53d0cf0e20d391222fe5c1b0d4ae93"
RELEASE_BUNDLE_SHA256="e4fb2c0f274ed88e34a5904c2d85feb3dcc231a7a5d794072fff158a29178208"
COSIGN_SHA256="f7622ed3cf22e55e1ae6377c080979ff77a22da9981c11df222a2e444991e7cf"
TRUST_KEY_ID="stateport-alpha-private-2026-08"
TRUST_KEY_FINGERPRINT="sha256:3dca6219e41310c6a95a8189669aacad3198e6c84489946406b8f986e1f4211a"

fail() { printf 'StatePort install: %s\n' "$*" >&2; exit 1; }

[ "$(uname -s 2>/dev/null || true)" = "Linux" ] || fail "Linux is required."
case "$(uname -m 2>/dev/null || true)" in
  x86_64|amd64) ;;
  *) fail "v$VERSION currently ships only for Linux AMD64." ;;
esac
[ "$(id -u)" -ne 0 ] || fail "Run this as your normal user, not as root."
command -v curl >/dev/null 2>&1 || fail "curl is required to start the bootstrap."
command -v sha256sum >/dev/null 2>&1 || fail "sha256sum is required (normally provided by coreutils)."
command -v python3 >/dev/null 2>&1 || fail "Python 3.12 or newer is required."
python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 12) else 1)' \
  >/dev/null 2>&1 || fail "Python 3.12 or newer is required."
command -v podman >/dev/null 2>&1 || fail "rootless Podman is required."
command -v systemctl >/dev/null 2>&1 || fail "systemd user services are required."
[ -r /sys/fs/cgroup/cgroup.controllers ] || fail "cgroup v2 is required."

umask 077
tmp=$(mktemp -d "${TMPDIR:-/tmp}/stateport-install.XXXXXX") || fail "Cannot create a private temporary directory."
trap 'rm -rf "$tmp"' EXIT HUP INT TERM
get() { curl -fsSL --proto '=https' --tlsv1.2 --retry 3 -o "$2" "$1"; }
check() { printf '%s  %s\n' "$1" "$2" | sha256sum -c --status || fail "Checksum failed: $2"; }

printf 'Downloading and verifying StatePort %s for %s...\n' "$VERSION" "$CAPABILITY_TARGET"
get "$RELEASE_ROOT/stateport-installer" "$tmp/installer"
check "$INSTALLER_SHA256" "$tmp/installer"
get "$RELEASE_ROOT/release-index.json" "$tmp/release-index.json"
check "$RELEASE_INDEX_SHA256" "$tmp/release-index.json"
get "$RELEASE_ROOT/release-index.sigstore.json" "$tmp/release-index.sigstore.json"
check "$RELEASE_BUNDLE_SHA256" "$tmp/release-index.sigstore.json"
get "$RELEASE_ROOT/stateport-alpha-2026-08-cosign.pub" "$tmp/release.pub"
get "$COSIGN_URL" "$tmp/cosign"
check "$COSIGN_SHA256" "$tmp/cosign"
chmod 700 "$tmp/installer" "$tmp/cosign"

if [ "${STATEPORT_INSTALL_YES:-0}" != 1 ]; then
  printf 'Install the signed alpha candidate for this user? Type install: ' >/dev/tty
  IFS= read -r answer </dev/tty || answer=
  [ "$answer" = install ] || fail "Installation not confirmed."
fi

# The signed artifact performs evaluate_linux_host and refuses any host that
# does not satisfy the complete portable target contract.
python3 "$tmp/installer" \
  --release-index "$RELEASE_ROOT/release-index.json" \
  --release-index-sha256 "$RELEASE_INDEX_SHA256" \
  --bundle-root "$tmp" \
  --trust-public-key "$tmp/release.pub" \
  --trust-key-id "$TRUST_KEY_ID" \
  --trust-key-fingerprint "$TRUST_KEY_FINGERPRINT" \
  --updater-wheel "$RELEASE_ROOT/stateport-updater" \
  --compose "$RELEASE_ROOT/compose.yaml" \
  --source-archive "$RELEASE_ROOT/stateport-source.tar" \
  --release-notes "$RELEASE_ROOT/release-notes.md" \
  --known-limitations "$RELEASE_ROOT/known-limitations.md" \
  --channel alpha \
  --cosign "$tmp/cosign" \
  --installer-path "$tmp/installer" \
  --yes
