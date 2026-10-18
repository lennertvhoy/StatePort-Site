#!/bin/sh
# StatePort v0.1.0-alpha.25 Windows 11 + WSL2 + Ubuntu 24.04 bootstrap.
set -eu
STATEPORT_VERSION="0.1.0-alpha.25"
RELEASE_ROOT="https://lennertvhoy.github.io/StatePort-Site/download/0.1.0-alpha.25"
PROBE_ROOT="https://lennertvhoy.github.io/StatePort-Site/download/alpha25-manifests"
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
  tmp=$(mktemp -d "${TMPDIR:-/tmp}/stateport-alpha25-probe.XXXXXX") || fail "Cannot create a private probe directory."
  trap 'rm -rf "$tmp"' EXIT
  trap 'exit 129' HUP
  trap 'exit 130' INT
  trap 'exit 143' TERM
  get "$PROBE_ROOT/stateport-api.json" "$tmp/stateport-api.manifest.json" "image manifest: stateport-api"
  check "01e411a6bb0a19892512566e47b60a88b9fc6ae5131df0904457f9e5d65e58ca" "$tmp/stateport-api.manifest.json"
  get "$PROBE_ROOT/stateport-dev-workspace.json" "$tmp/stateport-dev-workspace.manifest.json" "image manifest: stateport-dev-workspace"
  check "43683d9bdaa75b856b0e0fd4cd341ed24b69843aa1daa9b2734b892d4124ebd7" "$tmp/stateport-dev-workspace.manifest.json"
  get "$PROBE_ROOT/stateport-execution-host.json" "$tmp/stateport-execution-host.manifest.json" "image manifest: stateport-execution-host"
  check "1254955a40ec2a7c5f5153b1c20360fed4dea7691a7f8a668d35f0e67fb877c8" "$tmp/stateport-execution-host.manifest.json"
  get "$PROBE_ROOT/stateport-playwright.json" "$tmp/stateport-playwright.manifest.json" "image manifest: stateport-playwright"
  check "36089a664756f3e0226a5165b0bd166868272a49f308946d0347f4c3bd06e047" "$tmp/stateport-playwright.manifest.json"
  get "$PROBE_ROOT/stateport-runner.json" "$tmp/stateport-runner.manifest.json" "image manifest: stateport-runner"
  check "69096f2204d3c2d4839987e0b8cde5277c831edadc521e634268fd9b3403f773" "$tmp/stateport-runner.manifest.json"
  get "$PROBE_ROOT/stateport-web.json" "$tmp/stateport-web.manifest.json" "image manifest: stateport-web"
  check "46fd44cca6098451c486a783f0b5b0daa23ae178ccb35404c514e788e5b7625a" "$tmp/stateport-web.manifest.json"
  get "$PROBE_ROOT/stateport-worker.json" "$tmp/stateport-worker.manifest.json" "image manifest: stateport-worker"
  check "a07317f87f2c68f1131bb760be4ca03010eb735110c70d5ca162551762a581b7" "$tmp/stateport-worker.manifest.json"
  printf "StatePort Alpha.25 transport probe passed: bootstrap syntax and 7 exact image manifests verified; installer was not executed.\n"
  exit 0
fi
if [ "$mode" = materialization-preflight ]; then
  command -v curl >/dev/null 2>&1 || fail "curl is required for the materialization preflight."
  command -v install >/dev/null 2>&1 || fail "install is required for the materialization preflight."
  command -v sha256sum >/dev/null 2>&1 || fail "sha256sum is required for the materialization preflight."
  command -v stat >/dev/null 2>&1 || fail "stat is required for the materialization preflight."
  ensure_root_helper_parent / 0 0 check
  umask 077
  tmp=$(mktemp -d "${TMPDIR:-/tmp}/stateport-alpha25-materialization.XXXXXX") || fail "Cannot create a private preflight directory."
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
  printf "StatePort Alpha.25 materialization preflight passed: target, pinned helper transport, and absent-parent creation order verified; packages, root files, images, and installer were not changed or executed.\n"
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
check "cdadbcf3d55875a3560641cfb1e087d18ebd82ca01327c2827326a7a90128907" "$tmp/installer"
get "$RELEASE_ROOT/stateport-execution-host-provision" "$tmp/provisioner" "execution-host provisioner"
check "3545e3216fded144b4dc783bf38ad1622b808c1e3e821ec729112bc875011d1e" "$tmp/provisioner"
get "$RELEASE_ROOT/stateport-updater" "$tmp/updater" "signed updater"
check "8bfa3e1ab9a87b8b4308e54844b2508a6a1e1cdea073dfc8689266ba79313865" "$tmp/updater"
get "$RELEASE_ROOT/release-index.json" "$tmp/release-index.json" "signed release index"
check "aa4cb840136242ecf0f008b5414d6dcdf34c5c11e5a614f580f484cf1e8944d5" "$tmp/release-index.json"
get "$RELEASE_ROOT/release-index.sigstore.json" "$tmp/release-index.sigstore.json" "release index signature"
check "182f74d464615fcaf47b42158ec6e05f86e121a1576c29cfc5b7e81c8ed898d1" "$tmp/release-index.sigstore.json"
get "$RELEASE_ROOT/stateport-alpha-2026-08-cosign.pub" "$tmp/release.pub" "release trust key"
check "798d6ea6e2703993758f0fb45618b1f05b40f6ef116e7d286fd5a6867859b8ad" "$tmp/release.pub"
get "$COSIGN_URL" "$tmp/cosign" "Cosign executable"
check "4629c757b7618056f8ddd7e2625ae9fdd94c0372a65049520bc7d9df9efc7f71" "$tmp/cosign"
chmod 700 "$tmp/installer" "$tmp/cosign"
mkdir -m 700 "$tmp/predecessor-bundle"
get "$RELEASE_ROOT/predecessor-bundle/release-index.sigstore.json" "$tmp/predecessor-bundle/release-index.sigstore.json" "predecessor signature bundle"
check "28cb50d14dd078d68d7fd37fd079edfb80001e794f29355cf9d406d0d476a544" "$tmp/predecessor-bundle/release-index.sigstore.json"
mkdir -p -m 700 "$tmp/28cb50d14dd078d68d7fd37fd079edfb80001e794f29355cf9d406d0d476a544"
install -m 600 "$tmp/predecessor-bundle/release-index.sigstore.json" "$tmp/28cb50d14dd078d68d7fd37fd079edfb80001e794f29355cf9d406d0d476a544/release-index.sigstore.json"
get "$RELEASE_ROOT/signatures/stateport-api.sigstore.json" "$tmp/image-bundles/stateport-api.sigstore.json" "image signature: stateport-api"
check "4897f4e02dd7d298f1b8e259aae9d687618508660698872b6e550a3e4791b2ea" "$tmp/image-bundles/stateport-api.sigstore.json"
get "$RELEASE_ROOT/signatures/stateport-dev-workspace.sigstore.json" "$tmp/image-bundles/stateport-dev-workspace.sigstore.json" "image signature: stateport-dev-workspace"
check "7d84435a27648eba98445e7972e4def85d991740f9abb1a09287d8a01994d793" "$tmp/image-bundles/stateport-dev-workspace.sigstore.json"
get "$RELEASE_ROOT/signatures/stateport-execution-host.sigstore.json" "$tmp/image-bundles/stateport-execution-host.sigstore.json" "image signature: stateport-execution-host"
check "388148759f3d112afe31e34949781233ba78f07daee82e65f9c3fda14dc17497" "$tmp/image-bundles/stateport-execution-host.sigstore.json"
get "$RELEASE_ROOT/signatures/stateport-playwright.sigstore.json" "$tmp/image-bundles/stateport-playwright.sigstore.json" "image signature: stateport-playwright"
check "79eeec261e810039a6507b704914aac723e92f4583d14edcf4a267a3da84394b" "$tmp/image-bundles/stateport-playwright.sigstore.json"
get "$RELEASE_ROOT/signatures/stateport-runner.sigstore.json" "$tmp/image-bundles/stateport-runner.sigstore.json" "image signature: stateport-runner"
check "782b3034207c81b7cb385563d5661ea0dc5be3c28636c30201e9b48fe4af2aa8" "$tmp/image-bundles/stateport-runner.sigstore.json"
get "$RELEASE_ROOT/signatures/stateport-web.sigstore.json" "$tmp/image-bundles/stateport-web.sigstore.json" "image signature: stateport-web"
check "62a787ae18d5c26303461e1b7bf57c1135c636a33874e457b5e6db1e6d9920fe" "$tmp/image-bundles/stateport-web.sigstore.json"
get "$RELEASE_ROOT/signatures/stateport-worker.sigstore.json" "$tmp/image-bundles/stateport-worker.sigstore.json" "image signature: stateport-worker"
check "c2f63ea13b6f32d3f2edbbeee295863898132b3a910eb27855ca3a2d54010bb4" "$tmp/image-bundles/stateport-worker.sigstore.json"
get "$RELEASE_ROOT/stateport-podman-package-bundle.tar" "$tmp/podman-package-bundle.tar" "signed Podman package bundle"
check "a472bd4a28dacc2ccfc286ed35ba76d3bfaa71fc765a5b51d09b84cbc0c9ea2f" "$tmp/podman-package-bundle.tar"
get "$PROBE_ROOT/stateport-api.json" "$tmp/image-manifests/stateport-api" "image manifest: stateport-api"
check "01e411a6bb0a19892512566e47b60a88b9fc6ae5131df0904457f9e5d65e58ca" "$tmp/image-manifests/stateport-api"
mkdir -m 700 "$tmp/image-carriers/stateport-api" "$tmp/image-carriers/stateport-api/blobs" "$tmp/image-carriers/stateport-api/blobs/sha256"
cp "$tmp/image-manifests/stateport-api" "$tmp/image-carriers/stateport-api/blobs/sha256/01e411a6bb0a19892512566e47b60a88b9fc6ae5131df0904457f9e5d65e58ca"
printf '{"schemaVersion":2,"manifests":[{"digest":"sha256:01e411a6bb0a19892512566e47b60a88b9fc6ae5131df0904457f9e5d65e58ca"}]}\n' > "$tmp/image-carriers/stateport-api/index.json"
tar -cf "$tmp/image-archives/stateport-api.oci.tar" --sort=name --mtime=@0 --owner=0 --group=0 --numeric-owner -C "$tmp/image-carriers/stateport-api" index.json "blobs/sha256/01e411a6bb0a19892512566e47b60a88b9fc6ae5131df0904457f9e5d65e58ca"
get "$PROBE_ROOT/stateport-dev-workspace.json" "$tmp/image-manifests/stateport-dev-workspace" "image manifest: stateport-dev-workspace"
check "43683d9bdaa75b856b0e0fd4cd341ed24b69843aa1daa9b2734b892d4124ebd7" "$tmp/image-manifests/stateport-dev-workspace"
mkdir -m 700 "$tmp/image-carriers/stateport-dev-workspace" "$tmp/image-carriers/stateport-dev-workspace/blobs" "$tmp/image-carriers/stateport-dev-workspace/blobs/sha256"
cp "$tmp/image-manifests/stateport-dev-workspace" "$tmp/image-carriers/stateport-dev-workspace/blobs/sha256/43683d9bdaa75b856b0e0fd4cd341ed24b69843aa1daa9b2734b892d4124ebd7"
printf '{"schemaVersion":2,"manifests":[{"digest":"sha256:43683d9bdaa75b856b0e0fd4cd341ed24b69843aa1daa9b2734b892d4124ebd7"}]}\n' > "$tmp/image-carriers/stateport-dev-workspace/index.json"
tar -cf "$tmp/image-archives/stateport-dev-workspace.oci.tar" --sort=name --mtime=@0 --owner=0 --group=0 --numeric-owner -C "$tmp/image-carriers/stateport-dev-workspace" index.json "blobs/sha256/43683d9bdaa75b856b0e0fd4cd341ed24b69843aa1daa9b2734b892d4124ebd7"
get "$PROBE_ROOT/stateport-execution-host.json" "$tmp/image-manifests/stateport-execution-host" "image manifest: stateport-execution-host"
check "1254955a40ec2a7c5f5153b1c20360fed4dea7691a7f8a668d35f0e67fb877c8" "$tmp/image-manifests/stateport-execution-host"
mkdir -m 700 "$tmp/image-carriers/stateport-execution-host" "$tmp/image-carriers/stateport-execution-host/blobs" "$tmp/image-carriers/stateport-execution-host/blobs/sha256"
cp "$tmp/image-manifests/stateport-execution-host" "$tmp/image-carriers/stateport-execution-host/blobs/sha256/1254955a40ec2a7c5f5153b1c20360fed4dea7691a7f8a668d35f0e67fb877c8"
printf '{"schemaVersion":2,"manifests":[{"digest":"sha256:1254955a40ec2a7c5f5153b1c20360fed4dea7691a7f8a668d35f0e67fb877c8"}]}\n' > "$tmp/image-carriers/stateport-execution-host/index.json"
tar -cf "$tmp/image-archives/stateport-execution-host.oci.tar" --sort=name --mtime=@0 --owner=0 --group=0 --numeric-owner -C "$tmp/image-carriers/stateport-execution-host" index.json "blobs/sha256/1254955a40ec2a7c5f5153b1c20360fed4dea7691a7f8a668d35f0e67fb877c8"
get "$PROBE_ROOT/stateport-playwright.json" "$tmp/image-manifests/stateport-playwright" "image manifest: stateport-playwright"
check "36089a664756f3e0226a5165b0bd166868272a49f308946d0347f4c3bd06e047" "$tmp/image-manifests/stateport-playwright"
mkdir -m 700 "$tmp/image-carriers/stateport-playwright" "$tmp/image-carriers/stateport-playwright/blobs" "$tmp/image-carriers/stateport-playwright/blobs/sha256"
cp "$tmp/image-manifests/stateport-playwright" "$tmp/image-carriers/stateport-playwright/blobs/sha256/36089a664756f3e0226a5165b0bd166868272a49f308946d0347f4c3bd06e047"
printf '{"schemaVersion":2,"manifests":[{"digest":"sha256:36089a664756f3e0226a5165b0bd166868272a49f308946d0347f4c3bd06e047"}]}\n' > "$tmp/image-carriers/stateport-playwright/index.json"
tar -cf "$tmp/image-archives/stateport-playwright.oci.tar" --sort=name --mtime=@0 --owner=0 --group=0 --numeric-owner -C "$tmp/image-carriers/stateport-playwright" index.json "blobs/sha256/36089a664756f3e0226a5165b0bd166868272a49f308946d0347f4c3bd06e047"
get "$PROBE_ROOT/stateport-runner.json" "$tmp/image-manifests/stateport-runner" "image manifest: stateport-runner"
check "69096f2204d3c2d4839987e0b8cde5277c831edadc521e634268fd9b3403f773" "$tmp/image-manifests/stateport-runner"
mkdir -m 700 "$tmp/image-carriers/stateport-runner" "$tmp/image-carriers/stateport-runner/blobs" "$tmp/image-carriers/stateport-runner/blobs/sha256"
cp "$tmp/image-manifests/stateport-runner" "$tmp/image-carriers/stateport-runner/blobs/sha256/69096f2204d3c2d4839987e0b8cde5277c831edadc521e634268fd9b3403f773"
printf '{"schemaVersion":2,"manifests":[{"digest":"sha256:69096f2204d3c2d4839987e0b8cde5277c831edadc521e634268fd9b3403f773"}]}\n' > "$tmp/image-carriers/stateport-runner/index.json"
tar -cf "$tmp/image-archives/stateport-runner.oci.tar" --sort=name --mtime=@0 --owner=0 --group=0 --numeric-owner -C "$tmp/image-carriers/stateport-runner" index.json "blobs/sha256/69096f2204d3c2d4839987e0b8cde5277c831edadc521e634268fd9b3403f773"
get "$PROBE_ROOT/stateport-web.json" "$tmp/image-manifests/stateport-web" "image manifest: stateport-web"
check "46fd44cca6098451c486a783f0b5b0daa23ae178ccb35404c514e788e5b7625a" "$tmp/image-manifests/stateport-web"
mkdir -m 700 "$tmp/image-carriers/stateport-web" "$tmp/image-carriers/stateport-web/blobs" "$tmp/image-carriers/stateport-web/blobs/sha256"
cp "$tmp/image-manifests/stateport-web" "$tmp/image-carriers/stateport-web/blobs/sha256/46fd44cca6098451c486a783f0b5b0daa23ae178ccb35404c514e788e5b7625a"
printf '{"schemaVersion":2,"manifests":[{"digest":"sha256:46fd44cca6098451c486a783f0b5b0daa23ae178ccb35404c514e788e5b7625a"}]}\n' > "$tmp/image-carriers/stateport-web/index.json"
tar -cf "$tmp/image-archives/stateport-web.oci.tar" --sort=name --mtime=@0 --owner=0 --group=0 --numeric-owner -C "$tmp/image-carriers/stateport-web" index.json "blobs/sha256/46fd44cca6098451c486a783f0b5b0daa23ae178ccb35404c514e788e5b7625a"
get "$PROBE_ROOT/stateport-worker.json" "$tmp/image-manifests/stateport-worker" "image manifest: stateport-worker"
check "a07317f87f2c68f1131bb760be4ca03010eb735110c70d5ca162551762a581b7" "$tmp/image-manifests/stateport-worker"
mkdir -m 700 "$tmp/image-carriers/stateport-worker" "$tmp/image-carriers/stateport-worker/blobs" "$tmp/image-carriers/stateport-worker/blobs/sha256"
cp "$tmp/image-manifests/stateport-worker" "$tmp/image-carriers/stateport-worker/blobs/sha256/a07317f87f2c68f1131bb760be4ca03010eb735110c70d5ca162551762a581b7"
printf '{"schemaVersion":2,"manifests":[{"digest":"sha256:a07317f87f2c68f1131bb760be4ca03010eb735110c70d5ca162551762a581b7"}]}\n' > "$tmp/image-carriers/stateport-worker/index.json"
tar -cf "$tmp/image-archives/stateport-worker.oci.tar" --sort=name --mtime=@0 --owner=0 --group=0 --numeric-owner -C "$tmp/image-carriers/stateport-worker" index.json "blobs/sha256/a07317f87f2c68f1131bb760be4ca03010eb735110c70d5ca162551762a581b7"
retain_slot() { mkdir -p -m 700 "$1"; install -m 600 "$2" "$1/$3"; }
retain_slot "$tmp/182f74d464615fcaf47b42158ec6e05f86e121a1576c29cfc5b7e81c8ed898d1" "$tmp/release-index.sigstore.json" "release-index.sigstore.json"
retain_slot "$tmp/4897f4e02dd7d298f1b8e259aae9d687618508660698872b6e550a3e4791b2ea" "$tmp/image-bundles/stateport-api.sigstore.json" "stateport-api.sigstore.json"
retain_slot "$tmp/7d84435a27648eba98445e7972e4def85d991740f9abb1a09287d8a01994d793" "$tmp/image-bundles/stateport-dev-workspace.sigstore.json" "stateport-dev-workspace.sigstore.json"
retain_slot "$tmp/388148759f3d112afe31e34949781233ba78f07daee82e65f9c3fda14dc17497" "$tmp/image-bundles/stateport-execution-host.sigstore.json" "stateport-execution-host.sigstore.json"
retain_slot "$tmp/79eeec261e810039a6507b704914aac723e92f4583d14edcf4a267a3da84394b" "$tmp/image-bundles/stateport-playwright.sigstore.json" "stateport-playwright.sigstore.json"
retain_slot "$tmp/782b3034207c81b7cb385563d5661ea0dc5be3c28636c30201e9b48fe4af2aa8" "$tmp/image-bundles/stateport-runner.sigstore.json" "stateport-runner.sigstore.json"
retain_slot "$tmp/62a787ae18d5c26303461e1b7bf57c1135c636a33874e457b5e6db1e6d9920fe" "$tmp/image-bundles/stateport-web.sigstore.json" "stateport-web.sigstore.json"
retain_slot "$tmp/c2f63ea13b6f32d3f2edbbeee295863898132b3a910eb27855ca3a2d54010bb4" "$tmp/image-bundles/stateport-worker.sigstore.json" "stateport-worker.sigstore.json"
sudo -v
sudo apt-get update -o DPkg::Lock::Timeout=900 || { printf "StatePort apt update retry after lock contention\n" >&2; sleep 10; sudo apt-get update -o DPkg::Lock::Timeout=900; }
sudo apt-get install -y --no-install-recommends -o DPkg::Lock::Timeout=900 ca-certificates fuse3 nftables libglib2.0-0t64 libgpgme11t64 libdevmapper1.02.1 libfuse3-3 libseccomp2 libsqlite3-0 libaudit1 libselinux1 dbus-broker dbus-session-bus-common libpam-systemd systemd python3 python3-venv
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
sudo -n sh -c 'printf "%s  %s\n" "$1" "$2" | sha256sum -c --status' sh "cdadbcf3d55875a3560641cfb1e087d18ebd82ca01327c2827326a7a90128907" "$root_stage/installer" || fail "Sealed installer copy changed."
sudo -n sh -c 'printf "%s  %s\n" "$1" "$2" | sha256sum -c --status' sh "4629c757b7618056f8ddd7e2625ae9fdd94c0372a65049520bc7d9df9efc7f71" "$root_stage/cosign" || fail "Sealed Cosign copy changed."
sudo -n sh -c 'printf "%s  %s\n" "$1" "$2" | sha256sum -c --status' sh "aa4cb840136242ecf0f008b5414d6dcdf34c5c11e5a614f580f484cf1e8944d5" "$root_stage/release-index.json" || fail "Sealed release index changed."
sudo -n sh -c 'printf "%s  %s\n" "$1" "$2" | sha256sum -c --status' sh "182f74d464615fcaf47b42158ec6e05f86e121a1576c29cfc5b7e81c8ed898d1" "$root_stage/release-index.sigstore.json" || fail "Sealed release signature changed."
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
hold_packages="$(python3 -c 'import json,sys;d=json.load(open(sys.argv[1]));print(" ".join(sorted(d["packages"])))' "$tmp/podman-package-preflight.json")" && sudo -n apt-mark hold $hold_packages && printf "StatePort held sealed packages: %s\n" "$hold_packages"
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
sudo -n sh -c 'printf "%s  %s\n" "$1" "$2" | sha256sum -c --status' sh "3545e3216fded144b4dc783bf38ad1622b808c1e3e821ec729112bc875011d1e" /usr/local/libexec/stateport-execution-host-provision || fail "Installed execution-host provisioner changed."
sudo -n /usr/local/libexec/stateport-execution-host-provision materialize \
  --execution-host-provisioner /usr/local/libexec/stateport-execution-host-provision \
  --execution-host-provisioner-digest "sha256:3545e3216fded144b4dc783bf38ad1622b808c1e3e821ec729112bc875011d1e" \
  --execution-host-provisioner-bytes "35799" \
  --updater-wheel "$tmp/updater" --updater-wheel-digest "sha256:8bfa3e1ab9a87b8b4308e54844b2508a6a1e1cdea073dfc8689266ba79313865" \
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
  --channel alpha --actor-id "local-owner-$(id -un)" >"$tmp/initialize-updater.json" || fail "The StatePort updater could not be set up; StatePort itself is installed (see the message above)."
