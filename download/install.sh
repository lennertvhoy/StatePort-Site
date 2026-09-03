#!/bin/sh
# StatePort v0.1.0-alpha.12 Windows 11 + WSL2 + Ubuntu 24.04 bootstrap.
set -eu
STATEPORT_VERSION="0.1.0-alpha.12"
RELEASE_ROOT="https://lennertvhoy.github.io/StatePort-Site/download/0.1.0-alpha.12"
PROBE_ROOT="https://lennertvhoy.github.io/StatePort-Site/download/alpha12-manifests"
TARGET="wsl2-ubuntu2404-linux-amd64-rootless-podman-quadlet"
STATE_ROOT="${STATEPORT_STATE_ROOT:-$HOME/.local/state/stateport-install}"
RECEIPT="/var/lib/stateport-provisioning/receipts/execution-host-provisioning-receipt.json"
COSIGN_URL="https://github.com/sigstore/cosign/releases/download/v3.1.3/cosign-linux-amd64"
fail() { printf "StatePort install: %s\n" "$*" >&2; exit 1; }
mode=install
case "${1-}" in --transport-probe) mode=probe; shift ;; --materialization-preflight) mode=materialization-preflight; shift ;; "") ;; *) fail "Usage: $0 [--transport-probe|--materialization-preflight]" ;; esac
[ "$#" -eq 0 ] || fail "Usage: $0 [--transport-probe|--materialization-preflight]"
[ "$(id -u)" -ne 0 ] || fail "Run this as your normal WSL user, not root."
release=$(uname -r 2>/dev/null || true)
case "$(printf "%s" "$release" | tr "[:upper:]" "[:lower:]")" in *microsoft*wsl2*) ;; *) fail "WSL2 is required; WSL1 and native Linux are not this release target." ;; esac
[ "$(uname -m 2>/dev/null || true)" = "x86_64" ] || fail "WSL2 AMD64 is required."
. /etc/os-release 2>/dev/null || fail "Cannot read /etc/os-release."
[ "${ID:-}" = ubuntu ] && [ "${VERSION_ID:-}" = 24.04 ] || fail "Ubuntu 24.04 for WSL is required."
[ "$(ps -p 1 -o comm= 2>/dev/null | tr -d " ")" = systemd ] || fail "Enable systemd in WSL, run wsl --shutdown in PowerShell, reopen Ubuntu, then retry."
command -v powershell.exe >/dev/null 2>&1 || fail "Windows interoperability is required."
win_build=$(powershell.exe -NoProfile -NonInteractive -Command "[int](Get-CimInstance Win32_OperatingSystem).BuildNumber" 2>/dev/null | tr -d "\r\n ")
case "$win_build" in *[!0-9]*|"") fail "Cannot verify the Windows build." ;; esac
[ "$win_build" -ge 22000 ] || fail "Windows 11 build 22000 or newer is required."
get() {
  url=$1; destination=$2; label=$3; partial="$destination.part"; attempt=1
  while [ "$attempt" -le 4 ]; do
    rm -f "$partial"
    if curl -fsSL --proto "=https" --tlsv1.2 --connect-timeout 20 --max-time 600 -o "$partial" "$url"; then mv "$partial" "$destination"; return 0; fi
    printf "StatePort download retry: %s (attempt %s/4)\n" "$label" "$attempt" >&2
    attempt=$((attempt + 1)); [ "$attempt" -gt 4 ] || sleep 1
  done
  rm -f "$partial"
  fail "Download failed after 4 attempts: $label ($url)"
}
check() { printf "%s  %s\n" "$1" "$2" | sha256sum -c --status || fail "Checksum failed: $2"; }
ensure_root_helper_parent() {
  case "$1" in /) prefix= ;; /*) prefix=${1%/} ;; *) fail "Root-helper prefix must be absolute." ;; esac
  owner=$2; group=$3; action=$4
  for path in "$prefix/usr" "$prefix/usr/local"; do
    [ -d "$path" ] && [ ! -L "$path" ] || fail "Root-helper parent is unavailable or symlinked: $path"
    metadata=$(stat -c "%u:%g:%a" -- "$path") || fail "Cannot inspect root-helper parent: $path"
    case "$metadata" in "$owner:$group:755"|"$owner:$group:555") ;; *) fail "Root-helper parent has unsafe ownership or mode: $path ($metadata)" ;; esac
  done
  parent="$prefix/usr/local/libexec"
  [ ! -L "$parent" ] || fail "Root-helper directory is symlinked: $parent"
  if [ ! -e "$parent" ]; then
    case "$action" in sudo) sudo -n install -d -o "$owner" -g "$group" -m 0755 -- "$parent" ;; local) install -d -m 0755 -- "$parent" ;; check) return 0 ;; *) fail "Unknown root-helper parent action." ;; esac
  fi
  [ -d "$parent" ] && [ ! -L "$parent" ] || fail "Root-helper directory is unavailable or symlinked: $parent"
  metadata=$(stat -c "%u:%g:%a" -- "$parent") || fail "Cannot inspect root-helper directory: $parent"
  [ "$metadata" = "$owner:$group:755" ] || fail "Root-helper directory has unsafe ownership or mode: $parent ($metadata)"
}
if [ "$mode" = probe ]; then
  command -v curl >/dev/null 2>&1 || fail "curl is required for the transport probe."
  command -v sha256sum >/dev/null 2>&1 || fail "sha256sum is required for the transport probe."
  umask 077
  tmp=$(mktemp -d "${TMPDIR:-/tmp}/stateport-alpha12-probe.XXXXXX") || fail "Cannot create a private probe directory."
  trap 'rm -rf "$tmp"' EXIT
  trap 'exit 129' HUP
  trap 'exit 130' INT
  trap 'exit 143' TERM
  get "$PROBE_ROOT/stateport-api.json" "$tmp/stateport-api.manifest.json" "image manifest: stateport-api"
  check "01de186713c69817c1c09e5a36d7f94a8a24031efaf0105153f86372525c9578" "$tmp/stateport-api.manifest.json"
  get "$PROBE_ROOT/stateport-dev-workspace.json" "$tmp/stateport-dev-workspace.manifest.json" "image manifest: stateport-dev-workspace"
  check "14151a4b5bb47dc4b7b9004fd68a2acee5ac4c97e514fe950d048d029f3717d5" "$tmp/stateport-dev-workspace.manifest.json"
  get "$PROBE_ROOT/stateport-execution-host.json" "$tmp/stateport-execution-host.manifest.json" "image manifest: stateport-execution-host"
  check "8baf9d180df73096ef26e4d25b44c046f39c29248ebba66b35d5841b72884fd9" "$tmp/stateport-execution-host.manifest.json"
  get "$PROBE_ROOT/stateport-playwright.json" "$tmp/stateport-playwright.manifest.json" "image manifest: stateport-playwright"
  check "c12380bb195db1b8a77fe1d39fc2dc87d04c54f1cfd9759b4cfac129a3f03f19" "$tmp/stateport-playwright.manifest.json"
  get "$PROBE_ROOT/stateport-runner.json" "$tmp/stateport-runner.manifest.json" "image manifest: stateport-runner"
  check "96f41f8a153c6a57fc7d6535cde8135051f3f9cefc1cb48bda651b02baf52a6a" "$tmp/stateport-runner.manifest.json"
  get "$PROBE_ROOT/stateport-web.json" "$tmp/stateport-web.manifest.json" "image manifest: stateport-web"
  check "14becec41e36b3883886128c230a733ca333842824fea812e6b1f96e0c1df7c3" "$tmp/stateport-web.manifest.json"
  get "$PROBE_ROOT/stateport-worker.json" "$tmp/stateport-worker.manifest.json" "image manifest: stateport-worker"
  check "77e4f18306e9f43bb415bf0dd73c1c2645d39366908fed59ad93af43639d10f3" "$tmp/stateport-worker.manifest.json"
  printf "StatePort Alpha.12 transport probe passed: bootstrap syntax and 7 exact image manifests verified; installer was not executed.\n"
  exit 0
fi
if [ "$mode" = materialization-preflight ]; then
  command -v curl >/dev/null 2>&1 || fail "curl is required for the materialization preflight."
  command -v install >/dev/null 2>&1 || fail "install is required for the materialization preflight."
  command -v sha256sum >/dev/null 2>&1 || fail "sha256sum is required for the materialization preflight."
  command -v stat >/dev/null 2>&1 || fail "stat is required for the materialization preflight."
  ensure_root_helper_parent / 0 0 check
  umask 077
  tmp=$(mktemp -d "${TMPDIR:-/tmp}/stateport-alpha12-materialization.XXXXXX") || fail "Cannot create a private preflight directory."
  trap 'rm -rf "$tmp"' EXIT
  trap 'exit 129' HUP
  trap 'exit 130' INT
  trap 'exit 143' TERM
  mkdir -m 755 "$tmp/root" "$tmp/root/usr" "$tmp/root/usr/local"
  ensure_root_helper_parent "$tmp/root" "$(id -u)" "$(id -g)" local
  get "$RELEASE_ROOT/stateport-execution-host-provision" "$tmp/provisioner" "execution-host provisioner"
  check "312ef592fb05bb45458b8f58e5551f0e5594bde2111d90555267494785da6d32" "$tmp/provisioner"
  install -m 0555 -- "$tmp/provisioner" "$tmp/root/usr/local/libexec/stateport-execution-host-provision"
  check "312ef592fb05bb45458b8f58e5551f0e5594bde2111d90555267494785da6d32" "$tmp/root/usr/local/libexec/stateport-execution-host-provision"
  printf "StatePort Alpha.12 materialization preflight passed: target, pinned helper transport, and absent-parent creation order verified; packages, root files, images, and installer were not changed or executed.\n"
  exit 0
fi
command -v sudo >/dev/null 2>&1 || fail "sudo is required."
command -v curl >/dev/null 2>&1 || fail "curl is required before privileged installation."
command -v dpkg-deb >/dev/null 2>&1 || fail "dpkg-deb is required before privileged installation."
command -v python3 >/dev/null 2>&1 || fail "python3 is required before privileged installation."
command -v sha256sum >/dev/null 2>&1 || fail "sha256sum is required before privileged installation."
command -v tar >/dev/null 2>&1 || fail "tar is required before privileged installation."
umask 077
tmp=$(mktemp -d "${TMPDIR:-/tmp}/stateport-wsl2-install.XXXXXX") || fail "Cannot create a private temporary directory."
trap 'rm -rf "$tmp"' EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM
mkdir -m 700 "$tmp/image-bundles" "$tmp/image-manifests" "$tmp/image-archives" "$tmp/image-carriers"
manifest_carrier() {
  image_id=$1
  reference=$2
  digest=$3
  digest_hex=${digest#sha256:}
  manifest="$tmp/image-manifests/$image_id"
  carrier="$tmp/image-carriers/$image_id"
  skopeo inspect --raw "docker://$reference" > "$manifest" || fail "Manifest download failed: $image_id"
  check "$digest_hex" "$manifest"
  mkdir -m 700 "$carrier"
  mkdir -p -m 700 "$carrier/blobs/sha256"
  cp "$manifest" "$carrier/blobs/sha256/$digest_hex"
  printf '{"schemaVersion":2,"manifests":[{"digest":"%s"}]}\n' "$digest" > "$carrier/index.json"
  tar -cf "$tmp/image-archives/$image_id.oci.tar" --sort=name --mtime=@0 --owner=0 --group=0 --numeric-owner -C "$carrier" index.json "blobs/sha256/$digest_hex"
}
get "$RELEASE_ROOT/stateport-installer" "$tmp/installer" "signed installer"
check "36f00872df78f413153149168e2899c1313797468c6828bf9eee99fdb2ea7416" "$tmp/installer"
get "$RELEASE_ROOT/stateport-execution-host-provision" "$tmp/provisioner" "execution-host provisioner"
check "312ef592fb05bb45458b8f58e5551f0e5594bde2111d90555267494785da6d32" "$tmp/provisioner"
get "$RELEASE_ROOT/stateport-updater" "$tmp/updater" "signed updater"
check "feec0e2de7b3666ca804e5a0802c192d17f1413915a6b855b697288e5ed41a70" "$tmp/updater"
get "$RELEASE_ROOT/release-index.json" "$tmp/release-index.json" "signed release index"
check "8fab98e60b1f4ed067aa8b3f2c8552f3dda266b53328c601eb67ce93671bfabb" "$tmp/release-index.json"
get "$RELEASE_ROOT/release-index.sigstore.json" "$tmp/release-index.sigstore.json" "release index signature"
check "6c1c0906742f778f9501405686c0c7de1959fe59c1fae4264cbeb99a6ad7ce31" "$tmp/release-index.sigstore.json"
get "$RELEASE_ROOT/stateport-alpha-2026-08-cosign.pub" "$tmp/release.pub" "release trust key"
check "798d6ea6e2703993758f0fb45618b1f05b40f6ef116e7d286fd5a6867859b8ad" "$tmp/release.pub"
get "$COSIGN_URL" "$tmp/cosign" "Cosign executable"
check "4629c757b7618056f8ddd7e2625ae9fdd94c0372a65049520bc7d9df9efc7f71" "$tmp/cosign"
chmod 700 "$tmp/installer" "$tmp/cosign"
get "$RELEASE_ROOT/signatures/stateport-api.sigstore.json" "$tmp/image-bundles/stateport-api.sigstore.json" "image signature: stateport-api"
check "f05880f1911a71c945765548f9d857d579434402af4553ee2327a26cf1c5d7af" "$tmp/image-bundles/stateport-api.sigstore.json"
get "$RELEASE_ROOT/signatures/stateport-dev-workspace.sigstore.json" "$tmp/image-bundles/stateport-dev-workspace.sigstore.json" "image signature: stateport-dev-workspace"
check "f6ab7f1048b34cab224e7731f642ff1434199a4dc3f3cc60f5ee5e2cfd557668" "$tmp/image-bundles/stateport-dev-workspace.sigstore.json"
get "$RELEASE_ROOT/signatures/stateport-execution-host.sigstore.json" "$tmp/image-bundles/stateport-execution-host.sigstore.json" "image signature: stateport-execution-host"
check "5d4ffb595b5da0d606a1a7b57dd8737ff87af362e7f06b681ba5df59bce46cad" "$tmp/image-bundles/stateport-execution-host.sigstore.json"
get "$RELEASE_ROOT/signatures/stateport-playwright.sigstore.json" "$tmp/image-bundles/stateport-playwright.sigstore.json" "image signature: stateport-playwright"
check "385a0c909e03ca06d198c6ec8ac2017f6c7c38ec5af4f26e5440b4356f3e9cd4" "$tmp/image-bundles/stateport-playwright.sigstore.json"
get "$RELEASE_ROOT/signatures/stateport-runner.sigstore.json" "$tmp/image-bundles/stateport-runner.sigstore.json" "image signature: stateport-runner"
check "4af105b5f163da8d4b8ee7581f72dda118f224eccd3b22868b23604e5299c9de" "$tmp/image-bundles/stateport-runner.sigstore.json"
get "$RELEASE_ROOT/signatures/stateport-web.sigstore.json" "$tmp/image-bundles/stateport-web.sigstore.json" "image signature: stateport-web"
check "783c5066016869108b6768bd4b81d44a2a2793d4fa2ba98083f68bcaf8b590c3" "$tmp/image-bundles/stateport-web.sigstore.json"
get "$RELEASE_ROOT/signatures/stateport-worker.sigstore.json" "$tmp/image-bundles/stateport-worker.sigstore.json" "image signature: stateport-worker"
check "3cb5866fd25f2d4ca675c925d289e532ff21fb85d5c4423eab96a5a74dafef0d" "$tmp/image-bundles/stateport-worker.sigstore.json"
get "$RELEASE_ROOT/stateport-podman-package-bundle.tar" "$tmp/podman-package-bundle.tar" "signed Podman package bundle"
check "445ddd9ac38cc581376260543e9246ebee360f75e75a22e6df3ce9a428b7106f" "$tmp/podman-package-bundle.tar"
get "$PROBE_ROOT/stateport-api.json" "$tmp/image-manifests/stateport-api" "image manifest: stateport-api"
check "01de186713c69817c1c09e5a36d7f94a8a24031efaf0105153f86372525c9578" "$tmp/image-manifests/stateport-api"
mkdir -m 700 "$tmp/image-carriers/stateport-api" "$tmp/image-carriers/stateport-api/blobs" "$tmp/image-carriers/stateport-api/blobs/sha256"
cp "$tmp/image-manifests/stateport-api" "$tmp/image-carriers/stateport-api/blobs/sha256/01de186713c69817c1c09e5a36d7f94a8a24031efaf0105153f86372525c9578"
printf '{"schemaVersion":2,"manifests":[{"digest":"sha256:01de186713c69817c1c09e5a36d7f94a8a24031efaf0105153f86372525c9578"}]}\n' > "$tmp/image-carriers/stateport-api/index.json"
tar -cf "$tmp/image-archives/stateport-api.oci.tar" --sort=name --mtime=@0 --owner=0 --group=0 --numeric-owner -C "$tmp/image-carriers/stateport-api" index.json "blobs/sha256/01de186713c69817c1c09e5a36d7f94a8a24031efaf0105153f86372525c9578"
get "$PROBE_ROOT/stateport-dev-workspace.json" "$tmp/image-manifests/stateport-dev-workspace" "image manifest: stateport-dev-workspace"
check "14151a4b5bb47dc4b7b9004fd68a2acee5ac4c97e514fe950d048d029f3717d5" "$tmp/image-manifests/stateport-dev-workspace"
mkdir -m 700 "$tmp/image-carriers/stateport-dev-workspace" "$tmp/image-carriers/stateport-dev-workspace/blobs" "$tmp/image-carriers/stateport-dev-workspace/blobs/sha256"
cp "$tmp/image-manifests/stateport-dev-workspace" "$tmp/image-carriers/stateport-dev-workspace/blobs/sha256/14151a4b5bb47dc4b7b9004fd68a2acee5ac4c97e514fe950d048d029f3717d5"
printf '{"schemaVersion":2,"manifests":[{"digest":"sha256:14151a4b5bb47dc4b7b9004fd68a2acee5ac4c97e514fe950d048d029f3717d5"}]}\n' > "$tmp/image-carriers/stateport-dev-workspace/index.json"
tar -cf "$tmp/image-archives/stateport-dev-workspace.oci.tar" --sort=name --mtime=@0 --owner=0 --group=0 --numeric-owner -C "$tmp/image-carriers/stateport-dev-workspace" index.json "blobs/sha256/14151a4b5bb47dc4b7b9004fd68a2acee5ac4c97e514fe950d048d029f3717d5"
get "$PROBE_ROOT/stateport-execution-host.json" "$tmp/image-manifests/stateport-execution-host" "image manifest: stateport-execution-host"
check "8baf9d180df73096ef26e4d25b44c046f39c29248ebba66b35d5841b72884fd9" "$tmp/image-manifests/stateport-execution-host"
mkdir -m 700 "$tmp/image-carriers/stateport-execution-host" "$tmp/image-carriers/stateport-execution-host/blobs" "$tmp/image-carriers/stateport-execution-host/blobs/sha256"
cp "$tmp/image-manifests/stateport-execution-host" "$tmp/image-carriers/stateport-execution-host/blobs/sha256/8baf9d180df73096ef26e4d25b44c046f39c29248ebba66b35d5841b72884fd9"
printf '{"schemaVersion":2,"manifests":[{"digest":"sha256:8baf9d180df73096ef26e4d25b44c046f39c29248ebba66b35d5841b72884fd9"}]}\n' > "$tmp/image-carriers/stateport-execution-host/index.json"
tar -cf "$tmp/image-archives/stateport-execution-host.oci.tar" --sort=name --mtime=@0 --owner=0 --group=0 --numeric-owner -C "$tmp/image-carriers/stateport-execution-host" index.json "blobs/sha256/8baf9d180df73096ef26e4d25b44c046f39c29248ebba66b35d5841b72884fd9"
get "$PROBE_ROOT/stateport-playwright.json" "$tmp/image-manifests/stateport-playwright" "image manifest: stateport-playwright"
check "c12380bb195db1b8a77fe1d39fc2dc87d04c54f1cfd9759b4cfac129a3f03f19" "$tmp/image-manifests/stateport-playwright"
mkdir -m 700 "$tmp/image-carriers/stateport-playwright" "$tmp/image-carriers/stateport-playwright/blobs" "$tmp/image-carriers/stateport-playwright/blobs/sha256"
cp "$tmp/image-manifests/stateport-playwright" "$tmp/image-carriers/stateport-playwright/blobs/sha256/c12380bb195db1b8a77fe1d39fc2dc87d04c54f1cfd9759b4cfac129a3f03f19"
printf '{"schemaVersion":2,"manifests":[{"digest":"sha256:c12380bb195db1b8a77fe1d39fc2dc87d04c54f1cfd9759b4cfac129a3f03f19"}]}\n' > "$tmp/image-carriers/stateport-playwright/index.json"
tar -cf "$tmp/image-archives/stateport-playwright.oci.tar" --sort=name --mtime=@0 --owner=0 --group=0 --numeric-owner -C "$tmp/image-carriers/stateport-playwright" index.json "blobs/sha256/c12380bb195db1b8a77fe1d39fc2dc87d04c54f1cfd9759b4cfac129a3f03f19"
get "$PROBE_ROOT/stateport-runner.json" "$tmp/image-manifests/stateport-runner" "image manifest: stateport-runner"
check "96f41f8a153c6a57fc7d6535cde8135051f3f9cefc1cb48bda651b02baf52a6a" "$tmp/image-manifests/stateport-runner"
mkdir -m 700 "$tmp/image-carriers/stateport-runner" "$tmp/image-carriers/stateport-runner/blobs" "$tmp/image-carriers/stateport-runner/blobs/sha256"
cp "$tmp/image-manifests/stateport-runner" "$tmp/image-carriers/stateport-runner/blobs/sha256/96f41f8a153c6a57fc7d6535cde8135051f3f9cefc1cb48bda651b02baf52a6a"
printf '{"schemaVersion":2,"manifests":[{"digest":"sha256:96f41f8a153c6a57fc7d6535cde8135051f3f9cefc1cb48bda651b02baf52a6a"}]}\n' > "$tmp/image-carriers/stateport-runner/index.json"
tar -cf "$tmp/image-archives/stateport-runner.oci.tar" --sort=name --mtime=@0 --owner=0 --group=0 --numeric-owner -C "$tmp/image-carriers/stateport-runner" index.json "blobs/sha256/96f41f8a153c6a57fc7d6535cde8135051f3f9cefc1cb48bda651b02baf52a6a"
get "$PROBE_ROOT/stateport-web.json" "$tmp/image-manifests/stateport-web" "image manifest: stateport-web"
check "14becec41e36b3883886128c230a733ca333842824fea812e6b1f96e0c1df7c3" "$tmp/image-manifests/stateport-web"
mkdir -m 700 "$tmp/image-carriers/stateport-web" "$tmp/image-carriers/stateport-web/blobs" "$tmp/image-carriers/stateport-web/blobs/sha256"
cp "$tmp/image-manifests/stateport-web" "$tmp/image-carriers/stateport-web/blobs/sha256/14becec41e36b3883886128c230a733ca333842824fea812e6b1f96e0c1df7c3"
printf '{"schemaVersion":2,"manifests":[{"digest":"sha256:14becec41e36b3883886128c230a733ca333842824fea812e6b1f96e0c1df7c3"}]}\n' > "$tmp/image-carriers/stateport-web/index.json"
tar -cf "$tmp/image-archives/stateport-web.oci.tar" --sort=name --mtime=@0 --owner=0 --group=0 --numeric-owner -C "$tmp/image-carriers/stateport-web" index.json "blobs/sha256/14becec41e36b3883886128c230a733ca333842824fea812e6b1f96e0c1df7c3"
get "$PROBE_ROOT/stateport-worker.json" "$tmp/image-manifests/stateport-worker" "image manifest: stateport-worker"
check "77e4f18306e9f43bb415bf0dd73c1c2645d39366908fed59ad93af43639d10f3" "$tmp/image-manifests/stateport-worker"
mkdir -m 700 "$tmp/image-carriers/stateport-worker" "$tmp/image-carriers/stateport-worker/blobs" "$tmp/image-carriers/stateport-worker/blobs/sha256"
cp "$tmp/image-manifests/stateport-worker" "$tmp/image-carriers/stateport-worker/blobs/sha256/77e4f18306e9f43bb415bf0dd73c1c2645d39366908fed59ad93af43639d10f3"
printf '{"schemaVersion":2,"manifests":[{"digest":"sha256:77e4f18306e9f43bb415bf0dd73c1c2645d39366908fed59ad93af43639d10f3"}]}\n' > "$tmp/image-carriers/stateport-worker/index.json"
tar -cf "$tmp/image-archives/stateport-worker.oci.tar" --sort=name --mtime=@0 --owner=0 --group=0 --numeric-owner -C "$tmp/image-carriers/stateport-worker" index.json "blobs/sha256/77e4f18306e9f43bb415bf0dd73c1c2645d39366908fed59ad93af43639d10f3"
retain_slot() { mkdir -p -m 700 "$1"; install -m 600 "$2" "$1/$3"; }
retain_slot "$tmp/6c1c0906742f778f9501405686c0c7de1959fe59c1fae4264cbeb99a6ad7ce31" "$tmp/release-index.sigstore.json" "release-index.sigstore.json"
retain_slot "$tmp/f05880f1911a71c945765548f9d857d579434402af4553ee2327a26cf1c5d7af" "$tmp/image-bundles/stateport-api.sigstore.json" "stateport-api.sigstore.json"
retain_slot "$tmp/f6ab7f1048b34cab224e7731f642ff1434199a4dc3f3cc60f5ee5e2cfd557668" "$tmp/image-bundles/stateport-dev-workspace.sigstore.json" "stateport-dev-workspace.sigstore.json"
retain_slot "$tmp/5d4ffb595b5da0d606a1a7b57dd8737ff87af362e7f06b681ba5df59bce46cad" "$tmp/image-bundles/stateport-execution-host.sigstore.json" "stateport-execution-host.sigstore.json"
retain_slot "$tmp/385a0c909e03ca06d198c6ec8ac2017f6c7c38ec5af4f26e5440b4356f3e9cd4" "$tmp/image-bundles/stateport-playwright.sigstore.json" "stateport-playwright.sigstore.json"
retain_slot "$tmp/4af105b5f163da8d4b8ee7581f72dda118f224eccd3b22868b23604e5299c9de" "$tmp/image-bundles/stateport-runner.sigstore.json" "stateport-runner.sigstore.json"
retain_slot "$tmp/783c5066016869108b6768bd4b81d44a2a2793d4fa2ba98083f68bcaf8b590c3" "$tmp/image-bundles/stateport-web.sigstore.json" "stateport-web.sigstore.json"
retain_slot "$tmp/3cb5866fd25f2d4ca675c925d289e532ff21fb85d5c4423eab96a5a74dafef0d" "$tmp/image-bundles/stateport-worker.sigstore.json" "stateport-worker.sigstore.json"
sudo -v
sudo apt-get update -o DPkg::Lock::Timeout=300 || { printf "StatePort apt update retry after lock contention\n" >&2; sleep 10; sudo apt-get update -o DPkg::Lock::Timeout=300; }
sudo apt-get install -y --no-install-recommends -o DPkg::Lock::Timeout=300 ca-certificates fuse3 nftables libglib2.0-0t64 libgpgme11t64 libdevmapper1.02.1 libfuse3-3 libseccomp2 libsqlite3-0 libaudit1 libselinux1 dbus-broker dbus-session-bus-common libpam-systemd systemd python3 python3-venv
python3 "$tmp/installer" --verify-podman-package-bundle \
  --release-index "$tmp/release-index.json" \
  --bundle-root "$tmp" \
  --trust-public-key "$tmp/release.pub" \
  --trust-key-id "stateport-alpha-private-2026-08" \
  --trust-key-fingerprint "sha256:df24c1ccdcf1ecf72da6d8d81ae8b0ffaca8d399826091b107cc4d6905915ea5" \
  --updater-wheel "$tmp/updater" \
  --execution-host-provisioner "$tmp/provisioner" \
  --compose "$RELEASE_ROOT/compose.yaml" \
  --source-archive "$RELEASE_ROOT/stateport-source.tar" \
  --release-notes "$RELEASE_ROOT/release-notes.md" \
  --known-limitations "$RELEASE_ROOT/known-limitations.md" \
  --channel alpha \
  --cosign "$tmp/cosign" \
  --installer-path "$tmp/installer" \
  --podman-package-bundle "$tmp/podman-package-bundle.tar" \
  --podman-package-output "$tmp/podman-packages" > "$tmp/podman-package-preflight.json"
package_plan_digest=$(python3 - "$tmp/podman-package-preflight.json" <<'PY'
import json, re, sys
value = json.load(open(sys.argv[1], encoding="utf-8"))
digest = value.get("packagePlanDigest", "")
if re.fullmatch(r"sha256:[0-9a-f]{64}", digest) is None:
    raise SystemExit("invalid authenticated package plan")
print("Authenticated repository-free package plan:", digest, file=sys.stderr)
for name, action in sorted(value["transaction"].items()):
    package = value["packages"][name]
    current = action["currentVersion"] or "absent"
    print(f"  {action['action']}: {name} {current} -> {action['targetVersion']} ({package['sha256']}, {package['size']} bytes)", file=sys.stderr)
print(digest, end="")
PY
)
printf "Type install-packages to authorize this exact authenticated package plan: " >/dev/tty
IFS= read -r package_answer </dev/tty || package_answer=
[ "$package_answer" = install-packages ] || fail "Authenticated package plan not confirmed."
sudo -v
root_stage=$(sudo -n mktemp -d /var/tmp/stateport-podman-packages.XXXXXX) || fail "Cannot create sealed root package staging."
trap 'status=$?; [ -z "${root_stage-}" ] || sudo -n rm -rf -- "$root_stage" >/dev/null 2>&1 || true; rm -rf "$tmp"; exit "$status"' EXIT
sudo -n install -o root -g root -m 0500 "$tmp/installer" "$root_stage/installer"
sudo -n install -o root -g root -m 0500 "$tmp/cosign" "$root_stage/cosign"
sudo -n install -o root -g root -m 0400 "$tmp/release-index.json" "$root_stage/release-index.json"
sudo -n install -o root -g root -m 0400 "$tmp/release-index.sigstore.json" "$root_stage/release-index.sigstore.json"
sudo -n install -o root -g root -m 0400 "$tmp/release.pub" "$root_stage/release.pub"
sudo -n install -o root -g root -m 0400 "$tmp/podman-package-bundle.tar" "$root_stage/podman-package-bundle.tar"
sudo -n sh -c 'printf "%s  %s\n" "$1" "$2" | sha256sum -c --status' sh "36f00872df78f413153149168e2899c1313797468c6828bf9eee99fdb2ea7416" "$root_stage/installer" || fail "Sealed installer copy changed."
sudo -n sh -c 'printf "%s  %s\n" "$1" "$2" | sha256sum -c --status' sh "4629c757b7618056f8ddd7e2625ae9fdd94c0372a65049520bc7d9df9efc7f71" "$root_stage/cosign" || fail "Sealed Cosign copy changed."
sudo -n sh -c 'printf "%s  %s\n" "$1" "$2" | sha256sum -c --status' sh "8fab98e60b1f4ed067aa8b3f2c8552f3dda266b53328c601eb67ce93671bfabb" "$root_stage/release-index.json" || fail "Sealed release index changed."
sudo -n sh -c 'printf "%s  %s\n" "$1" "$2" | sha256sum -c --status' sh "6c1c0906742f778f9501405686c0c7de1959fe59c1fae4264cbeb99a6ad7ce31" "$root_stage/release-index.sigstore.json" || fail "Sealed release signature changed."
sudo -n sh -c 'printf "%s  %s\n" "$1" "$2" | sha256sum -c --status' sh "798d6ea6e2703993758f0fb45618b1f05b40f6ef116e7d286fd5a6867859b8ad" "$root_stage/release.pub" || fail "Sealed trust key changed."
sudo -n sh -c 'printf "%s  %s\n" "$1" "$2" | sha256sum -c --status' sh "445ddd9ac38cc581376260543e9246ebee360f75e75a22e6df3ce9a428b7106f" "$root_stage/podman-package-bundle.tar" || fail "Sealed package bundle changed."
sudo -n "$root_stage/installer" --verify-sealed-podman-package-bundle \
  --release-index "$root_stage/release-index.json" --bundle-root "$root_stage" \
  --trust-public-key "$root_stage/release.pub" --trust-key-id "stateport-alpha-private-2026-08" \
  --trust-key-fingerprint "sha256:df24c1ccdcf1ecf72da6d8d81ae8b0ffaca8d399826091b107cc4d6905915ea5" --cosign "$root_stage/cosign" \
  --installer-path "$root_stage/installer" \
  --podman-package-bundle "$root_stage/podman-package-bundle.tar" \
  --podman-package-output "$root_stage/extracted" > "$tmp/root-package-preflight.json"
python3 - "$tmp/podman-package-preflight.json" "$tmp/root-package-preflight.json" <<'PY'
import json, sys
left, right = (json.load(open(path, encoding="utf-8")) for path in sys.argv[1:])
left.pop("releaseAdmission", None)
if left != right:
    raise SystemExit("root package re-verification differs from unprivileged admission")
PY
root_package_dir="$root_stage/extracted"
sudo -n apt-get install -y --no-download --no-install-recommends --no-remove -o DPkg::Lock::Timeout=300 -o Dir::Etc::sourcelist=/dev/null -o Dir::Etc::sourceparts=- -o Dir::State::lists="$root_stage/extracted/.apt-lists" "$root_package_dir/podman-package-bundle/packages/aardvark-dns_1.14.0-3stateport1~24.04.1_amd64.deb" "$root_package_dir/podman-package-bundle/packages/catatonit_0.1.7-1_amd64.deb" "$root_package_dir/podman-package-bundle/packages/conmon_2.1.10+ds1-1build2_amd64.deb" "$root_package_dir/podman-package-bundle/packages/containers-storage_1.51.0+ds1-2ubuntu0.24.04.3_amd64.deb" "$root_package_dir/podman-package-bundle/packages/dbus-user-session_1.14.10-4ubuntu4.1_amd64.deb" "$root_package_dir/podman-package-bundle/packages/fuse-overlayfs_1.13-1_amd64.deb" "$root_package_dir/podman-package-bundle/packages/golang-github-containers-common_0.57.4+ds1-2ubuntu0.2_all.deb" "$root_package_dir/podman-package-bundle/packages/golang-github-containers-image_5.29.2-2_all.deb" "$root_package_dir/podman-package-bundle/packages/libslirp0_4.7.0-1ubuntu3.1_amd64.deb" "$root_package_dir/podman-package-bundle/packages/libsubid4_4.13+dfsg1-4ubuntu3.2_amd64.deb" "$root_package_dir/podman-package-bundle/packages/netavark_1.14.0-2stateport1~24.04.1_amd64.deb" "$root_package_dir/podman-package-bundle/packages/podman_5.4.2+ds1-2stateport2~24.04.1_amd64.deb" "$root_package_dir/podman-package-bundle/packages/python3-venv_3.12.3-0ubuntu2.1_amd64.deb" "$root_package_dir/podman-package-bundle/packages/runc_1.3.4-0ubuntu1~24.04.1_amd64.deb" "$root_package_dir/podman-package-bundle/packages/skopeo_1.13.3+ds1-2build2_amd64.deb" "$root_package_dir/podman-package-bundle/packages/slirp4netns_1.2.1-1build2_amd64.deb" "$root_package_dir/podman-package-bundle/packages/uidmap_4.13+dfsg1-4ubuntu3.2_amd64.deb"
sudo -n rm -rf -- "$root_stage"; root_stage=
python3 "$tmp/installer" --verify-installed-podman-packages --podman-package-preflight "$tmp/podman-package-preflight.json" > "$tmp/podman-package-installation.json"
sudo loginctl enable-linger "$USER"
command -v curl >/dev/null 2>&1 || fail "curl installation failed."
command -v skopeo >/dev/null 2>&1 || fail "skopeo installation failed."
command -v tar >/dev/null 2>&1 || fail "tar is required."
command -v sha256sum >/dev/null 2>&1 || fail "sha256sum is required."
python3 "$tmp/installer" \
  --release-index "$tmp/release-index.json" \
  --bundle-root "$tmp" \
  --trust-public-key "$tmp/release.pub" \
  --trust-key-id stateport-alpha-private-2026-08 \
  --trust-key-fingerprint sha256:df24c1ccdcf1ecf72da6d8d81ae8b0ffaca8d399826091b107cc4d6905915ea5 \
  --updater-wheel "$tmp/updater" \
  --execution-host-provisioner "$tmp/provisioner" \
  --compose "$RELEASE_ROOT/compose.yaml" \
  --source-archive "$RELEASE_ROOT/stateport-source.tar" \
  --release-notes "$RELEASE_ROOT/release-notes.md" \
  --known-limitations "$RELEASE_ROOT/known-limitations.md" \
  --podman-package-bundle "$tmp/podman-package-bundle.tar" \
  --channel alpha \
  --cosign "$tmp/cosign" \
  --installer-path "$tmp/installer" \
  --execution-host-receipt "$RECEIPT" \
  --state-root "$STATE_ROOT" \
  --podman-package-preflight "$tmp/podman-package-preflight.json" \
  --confirmed-package-plan-digest "$package_plan_digest" \
  --yes --confirmed-plan-digest "$install_plan_digest" \
  --prepare-execution-host
sudo -v
install_plan_digest=$(python3 - "$STATE_ROOT/install-plan.json" <<'PY'
import json, re, sys
value = json.load(open(sys.argv[1], encoding="utf-8"))
digest = value.get("planDigest", "")
if re.fullmatch(r"sha256:[0-9a-f]{64}", digest) is None:
    raise SystemExit("prepared install plan has no exact digest")
print("Exact StatePort install plan:", digest, file=sys.stderr)
print("  release:", value["release"]["version"], value["release"]["signedPayloadDigest"], file=sys.stderr)
print("  package plan:", value["podmanPackageInstallation"]["packagePlanDigest"], file=sys.stderr)
for image in value["images"]:
    print("  image:", image["imageId"], image["digest"], file=sys.stderr)
print(digest, end="")
PY
)
printf "Type install-exact to authorize this exact plan: " >/dev/tty
IFS= read -r install_answer </dev/tty || install_answer=
[ "$install_answer" = install-exact ] || fail "Exact install plan not confirmed."
ensure_root_helper_parent / 0 0 sudo
sudo -n install -o root -g root -m 0555 "$tmp/provisioner" /usr/local/libexec/stateport-execution-host-provision
sudo -n /usr/local/libexec/stateport-execution-host-provision materialize \
  --execution-host-provisioner /usr/local/libexec/stateport-execution-host-provision \
  --execution-host-provisioner-digest "sha256:312ef592fb05bb45458b8f58e5551f0e5594bde2111d90555267494785da6d32" \
  --execution-host-provisioner-bytes "35615" \
  --updater-wheel "$tmp/updater" --updater-wheel-digest "sha256:feec0e2de7b3666ca804e5a0802c192d17f1413915a6b855b697288e5ed41a70" \
  --release-index "$tmp/release-index.json" --bundle-root "$tmp" \
  --cosign "$tmp/cosign" --cosign-digest "sha256:4629c757b7618056f8ddd7e2625ae9fdd94c0372a65049520bc7d9df9efc7f71" \
  --trust-public-key "$tmp/release.pub" --trust-public-key-digest "sha256:798d6ea6e2703993758f0fb45618b1f05b40f6ef116e7d286fd5a6867859b8ad" \
  --trust-key-id "stateport-alpha-private-2026-08" --trust-key-fingerprint "sha256:df24c1ccdcf1ecf72da6d8d81ae8b0ffaca8d399826091b107cc4d6905915ea5"
sudo -n /usr/local/libexec/stateport-execution-host-provision provision \
  --release-index "$tmp/release-index.json" --plan "$STATE_ROOT/execution-host-provisioning-plan.json" \
  --cosign /usr/local/lib/stateport/tools/cosign \
  --trust-public-key /etc/stateport/alpha-2026-08-cosign.pub \
  --trust-key-id "stateport-alpha-private-2026-08" --trust-key-fingerprint "sha256:df24c1ccdcf1ecf72da6d8d81ae8b0ffaca8d399826091b107cc4d6905915ea5" \
  --channel alpha --bundle-root "$STATE_ROOT/updater/bundles" --receipt-out "$RECEIPT"
sudo -n systemctl restart "user@$(id -u).service"
python3 "$tmp/installer" \
  --release-index "$tmp/release-index.json" \
  --bundle-root "$tmp" \
  --trust-public-key "$tmp/release.pub" \
  --trust-key-id stateport-alpha-private-2026-08 \
  --trust-key-fingerprint sha256:df24c1ccdcf1ecf72da6d8d81ae8b0ffaca8d399826091b107cc4d6905915ea5 \
  --updater-wheel "$tmp/updater" \
  --execution-host-provisioner "$tmp/provisioner" \
  --compose "$RELEASE_ROOT/compose.yaml" \
  --source-archive "$RELEASE_ROOT/stateport-source.tar" \
  --release-notes "$RELEASE_ROOT/release-notes.md" \
  --known-limitations "$RELEASE_ROOT/known-limitations.md" \
  --podman-package-bundle "$tmp/podman-package-bundle.tar" \
  --channel alpha \
  --cosign "$tmp/cosign" \
  --installer-path "$tmp/installer" \
  --execution-host-receipt "$RECEIPT" \
  --state-root "$STATE_ROOT" \
  --podman-package-preflight "$tmp/podman-package-preflight.json" \
  --confirmed-package-plan-digest "$package_plan_digest" \
  --yes --confirmed-plan-digest "$install_plan_digest"
printf "StatePort %s installed successfully for %s.\n" "$STATEPORT_VERSION" "$TARGET"
