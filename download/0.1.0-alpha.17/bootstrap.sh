#!/bin/sh
# StatePort v0.1.0-alpha.17 Windows 11 + WSL2 + Ubuntu 24.04 bootstrap.
set -eu
STATEPORT_VERSION="0.1.0-alpha.17"
RELEASE_ROOT="https://lennertvhoy.github.io/StatePort-Site/download/0.1.0-alpha.17"
PROBE_ROOT="https://lennertvhoy.github.io/StatePort-Site/download/alpha17-manifests"
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
  tmp=$(mktemp -d "${TMPDIR:-/tmp}/stateport-alpha17-probe.XXXXXX") || fail "Cannot create a private probe directory."
  trap 'rm -rf "$tmp"' EXIT
  trap 'exit 129' HUP
  trap 'exit 130' INT
  trap 'exit 143' TERM
  get "$PROBE_ROOT/stateport-api.json" "$tmp/stateport-api.manifest.json" "image manifest: stateport-api"
  check "63d7c8f4eaa5e6742db8d73a9dd5f93594511c4e6010c06aa09e09c5bef31c57" "$tmp/stateport-api.manifest.json"
  get "$PROBE_ROOT/stateport-dev-workspace.json" "$tmp/stateport-dev-workspace.manifest.json" "image manifest: stateport-dev-workspace"
  check "e1d054da25bcf404fbf7ee57f8686901dbc31bd3d244162a2b401d8157bfdd02" "$tmp/stateport-dev-workspace.manifest.json"
  get "$PROBE_ROOT/stateport-execution-host.json" "$tmp/stateport-execution-host.manifest.json" "image manifest: stateport-execution-host"
  check "27b70d981709099a5ce8a7999a9160f8aad96c43edf2b1a5b4b8b0c96a858def" "$tmp/stateport-execution-host.manifest.json"
  get "$PROBE_ROOT/stateport-playwright.json" "$tmp/stateport-playwright.manifest.json" "image manifest: stateport-playwright"
  check "307892a7e0d5b46803b00a74b8ecc3ee96e3fd6a4829be237328b99df78c1a24" "$tmp/stateport-playwright.manifest.json"
  get "$PROBE_ROOT/stateport-runner.json" "$tmp/stateport-runner.manifest.json" "image manifest: stateport-runner"
  check "5782579c7ee235ca27b0002a03ba064b14f1654bcf1b0153c60275bfd5872a0c" "$tmp/stateport-runner.manifest.json"
  get "$PROBE_ROOT/stateport-web.json" "$tmp/stateport-web.manifest.json" "image manifest: stateport-web"
  check "a0288e7eff247655c9e0ccbf71fc9652caad3c1fdba640c69b35cb85f8e10289" "$tmp/stateport-web.manifest.json"
  get "$PROBE_ROOT/stateport-worker.json" "$tmp/stateport-worker.manifest.json" "image manifest: stateport-worker"
  check "38e90db24ccc31d6a7368d577eafe3872ebf11b2db7a814e95e0d22fb3fd1637" "$tmp/stateport-worker.manifest.json"
  printf "StatePort Alpha.17 transport probe passed: bootstrap syntax and 7 exact image manifests verified; installer was not executed.\n"
  exit 0
fi
if [ "$mode" = materialization-preflight ]; then
  command -v curl >/dev/null 2>&1 || fail "curl is required for the materialization preflight."
  command -v install >/dev/null 2>&1 || fail "install is required for the materialization preflight."
  command -v sha256sum >/dev/null 2>&1 || fail "sha256sum is required for the materialization preflight."
  command -v stat >/dev/null 2>&1 || fail "stat is required for the materialization preflight."
  ensure_root_helper_parent / 0 0 check
  umask 077
  tmp=$(mktemp -d "${TMPDIR:-/tmp}/stateport-alpha17-materialization.XXXXXX") || fail "Cannot create a private preflight directory."
  trap 'rm -rf "$tmp"' EXIT
  trap 'exit 129' HUP
  trap 'exit 130' INT
  trap 'exit 143' TERM
  mkdir -m 755 "$tmp/root" "$tmp/root/usr" "$tmp/root/usr/local"
  ensure_root_helper_parent "$tmp/root" "$(id -u)" "$(id -g)" local
  get "$RELEASE_ROOT/stateport-execution-host-provision" "$tmp/provisioner" "execution-host provisioner"
  check "3545e3216fded144b4dc783bf38ad1622b808c1e3e821ec729112bc875011d1e" "$tmp/provisioner"
  install -m 0555 -- "$tmp/provisioner" "$tmp/root/usr/local/libexec/stateport-execution-host-provision"
  check "3545e3216fded144b4dc783bf38ad1622b808c1e3e821ec729112bc875011d1e" "$tmp/root/usr/local/libexec/stateport-execution-host-provision"
  printf "StatePort Alpha.17 materialization preflight passed: target, pinned helper transport, and absent-parent creation order verified; packages, root files, images, and installer were not changed or executed.\n"
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
check "0b35b3b4b40d4e32483e9fd884985a7731a3c763f52f62c8e55f4a5b0be8bc18" "$tmp/installer"
get "$RELEASE_ROOT/stateport-execution-host-provision" "$tmp/provisioner" "execution-host provisioner"
check "3545e3216fded144b4dc783bf38ad1622b808c1e3e821ec729112bc875011d1e" "$tmp/provisioner"
get "$RELEASE_ROOT/stateport-updater" "$tmp/updater" "signed updater"
check "3c74e81f0f2902334f6e410d8f5c4698353b150751db29d360c2c5c60ae6078e" "$tmp/updater"
get "$RELEASE_ROOT/release-index.json" "$tmp/release-index.json" "signed release index"
check "e2391732872e05402c2ae8bdb018b1b64b284c2490d88197a37cf011b6f8b809" "$tmp/release-index.json"
get "$RELEASE_ROOT/release-index.sigstore.json" "$tmp/release-index.sigstore.json" "release index signature"
check "810a9a5e27e03063f155cf71481f861bf0b16855b8a74a463d3e02d8225b00e4" "$tmp/release-index.sigstore.json"
get "$RELEASE_ROOT/stateport-alpha-2026-08-cosign.pub" "$tmp/release.pub" "release trust key"
check "798d6ea6e2703993758f0fb45618b1f05b40f6ef116e7d286fd5a6867859b8ad" "$tmp/release.pub"
get "$COSIGN_URL" "$tmp/cosign" "Cosign executable"
check "4629c757b7618056f8ddd7e2625ae9fdd94c0372a65049520bc7d9df9efc7f71" "$tmp/cosign"
chmod 700 "$tmp/installer" "$tmp/cosign"
mkdir -m 700 "$tmp/predecessor-bundle"
get "$RELEASE_ROOT/predecessor-bundle/release-index.sigstore.json" "$tmp/predecessor-bundle/release-index.sigstore.json" "predecessor signature bundle"
check "ff36ca75c5139d58a92e7d9b78a53f120aa4e4f42cdf9be35603eef3e682b557" "$tmp/predecessor-bundle/release-index.sigstore.json"
mkdir -p -m 700 "$tmp/ff36ca75c5139d58a92e7d9b78a53f120aa4e4f42cdf9be35603eef3e682b557"
install -m 600 "$tmp/predecessor-bundle/release-index.sigstore.json" "$tmp/ff36ca75c5139d58a92e7d9b78a53f120aa4e4f42cdf9be35603eef3e682b557/release-index.sigstore.json"
get "$RELEASE_ROOT/signatures/stateport-api.sigstore.json" "$tmp/image-bundles/stateport-api.sigstore.json" "image signature: stateport-api"
check "5e5ee079c1de11dba0e285586eb154332334d09e649fcafd1de779bbcce3756d" "$tmp/image-bundles/stateport-api.sigstore.json"
get "$RELEASE_ROOT/signatures/stateport-dev-workspace.sigstore.json" "$tmp/image-bundles/stateport-dev-workspace.sigstore.json" "image signature: stateport-dev-workspace"
check "9d8abecb5104e75e23e8a57704f5201ad7aad7bb9dfd38d92be154a17531ea30" "$tmp/image-bundles/stateport-dev-workspace.sigstore.json"
get "$RELEASE_ROOT/signatures/stateport-execution-host.sigstore.json" "$tmp/image-bundles/stateport-execution-host.sigstore.json" "image signature: stateport-execution-host"
check "2ee39ad4efdf33b20e5447b3a7f0230c62fbe8e6e0eb6eca668b89f2d2762455" "$tmp/image-bundles/stateport-execution-host.sigstore.json"
get "$RELEASE_ROOT/signatures/stateport-playwright.sigstore.json" "$tmp/image-bundles/stateport-playwright.sigstore.json" "image signature: stateport-playwright"
check "f63a1907af6d73e5b0c581e129da5cfd66383f2c6b38496419a0f2ead7b2d576" "$tmp/image-bundles/stateport-playwright.sigstore.json"
get "$RELEASE_ROOT/signatures/stateport-runner.sigstore.json" "$tmp/image-bundles/stateport-runner.sigstore.json" "image signature: stateport-runner"
check "ed173cd9ad511ef9c0dfb2092eeb42afa1ca941a07f6f31133ecfc38cdd4f08a" "$tmp/image-bundles/stateport-runner.sigstore.json"
get "$RELEASE_ROOT/signatures/stateport-web.sigstore.json" "$tmp/image-bundles/stateport-web.sigstore.json" "image signature: stateport-web"
check "d495486a15034420ad359ab0edfe29d69882e409ab070d5fd537536a1de190b4" "$tmp/image-bundles/stateport-web.sigstore.json"
get "$RELEASE_ROOT/signatures/stateport-worker.sigstore.json" "$tmp/image-bundles/stateport-worker.sigstore.json" "image signature: stateport-worker"
check "e5f3acf9544b7fac74873193a1fc7a7e6e8953406f320e03a581388916d7a1a1" "$tmp/image-bundles/stateport-worker.sigstore.json"
get "$RELEASE_ROOT/stateport-podman-package-bundle.tar" "$tmp/podman-package-bundle.tar" "signed Podman package bundle"
check "a472bd4a28dacc2ccfc286ed35ba76d3bfaa71fc765a5b51d09b84cbc0c9ea2f" "$tmp/podman-package-bundle.tar"
get "$PROBE_ROOT/stateport-api.json" "$tmp/image-manifests/stateport-api" "image manifest: stateport-api"
check "63d7c8f4eaa5e6742db8d73a9dd5f93594511c4e6010c06aa09e09c5bef31c57" "$tmp/image-manifests/stateport-api"
mkdir -m 700 "$tmp/image-carriers/stateport-api" "$tmp/image-carriers/stateport-api/blobs" "$tmp/image-carriers/stateport-api/blobs/sha256"
cp "$tmp/image-manifests/stateport-api" "$tmp/image-carriers/stateport-api/blobs/sha256/63d7c8f4eaa5e6742db8d73a9dd5f93594511c4e6010c06aa09e09c5bef31c57"
printf '{"schemaVersion":2,"manifests":[{"digest":"sha256:63d7c8f4eaa5e6742db8d73a9dd5f93594511c4e6010c06aa09e09c5bef31c57"}]}\n' > "$tmp/image-carriers/stateport-api/index.json"
tar -cf "$tmp/image-archives/stateport-api.oci.tar" --sort=name --mtime=@0 --owner=0 --group=0 --numeric-owner -C "$tmp/image-carriers/stateport-api" index.json "blobs/sha256/63d7c8f4eaa5e6742db8d73a9dd5f93594511c4e6010c06aa09e09c5bef31c57"
get "$PROBE_ROOT/stateport-dev-workspace.json" "$tmp/image-manifests/stateport-dev-workspace" "image manifest: stateport-dev-workspace"
check "e1d054da25bcf404fbf7ee57f8686901dbc31bd3d244162a2b401d8157bfdd02" "$tmp/image-manifests/stateport-dev-workspace"
mkdir -m 700 "$tmp/image-carriers/stateport-dev-workspace" "$tmp/image-carriers/stateport-dev-workspace/blobs" "$tmp/image-carriers/stateport-dev-workspace/blobs/sha256"
cp "$tmp/image-manifests/stateport-dev-workspace" "$tmp/image-carriers/stateport-dev-workspace/blobs/sha256/e1d054da25bcf404fbf7ee57f8686901dbc31bd3d244162a2b401d8157bfdd02"
printf '{"schemaVersion":2,"manifests":[{"digest":"sha256:e1d054da25bcf404fbf7ee57f8686901dbc31bd3d244162a2b401d8157bfdd02"}]}\n' > "$tmp/image-carriers/stateport-dev-workspace/index.json"
tar -cf "$tmp/image-archives/stateport-dev-workspace.oci.tar" --sort=name --mtime=@0 --owner=0 --group=0 --numeric-owner -C "$tmp/image-carriers/stateport-dev-workspace" index.json "blobs/sha256/e1d054da25bcf404fbf7ee57f8686901dbc31bd3d244162a2b401d8157bfdd02"
get "$PROBE_ROOT/stateport-execution-host.json" "$tmp/image-manifests/stateport-execution-host" "image manifest: stateport-execution-host"
check "27b70d981709099a5ce8a7999a9160f8aad96c43edf2b1a5b4b8b0c96a858def" "$tmp/image-manifests/stateport-execution-host"
mkdir -m 700 "$tmp/image-carriers/stateport-execution-host" "$tmp/image-carriers/stateport-execution-host/blobs" "$tmp/image-carriers/stateport-execution-host/blobs/sha256"
cp "$tmp/image-manifests/stateport-execution-host" "$tmp/image-carriers/stateport-execution-host/blobs/sha256/27b70d981709099a5ce8a7999a9160f8aad96c43edf2b1a5b4b8b0c96a858def"
printf '{"schemaVersion":2,"manifests":[{"digest":"sha256:27b70d981709099a5ce8a7999a9160f8aad96c43edf2b1a5b4b8b0c96a858def"}]}\n' > "$tmp/image-carriers/stateport-execution-host/index.json"
tar -cf "$tmp/image-archives/stateport-execution-host.oci.tar" --sort=name --mtime=@0 --owner=0 --group=0 --numeric-owner -C "$tmp/image-carriers/stateport-execution-host" index.json "blobs/sha256/27b70d981709099a5ce8a7999a9160f8aad96c43edf2b1a5b4b8b0c96a858def"
get "$PROBE_ROOT/stateport-playwright.json" "$tmp/image-manifests/stateport-playwright" "image manifest: stateport-playwright"
check "307892a7e0d5b46803b00a74b8ecc3ee96e3fd6a4829be237328b99df78c1a24" "$tmp/image-manifests/stateport-playwright"
mkdir -m 700 "$tmp/image-carriers/stateport-playwright" "$tmp/image-carriers/stateport-playwright/blobs" "$tmp/image-carriers/stateport-playwright/blobs/sha256"
cp "$tmp/image-manifests/stateport-playwright" "$tmp/image-carriers/stateport-playwright/blobs/sha256/307892a7e0d5b46803b00a74b8ecc3ee96e3fd6a4829be237328b99df78c1a24"
printf '{"schemaVersion":2,"manifests":[{"digest":"sha256:307892a7e0d5b46803b00a74b8ecc3ee96e3fd6a4829be237328b99df78c1a24"}]}\n' > "$tmp/image-carriers/stateport-playwright/index.json"
tar -cf "$tmp/image-archives/stateport-playwright.oci.tar" --sort=name --mtime=@0 --owner=0 --group=0 --numeric-owner -C "$tmp/image-carriers/stateport-playwright" index.json "blobs/sha256/307892a7e0d5b46803b00a74b8ecc3ee96e3fd6a4829be237328b99df78c1a24"
get "$PROBE_ROOT/stateport-runner.json" "$tmp/image-manifests/stateport-runner" "image manifest: stateport-runner"
check "5782579c7ee235ca27b0002a03ba064b14f1654bcf1b0153c60275bfd5872a0c" "$tmp/image-manifests/stateport-runner"
mkdir -m 700 "$tmp/image-carriers/stateport-runner" "$tmp/image-carriers/stateport-runner/blobs" "$tmp/image-carriers/stateport-runner/blobs/sha256"
cp "$tmp/image-manifests/stateport-runner" "$tmp/image-carriers/stateport-runner/blobs/sha256/5782579c7ee235ca27b0002a03ba064b14f1654bcf1b0153c60275bfd5872a0c"
printf '{"schemaVersion":2,"manifests":[{"digest":"sha256:5782579c7ee235ca27b0002a03ba064b14f1654bcf1b0153c60275bfd5872a0c"}]}\n' > "$tmp/image-carriers/stateport-runner/index.json"
tar -cf "$tmp/image-archives/stateport-runner.oci.tar" --sort=name --mtime=@0 --owner=0 --group=0 --numeric-owner -C "$tmp/image-carriers/stateport-runner" index.json "blobs/sha256/5782579c7ee235ca27b0002a03ba064b14f1654bcf1b0153c60275bfd5872a0c"
get "$PROBE_ROOT/stateport-web.json" "$tmp/image-manifests/stateport-web" "image manifest: stateport-web"
check "a0288e7eff247655c9e0ccbf71fc9652caad3c1fdba640c69b35cb85f8e10289" "$tmp/image-manifests/stateport-web"
mkdir -m 700 "$tmp/image-carriers/stateport-web" "$tmp/image-carriers/stateport-web/blobs" "$tmp/image-carriers/stateport-web/blobs/sha256"
cp "$tmp/image-manifests/stateport-web" "$tmp/image-carriers/stateport-web/blobs/sha256/a0288e7eff247655c9e0ccbf71fc9652caad3c1fdba640c69b35cb85f8e10289"
printf '{"schemaVersion":2,"manifests":[{"digest":"sha256:a0288e7eff247655c9e0ccbf71fc9652caad3c1fdba640c69b35cb85f8e10289"}]}\n' > "$tmp/image-carriers/stateport-web/index.json"
tar -cf "$tmp/image-archives/stateport-web.oci.tar" --sort=name --mtime=@0 --owner=0 --group=0 --numeric-owner -C "$tmp/image-carriers/stateport-web" index.json "blobs/sha256/a0288e7eff247655c9e0ccbf71fc9652caad3c1fdba640c69b35cb85f8e10289"
get "$PROBE_ROOT/stateport-worker.json" "$tmp/image-manifests/stateport-worker" "image manifest: stateport-worker"
check "38e90db24ccc31d6a7368d577eafe3872ebf11b2db7a814e95e0d22fb3fd1637" "$tmp/image-manifests/stateport-worker"
mkdir -m 700 "$tmp/image-carriers/stateport-worker" "$tmp/image-carriers/stateport-worker/blobs" "$tmp/image-carriers/stateport-worker/blobs/sha256"
cp "$tmp/image-manifests/stateport-worker" "$tmp/image-carriers/stateport-worker/blobs/sha256/38e90db24ccc31d6a7368d577eafe3872ebf11b2db7a814e95e0d22fb3fd1637"
printf '{"schemaVersion":2,"manifests":[{"digest":"sha256:38e90db24ccc31d6a7368d577eafe3872ebf11b2db7a814e95e0d22fb3fd1637"}]}\n' > "$tmp/image-carriers/stateport-worker/index.json"
tar -cf "$tmp/image-archives/stateport-worker.oci.tar" --sort=name --mtime=@0 --owner=0 --group=0 --numeric-owner -C "$tmp/image-carriers/stateport-worker" index.json "blobs/sha256/38e90db24ccc31d6a7368d577eafe3872ebf11b2db7a814e95e0d22fb3fd1637"
retain_slot() { mkdir -p -m 700 "$1"; install -m 600 "$2" "$1/$3"; }
retain_slot "$tmp/810a9a5e27e03063f155cf71481f861bf0b16855b8a74a463d3e02d8225b00e4" "$tmp/release-index.sigstore.json" "release-index.sigstore.json"
retain_slot "$tmp/5e5ee079c1de11dba0e285586eb154332334d09e649fcafd1de779bbcce3756d" "$tmp/image-bundles/stateport-api.sigstore.json" "stateport-api.sigstore.json"
retain_slot "$tmp/9d8abecb5104e75e23e8a57704f5201ad7aad7bb9dfd38d92be154a17531ea30" "$tmp/image-bundles/stateport-dev-workspace.sigstore.json" "stateport-dev-workspace.sigstore.json"
retain_slot "$tmp/2ee39ad4efdf33b20e5447b3a7f0230c62fbe8e6e0eb6eca668b89f2d2762455" "$tmp/image-bundles/stateport-execution-host.sigstore.json" "stateport-execution-host.sigstore.json"
retain_slot "$tmp/f63a1907af6d73e5b0c581e129da5cfd66383f2c6b38496419a0f2ead7b2d576" "$tmp/image-bundles/stateport-playwright.sigstore.json" "stateport-playwright.sigstore.json"
retain_slot "$tmp/ed173cd9ad511ef9c0dfb2092eeb42afa1ca941a07f6f31133ecfc38cdd4f08a" "$tmp/image-bundles/stateport-runner.sigstore.json" "stateport-runner.sigstore.json"
retain_slot "$tmp/d495486a15034420ad359ab0edfe29d69882e409ab070d5fd537536a1de190b4" "$tmp/image-bundles/stateport-web.sigstore.json" "stateport-web.sigstore.json"
retain_slot "$tmp/e5f3acf9544b7fac74873193a1fc7a7e6e8953406f320e03a581388916d7a1a1" "$tmp/image-bundles/stateport-worker.sigstore.json" "stateport-worker.sigstore.json"
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
sudo -n sh -c 'printf "%s  %s\n" "$1" "$2" | sha256sum -c --status' sh "0b35b3b4b40d4e32483e9fd884985a7731a3c763f52f62c8e55f4a5b0be8bc18" "$root_stage/installer" || fail "Sealed installer copy changed."
sudo -n sh -c 'printf "%s  %s\n" "$1" "$2" | sha256sum -c --status' sh "4629c757b7618056f8ddd7e2625ae9fdd94c0372a65049520bc7d9df9efc7f71" "$root_stage/cosign" || fail "Sealed Cosign copy changed."
sudo -n sh -c 'printf "%s  %s\n" "$1" "$2" | sha256sum -c --status' sh "e2391732872e05402c2ae8bdb018b1b64b284c2490d88197a37cf011b6f8b809" "$root_stage/release-index.json" || fail "Sealed release index changed."
sudo -n sh -c 'printf "%s  %s\n" "$1" "$2" | sha256sum -c --status' sh "810a9a5e27e03063f155cf71481f861bf0b16855b8a74a463d3e02d8225b00e4" "$root_stage/release-index.sigstore.json" || fail "Sealed release signature changed."
sudo -n sh -c 'printf "%s  %s\n" "$1" "$2" | sha256sum -c --status' sh "798d6ea6e2703993758f0fb45618b1f05b40f6ef116e7d286fd5a6867859b8ad" "$root_stage/release.pub" || fail "Sealed trust key changed."
sudo -n sh -c 'printf "%s  %s\n" "$1" "$2" | sha256sum -c --status' sh "a472bd4a28dacc2ccfc286ed35ba76d3bfaa71fc765a5b51d09b84cbc0c9ea2f" "$root_stage/podman-package-bundle.tar" || fail "Sealed package bundle changed."
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
sudo -n sh -c 'cd "$1/podman-package-bundle/packages" && dpkg -i -- *.deb' sh "$root_package_dir"
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
  --confirmed-plan-digest "$package_plan_digest" \
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
  --execution-host-provisioner-digest "sha256:3545e3216fded144b4dc783bf38ad1622b808c1e3e821ec729112bc875011d1e" \
  --execution-host-provisioner-bytes "35799" \
  --updater-wheel "$tmp/updater" --updater-wheel-digest "sha256:3c74e81f0f2902334f6e410d8f5c4698353b150751db29d360c2c5c60ae6078e" \
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
sudo -n /usr/local/libexec/stateport-execution-host-provision initialize-updater \
  --release-index "$tmp/release-index.json" --bundle-root "$tmp" \
  --cosign /usr/local/lib/stateport/tools/cosign \
  --trust-public-key /etc/stateport/alpha-2026-08-cosign.pub \
  --trust-key-id "stateport-alpha-private-2026-08" --trust-key-fingerprint "sha256:df24c1ccdcf1ecf72da6d8d81ae8b0ffaca8d399826091b107cc4d6905915ea5" \
  --channel alpha --actor-id "local-owner-$(id -un)"
printf "StatePort %s installed successfully for %s.\n" "$STATEPORT_VERSION" "$TARGET"
