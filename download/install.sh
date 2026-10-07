#!/bin/sh
# StatePort v0.1.0-alpha.23 Windows 11 + WSL2 + Ubuntu 24.04 bootstrap.
set -eu
STATEPORT_VERSION="0.1.0-alpha.23"
RELEASE_ROOT="https://lennertvhoy.github.io/StatePort-Site/download/0.1.0-alpha.23"
PROBE_ROOT="https://lennertvhoy.github.io/StatePort-Site/download/alpha23-manifests"
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
  tmp=$(mktemp -d "${TMPDIR:-/tmp}/stateport-alpha23-probe.XXXXXX") || fail "Cannot create a private probe directory."
  trap 'rm -rf "$tmp"' EXIT
  trap 'exit 129' HUP
  trap 'exit 130' INT
  trap 'exit 143' TERM
  get "$PROBE_ROOT/stateport-api.json" "$tmp/stateport-api.manifest.json" "image manifest: stateport-api"
  check "2d9a48b2ba80bacc1b73001a3670af4b7892aa8b99491c26c95ad02c8e936f23" "$tmp/stateport-api.manifest.json"
  get "$PROBE_ROOT/stateport-dev-workspace.json" "$tmp/stateport-dev-workspace.manifest.json" "image manifest: stateport-dev-workspace"
  check "77fd9a31f7dcd66722dc5e1253f7bf026ad0c8931224071ae6c26d08fe202da1" "$tmp/stateport-dev-workspace.manifest.json"
  get "$PROBE_ROOT/stateport-execution-host.json" "$tmp/stateport-execution-host.manifest.json" "image manifest: stateport-execution-host"
  check "4c66766b8aea81930d98edecec3339724a1b8ec2df3450c7fb54aaeae54d4a92" "$tmp/stateport-execution-host.manifest.json"
  get "$PROBE_ROOT/stateport-playwright.json" "$tmp/stateport-playwright.manifest.json" "image manifest: stateport-playwright"
  check "a8f44acd6d204d14cc2e687847bfee38c29971c7ae5c839ba09db2f9f5c7070c" "$tmp/stateport-playwright.manifest.json"
  get "$PROBE_ROOT/stateport-runner.json" "$tmp/stateport-runner.manifest.json" "image manifest: stateport-runner"
  check "9605809fb64d36bf788ada1441cdee58ddd8a358c54648d650e3cb102b651087" "$tmp/stateport-runner.manifest.json"
  get "$PROBE_ROOT/stateport-web.json" "$tmp/stateport-web.manifest.json" "image manifest: stateport-web"
  check "8d96843125a3d8159e8b90874152d9f357470e85aefceacc2ce7da0c273dec0c" "$tmp/stateport-web.manifest.json"
  get "$PROBE_ROOT/stateport-worker.json" "$tmp/stateport-worker.manifest.json" "image manifest: stateport-worker"
  check "a499002d359c520ad7333c9c3b736d9d02988b2b4f2e33f1f35b4c8a873c2276" "$tmp/stateport-worker.manifest.json"
  printf "StatePort Alpha.23 transport probe passed: bootstrap syntax and 7 exact image manifests verified; installer was not executed.\n"
  exit 0
fi
if [ "$mode" = materialization-preflight ]; then
  command -v curl >/dev/null 2>&1 || fail "curl is required for the materialization preflight."
  command -v install >/dev/null 2>&1 || fail "install is required for the materialization preflight."
  command -v sha256sum >/dev/null 2>&1 || fail "sha256sum is required for the materialization preflight."
  command -v stat >/dev/null 2>&1 || fail "stat is required for the materialization preflight."
  ensure_root_helper_parent / 0 0 check
  umask 077
  tmp=$(mktemp -d "${TMPDIR:-/tmp}/stateport-alpha23-materialization.XXXXXX") || fail "Cannot create a private preflight directory."
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
  printf "StatePort Alpha.23 materialization preflight passed: target, pinned helper transport, and absent-parent creation order verified; packages, root files, images, and installer were not changed or executed.\n"
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
check "dbaf3f0b0e46aa05a87d8a4ffc3f2d7840204b1bbfebdc3097172506189566db" "$tmp/installer"
get "$RELEASE_ROOT/stateport-execution-host-provision" "$tmp/provisioner" "execution-host provisioner"
check "3545e3216fded144b4dc783bf38ad1622b808c1e3e821ec729112bc875011d1e" "$tmp/provisioner"
get "$RELEASE_ROOT/stateport-updater" "$tmp/updater" "signed updater"
check "a006515afe6a7617dca014bd96e4cb437cd75bc9e3767c3da77aef6cfa5cea27" "$tmp/updater"
get "$RELEASE_ROOT/release-index.json" "$tmp/release-index.json" "signed release index"
check "e6bc7a35d5f6b6c080a7b2e439c51572b07819e7e0c12279d839049c1bd7d696" "$tmp/release-index.json"
get "$RELEASE_ROOT/release-index.sigstore.json" "$tmp/release-index.sigstore.json" "release index signature"
check "0975911176b75331383469106e48e68fb00625ec05b334fdc2ee1db88e3527c9" "$tmp/release-index.sigstore.json"
get "$RELEASE_ROOT/stateport-alpha-2026-08-cosign.pub" "$tmp/release.pub" "release trust key"
check "798d6ea6e2703993758f0fb45618b1f05b40f6ef116e7d286fd5a6867859b8ad" "$tmp/release.pub"
get "$COSIGN_URL" "$tmp/cosign" "Cosign executable"
check "4629c757b7618056f8ddd7e2625ae9fdd94c0372a65049520bc7d9df9efc7f71" "$tmp/cosign"
chmod 700 "$tmp/installer" "$tmp/cosign"
mkdir -m 700 "$tmp/predecessor-bundle"
get "$RELEASE_ROOT/predecessor-bundle/release-index.sigstore.json" "$tmp/predecessor-bundle/release-index.sigstore.json" "predecessor signature bundle"
check "61470f8c81f8d0f54899b33b9d501ff3997c1899be8e892aee16ceec8ddd2e7d" "$tmp/predecessor-bundle/release-index.sigstore.json"
mkdir -p -m 700 "$tmp/61470f8c81f8d0f54899b33b9d501ff3997c1899be8e892aee16ceec8ddd2e7d"
install -m 600 "$tmp/predecessor-bundle/release-index.sigstore.json" "$tmp/61470f8c81f8d0f54899b33b9d501ff3997c1899be8e892aee16ceec8ddd2e7d/release-index.sigstore.json"
get "$RELEASE_ROOT/signatures/stateport-api.sigstore.json" "$tmp/image-bundles/stateport-api.sigstore.json" "image signature: stateport-api"
check "b0d9ca385193f03a3cd095f7c9f98bb42fd732fde24022d01b3d41350bcc212b" "$tmp/image-bundles/stateport-api.sigstore.json"
get "$RELEASE_ROOT/signatures/stateport-dev-workspace.sigstore.json" "$tmp/image-bundles/stateport-dev-workspace.sigstore.json" "image signature: stateport-dev-workspace"
check "97c8d1835c7aaa836e964ac035d1376cc645925b47431e260795845d81625104" "$tmp/image-bundles/stateport-dev-workspace.sigstore.json"
get "$RELEASE_ROOT/signatures/stateport-execution-host.sigstore.json" "$tmp/image-bundles/stateport-execution-host.sigstore.json" "image signature: stateport-execution-host"
check "69f47e2027d88021f333b80cf653bdcc1e63bd541e80aea8d729622f9f5d96f2" "$tmp/image-bundles/stateport-execution-host.sigstore.json"
get "$RELEASE_ROOT/signatures/stateport-playwright.sigstore.json" "$tmp/image-bundles/stateport-playwright.sigstore.json" "image signature: stateport-playwright"
check "2739fb387f934b9f2eccc28005be126f9c52be8f595c70239d3cca710e90f2c2" "$tmp/image-bundles/stateport-playwright.sigstore.json"
get "$RELEASE_ROOT/signatures/stateport-runner.sigstore.json" "$tmp/image-bundles/stateport-runner.sigstore.json" "image signature: stateport-runner"
check "2203a3a1fbf8aafbf7338e9f56e767aa8e5c58e4f796fbedaa55c4989afd3a6a" "$tmp/image-bundles/stateport-runner.sigstore.json"
get "$RELEASE_ROOT/signatures/stateport-web.sigstore.json" "$tmp/image-bundles/stateport-web.sigstore.json" "image signature: stateport-web"
check "4afcc756835bbb1830d76151147135ca40e3851a419b8dffd12ce517c25be7f8" "$tmp/image-bundles/stateport-web.sigstore.json"
get "$RELEASE_ROOT/signatures/stateport-worker.sigstore.json" "$tmp/image-bundles/stateport-worker.sigstore.json" "image signature: stateport-worker"
check "89c39531cda6f956a5fb8ee0fd048b366ee73d3cb598241ee7347a8750503f2e" "$tmp/image-bundles/stateport-worker.sigstore.json"
get "$RELEASE_ROOT/stateport-podman-package-bundle.tar" "$tmp/podman-package-bundle.tar" "signed Podman package bundle"
check "a472bd4a28dacc2ccfc286ed35ba76d3bfaa71fc765a5b51d09b84cbc0c9ea2f" "$tmp/podman-package-bundle.tar"
get "$PROBE_ROOT/stateport-api.json" "$tmp/image-manifests/stateport-api" "image manifest: stateport-api"
check "2d9a48b2ba80bacc1b73001a3670af4b7892aa8b99491c26c95ad02c8e936f23" "$tmp/image-manifests/stateport-api"
mkdir -m 700 "$tmp/image-carriers/stateport-api" "$tmp/image-carriers/stateport-api/blobs" "$tmp/image-carriers/stateport-api/blobs/sha256"
cp "$tmp/image-manifests/stateport-api" "$tmp/image-carriers/stateport-api/blobs/sha256/2d9a48b2ba80bacc1b73001a3670af4b7892aa8b99491c26c95ad02c8e936f23"
printf '{"schemaVersion":2,"manifests":[{"digest":"sha256:2d9a48b2ba80bacc1b73001a3670af4b7892aa8b99491c26c95ad02c8e936f23"}]}\n' > "$tmp/image-carriers/stateport-api/index.json"
tar -cf "$tmp/image-archives/stateport-api.oci.tar" --sort=name --mtime=@0 --owner=0 --group=0 --numeric-owner -C "$tmp/image-carriers/stateport-api" index.json "blobs/sha256/2d9a48b2ba80bacc1b73001a3670af4b7892aa8b99491c26c95ad02c8e936f23"
get "$PROBE_ROOT/stateport-dev-workspace.json" "$tmp/image-manifests/stateport-dev-workspace" "image manifest: stateport-dev-workspace"
check "77fd9a31f7dcd66722dc5e1253f7bf026ad0c8931224071ae6c26d08fe202da1" "$tmp/image-manifests/stateport-dev-workspace"
mkdir -m 700 "$tmp/image-carriers/stateport-dev-workspace" "$tmp/image-carriers/stateport-dev-workspace/blobs" "$tmp/image-carriers/stateport-dev-workspace/blobs/sha256"
cp "$tmp/image-manifests/stateport-dev-workspace" "$tmp/image-carriers/stateport-dev-workspace/blobs/sha256/77fd9a31f7dcd66722dc5e1253f7bf026ad0c8931224071ae6c26d08fe202da1"
printf '{"schemaVersion":2,"manifests":[{"digest":"sha256:77fd9a31f7dcd66722dc5e1253f7bf026ad0c8931224071ae6c26d08fe202da1"}]}\n' > "$tmp/image-carriers/stateport-dev-workspace/index.json"
tar -cf "$tmp/image-archives/stateport-dev-workspace.oci.tar" --sort=name --mtime=@0 --owner=0 --group=0 --numeric-owner -C "$tmp/image-carriers/stateport-dev-workspace" index.json "blobs/sha256/77fd9a31f7dcd66722dc5e1253f7bf026ad0c8931224071ae6c26d08fe202da1"
get "$PROBE_ROOT/stateport-execution-host.json" "$tmp/image-manifests/stateport-execution-host" "image manifest: stateport-execution-host"
check "4c66766b8aea81930d98edecec3339724a1b8ec2df3450c7fb54aaeae54d4a92" "$tmp/image-manifests/stateport-execution-host"
mkdir -m 700 "$tmp/image-carriers/stateport-execution-host" "$tmp/image-carriers/stateport-execution-host/blobs" "$tmp/image-carriers/stateport-execution-host/blobs/sha256"
cp "$tmp/image-manifests/stateport-execution-host" "$tmp/image-carriers/stateport-execution-host/blobs/sha256/4c66766b8aea81930d98edecec3339724a1b8ec2df3450c7fb54aaeae54d4a92"
printf '{"schemaVersion":2,"manifests":[{"digest":"sha256:4c66766b8aea81930d98edecec3339724a1b8ec2df3450c7fb54aaeae54d4a92"}]}\n' > "$tmp/image-carriers/stateport-execution-host/index.json"
tar -cf "$tmp/image-archives/stateport-execution-host.oci.tar" --sort=name --mtime=@0 --owner=0 --group=0 --numeric-owner -C "$tmp/image-carriers/stateport-execution-host" index.json "blobs/sha256/4c66766b8aea81930d98edecec3339724a1b8ec2df3450c7fb54aaeae54d4a92"
get "$PROBE_ROOT/stateport-playwright.json" "$tmp/image-manifests/stateport-playwright" "image manifest: stateport-playwright"
check "a8f44acd6d204d14cc2e687847bfee38c29971c7ae5c839ba09db2f9f5c7070c" "$tmp/image-manifests/stateport-playwright"
mkdir -m 700 "$tmp/image-carriers/stateport-playwright" "$tmp/image-carriers/stateport-playwright/blobs" "$tmp/image-carriers/stateport-playwright/blobs/sha256"
cp "$tmp/image-manifests/stateport-playwright" "$tmp/image-carriers/stateport-playwright/blobs/sha256/a8f44acd6d204d14cc2e687847bfee38c29971c7ae5c839ba09db2f9f5c7070c"
printf '{"schemaVersion":2,"manifests":[{"digest":"sha256:a8f44acd6d204d14cc2e687847bfee38c29971c7ae5c839ba09db2f9f5c7070c"}]}\n' > "$tmp/image-carriers/stateport-playwright/index.json"
tar -cf "$tmp/image-archives/stateport-playwright.oci.tar" --sort=name --mtime=@0 --owner=0 --group=0 --numeric-owner -C "$tmp/image-carriers/stateport-playwright" index.json "blobs/sha256/a8f44acd6d204d14cc2e687847bfee38c29971c7ae5c839ba09db2f9f5c7070c"
get "$PROBE_ROOT/stateport-runner.json" "$tmp/image-manifests/stateport-runner" "image manifest: stateport-runner"
check "9605809fb64d36bf788ada1441cdee58ddd8a358c54648d650e3cb102b651087" "$tmp/image-manifests/stateport-runner"
mkdir -m 700 "$tmp/image-carriers/stateport-runner" "$tmp/image-carriers/stateport-runner/blobs" "$tmp/image-carriers/stateport-runner/blobs/sha256"
cp "$tmp/image-manifests/stateport-runner" "$tmp/image-carriers/stateport-runner/blobs/sha256/9605809fb64d36bf788ada1441cdee58ddd8a358c54648d650e3cb102b651087"
printf '{"schemaVersion":2,"manifests":[{"digest":"sha256:9605809fb64d36bf788ada1441cdee58ddd8a358c54648d650e3cb102b651087"}]}\n' > "$tmp/image-carriers/stateport-runner/index.json"
tar -cf "$tmp/image-archives/stateport-runner.oci.tar" --sort=name --mtime=@0 --owner=0 --group=0 --numeric-owner -C "$tmp/image-carriers/stateport-runner" index.json "blobs/sha256/9605809fb64d36bf788ada1441cdee58ddd8a358c54648d650e3cb102b651087"
get "$PROBE_ROOT/stateport-web.json" "$tmp/image-manifests/stateport-web" "image manifest: stateport-web"
check "8d96843125a3d8159e8b90874152d9f357470e85aefceacc2ce7da0c273dec0c" "$tmp/image-manifests/stateport-web"
mkdir -m 700 "$tmp/image-carriers/stateport-web" "$tmp/image-carriers/stateport-web/blobs" "$tmp/image-carriers/stateport-web/blobs/sha256"
cp "$tmp/image-manifests/stateport-web" "$tmp/image-carriers/stateport-web/blobs/sha256/8d96843125a3d8159e8b90874152d9f357470e85aefceacc2ce7da0c273dec0c"
printf '{"schemaVersion":2,"manifests":[{"digest":"sha256:8d96843125a3d8159e8b90874152d9f357470e85aefceacc2ce7da0c273dec0c"}]}\n' > "$tmp/image-carriers/stateport-web/index.json"
tar -cf "$tmp/image-archives/stateport-web.oci.tar" --sort=name --mtime=@0 --owner=0 --group=0 --numeric-owner -C "$tmp/image-carriers/stateport-web" index.json "blobs/sha256/8d96843125a3d8159e8b90874152d9f357470e85aefceacc2ce7da0c273dec0c"
get "$PROBE_ROOT/stateport-worker.json" "$tmp/image-manifests/stateport-worker" "image manifest: stateport-worker"
check "a499002d359c520ad7333c9c3b736d9d02988b2b4f2e33f1f35b4c8a873c2276" "$tmp/image-manifests/stateport-worker"
mkdir -m 700 "$tmp/image-carriers/stateport-worker" "$tmp/image-carriers/stateport-worker/blobs" "$tmp/image-carriers/stateport-worker/blobs/sha256"
cp "$tmp/image-manifests/stateport-worker" "$tmp/image-carriers/stateport-worker/blobs/sha256/a499002d359c520ad7333c9c3b736d9d02988b2b4f2e33f1f35b4c8a873c2276"
printf '{"schemaVersion":2,"manifests":[{"digest":"sha256:a499002d359c520ad7333c9c3b736d9d02988b2b4f2e33f1f35b4c8a873c2276"}]}\n' > "$tmp/image-carriers/stateport-worker/index.json"
tar -cf "$tmp/image-archives/stateport-worker.oci.tar" --sort=name --mtime=@0 --owner=0 --group=0 --numeric-owner -C "$tmp/image-carriers/stateport-worker" index.json "blobs/sha256/a499002d359c520ad7333c9c3b736d9d02988b2b4f2e33f1f35b4c8a873c2276"
retain_slot() { mkdir -p -m 700 "$1"; install -m 600 "$2" "$1/$3"; }
retain_slot "$tmp/0975911176b75331383469106e48e68fb00625ec05b334fdc2ee1db88e3527c9" "$tmp/release-index.sigstore.json" "release-index.sigstore.json"
retain_slot "$tmp/b0d9ca385193f03a3cd095f7c9f98bb42fd732fde24022d01b3d41350bcc212b" "$tmp/image-bundles/stateport-api.sigstore.json" "stateport-api.sigstore.json"
retain_slot "$tmp/97c8d1835c7aaa836e964ac035d1376cc645925b47431e260795845d81625104" "$tmp/image-bundles/stateport-dev-workspace.sigstore.json" "stateport-dev-workspace.sigstore.json"
retain_slot "$tmp/69f47e2027d88021f333b80cf653bdcc1e63bd541e80aea8d729622f9f5d96f2" "$tmp/image-bundles/stateport-execution-host.sigstore.json" "stateport-execution-host.sigstore.json"
retain_slot "$tmp/2739fb387f934b9f2eccc28005be126f9c52be8f595c70239d3cca710e90f2c2" "$tmp/image-bundles/stateport-playwright.sigstore.json" "stateport-playwright.sigstore.json"
retain_slot "$tmp/2203a3a1fbf8aafbf7338e9f56e767aa8e5c58e4f796fbedaa55c4989afd3a6a" "$tmp/image-bundles/stateport-runner.sigstore.json" "stateport-runner.sigstore.json"
retain_slot "$tmp/4afcc756835bbb1830d76151147135ca40e3851a419b8dffd12ce517c25be7f8" "$tmp/image-bundles/stateport-web.sigstore.json" "stateport-web.sigstore.json"
retain_slot "$tmp/89c39531cda6f956a5fb8ee0fd048b366ee73d3cb598241ee7347a8750503f2e" "$tmp/image-bundles/stateport-worker.sigstore.json" "stateport-worker.sigstore.json"
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
sudo -n sh -c 'printf "%s  %s\n" "$1" "$2" | sha256sum -c --status' sh "dbaf3f0b0e46aa05a87d8a4ffc3f2d7840204b1bbfebdc3097172506189566db" "$root_stage/installer" || fail "Sealed installer copy changed."
sudo -n sh -c 'printf "%s  %s\n" "$1" "$2" | sha256sum -c --status' sh "4629c757b7618056f8ddd7e2625ae9fdd94c0372a65049520bc7d9df9efc7f71" "$root_stage/cosign" || fail "Sealed Cosign copy changed."
sudo -n sh -c 'printf "%s  %s\n" "$1" "$2" | sha256sum -c --status' sh "e6bc7a35d5f6b6c080a7b2e439c51572b07819e7e0c12279d839049c1bd7d696" "$root_stage/release-index.json" || fail "Sealed release index changed."
sudo -n sh -c 'printf "%s  %s\n" "$1" "$2" | sha256sum -c --status' sh "0975911176b75331383469106e48e68fb00625ec05b334fdc2ee1db88e3527c9" "$root_stage/release-index.sigstore.json" || fail "Sealed release signature changed."
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
sudo -n /usr/local/libexec/stateport-execution-host-provision materialize \
  --execution-host-provisioner /usr/local/libexec/stateport-execution-host-provision \
  --execution-host-provisioner-digest "sha256:3545e3216fded144b4dc783bf38ad1622b808c1e3e821ec729112bc875011d1e" \
  --execution-host-provisioner-bytes "35799" \
  --updater-wheel "$tmp/updater" --updater-wheel-digest "sha256:a006515afe6a7617dca014bd96e4cb437cd75bc9e3767c3da77aef6cfa5cea27" \
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
