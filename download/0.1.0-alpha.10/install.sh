#!/bin/sh
# StatePort v0.1.0-alpha.10 Windows 11 + WSL2 + Ubuntu 24.04 bootstrap.
set -eu
STATEPORT_VERSION="0.1.0-alpha.10"
RELEASE_ROOT="https://lennertvhoy.github.io/StatePort-Site/download/0.1.0-alpha.10"
PROBE_ROOT="https://lennertvhoy.github.io/StatePort-Site/download/alpha10-manifests"
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
  tmp=$(mktemp -d "${TMPDIR:-/tmp}/stateport-alpha10-probe.XXXXXX") || fail "Cannot create a private probe directory."
  trap 'rm -rf "$tmp"' EXIT
  trap 'exit 129' HUP
  trap 'exit 130' INT
  trap 'exit 143' TERM
  get "$PROBE_ROOT/stateport-api.json" "$tmp/stateport-api.manifest.json" "image manifest: stateport-api"
  check "bfd04f5c9d59f08418557cef0345c7fe30e0e78718fc22cc6d528e741c8ca895" "$tmp/stateport-api.manifest.json"
  get "$PROBE_ROOT/stateport-dev-workspace.json" "$tmp/stateport-dev-workspace.manifest.json" "image manifest: stateport-dev-workspace"
  check "7d91f5bd383fb93cee979ed7226082c8c88f062b222d7f9f78534f4ce0ce06a0" "$tmp/stateport-dev-workspace.manifest.json"
  get "$PROBE_ROOT/stateport-execution-host.json" "$tmp/stateport-execution-host.manifest.json" "image manifest: stateport-execution-host"
  check "fcbf04af84c590038da50c9799cea6c58953a8d3c84c87ef1433def028c3f6d7" "$tmp/stateport-execution-host.manifest.json"
  get "$PROBE_ROOT/stateport-playwright.json" "$tmp/stateport-playwright.manifest.json" "image manifest: stateport-playwright"
  check "c51603a29f260b359ac1c002af15684264bfa9986fe502c8c9a1300139abcc59" "$tmp/stateport-playwright.manifest.json"
  get "$PROBE_ROOT/stateport-runner.json" "$tmp/stateport-runner.manifest.json" "image manifest: stateport-runner"
  check "0534422ca6b116fff08f675cfa0e22ffe9d3f52d95f3e14757b63988dab60160" "$tmp/stateport-runner.manifest.json"
  get "$PROBE_ROOT/stateport-web.json" "$tmp/stateport-web.manifest.json" "image manifest: stateport-web"
  check "6984bfa338f2903b00d4a0329adf69c038806cd08346e108dd143024273cb704" "$tmp/stateport-web.manifest.json"
  get "$PROBE_ROOT/stateport-worker.json" "$tmp/stateport-worker.manifest.json" "image manifest: stateport-worker"
  check "46d04e8c274192eb980ebeb89ae177abbef1f409a9e6c0b6dddf2acdcb468a23" "$tmp/stateport-worker.manifest.json"
  printf "StatePort Alpha.10 transport probe passed: bootstrap syntax and 7 exact image manifests verified; installer was not executed.\n"
  exit 0
fi
if [ "$mode" = materialization-preflight ]; then
  command -v curl >/dev/null 2>&1 || fail "curl is required for the materialization preflight."
  command -v install >/dev/null 2>&1 || fail "install is required for the materialization preflight."
  command -v sha256sum >/dev/null 2>&1 || fail "sha256sum is required for the materialization preflight."
  command -v stat >/dev/null 2>&1 || fail "stat is required for the materialization preflight."
  ensure_root_helper_parent / 0 0 check
  umask 077
  tmp=$(mktemp -d "${TMPDIR:-/tmp}/stateport-alpha10-materialization.XXXXXX") || fail "Cannot create a private preflight directory."
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
  printf "StatePort Alpha.10 materialization preflight passed: target, pinned helper transport, and absent-parent creation order verified; packages, root files, images, and installer were not changed or executed.\n"
  exit 0
fi
command -v sudo >/dev/null 2>&1 || fail "sudo is required."
printf "StatePort %s will install the WSL2 runtime and signed alpha. Type install: " "$STATEPORT_VERSION" >/dev/tty
IFS= read -r answer </dev/tty || answer=
[ "$answer" = install ] || fail "Installation not confirmed."
sudo -v
sudo apt-get update -o DPkg::Lock::Timeout=300 || { printf "StatePort apt update retry after lock contention\n" >&2; sleep 10; sudo apt-get update -o DPkg::Lock::Timeout=300; }
sudo apt-get install -y -o DPkg::Lock::Timeout=300 ca-certificates curl python3 python3-venv podman skopeo uidmap slirp4netns fuse-overlayfs dbus-user-session
sudo loginctl enable-linger "$USER"
command -v curl >/dev/null 2>&1 || fail "curl installation failed."
command -v skopeo >/dev/null 2>&1 || fail "skopeo installation failed."
command -v tar >/dev/null 2>&1 || fail "tar is required."
command -v sha256sum >/dev/null 2>&1 || fail "sha256sum is required."
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
check "8e8dbe88393d9a90b96727911a3eb7930ecae11b75e1099961560ec3c62d0df0" "$tmp/installer"
get "$RELEASE_ROOT/stateport-execution-host-provision" "$tmp/provisioner" "execution-host provisioner"
check "312ef592fb05bb45458b8f58e5551f0e5594bde2111d90555267494785da6d32" "$tmp/provisioner"
get "$RELEASE_ROOT/stateport-updater" "$tmp/updater" "signed updater"
check "cf083edb278b1d21ae8ec1062b6a81e73b133ef6d69243a9191612d832be2ae0" "$tmp/updater"
get "$RELEASE_ROOT/release-index.json" "$tmp/release-index.json" "signed release index"
check "2fc626fcab180f664f04f36d1fcceacaffa81ca96a658585f6684e3cf37abf89" "$tmp/release-index.json"
get "$RELEASE_ROOT/release-index.sigstore.json" "$tmp/release-index.sigstore.json" "release index signature"
check "db7814299a7603088e1a0cac3845a0c4be7a165465537bc7710957ecf5499b11" "$tmp/release-index.sigstore.json"
get "$RELEASE_ROOT/stateport-alpha-2026-08-cosign.pub" "$tmp/release.pub" "release trust key"
check "798d6ea6e2703993758f0fb45618b1f05b40f6ef116e7d286fd5a6867859b8ad" "$tmp/release.pub"
get "$COSIGN_URL" "$tmp/cosign" "Cosign executable"
check "4629c757b7618056f8ddd7e2625ae9fdd94c0372a65049520bc7d9df9efc7f71" "$tmp/cosign"
chmod 700 "$tmp/installer" "$tmp/cosign"
get "$RELEASE_ROOT/signatures/stateport-api.sigstore.json" "$tmp/image-bundles/stateport-api.sigstore.json" "image signature: stateport-api"
check "0ec448caad0230d9dad906901254f26d65999fc73c07c8d8b8008471fdfeaf9e" "$tmp/image-bundles/stateport-api.sigstore.json"
get "$RELEASE_ROOT/signatures/stateport-dev-workspace.sigstore.json" "$tmp/image-bundles/stateport-dev-workspace.sigstore.json" "image signature: stateport-dev-workspace"
check "b0238ded9fe803adbe869fc2a1fb395a6862b0f89912c2954c5ea805f8525d63" "$tmp/image-bundles/stateport-dev-workspace.sigstore.json"
get "$RELEASE_ROOT/signatures/stateport-execution-host.sigstore.json" "$tmp/image-bundles/stateport-execution-host.sigstore.json" "image signature: stateport-execution-host"
check "0b8df9c1c037b62b68e24fe31aec332b64603c540fb0423e05d2ada1907d7749" "$tmp/image-bundles/stateport-execution-host.sigstore.json"
get "$RELEASE_ROOT/signatures/stateport-playwright.sigstore.json" "$tmp/image-bundles/stateport-playwright.sigstore.json" "image signature: stateport-playwright"
check "44de023416958a2bb6da9d7543631b11df9e1a30ba23d79b589b74837f23c46b" "$tmp/image-bundles/stateport-playwright.sigstore.json"
get "$RELEASE_ROOT/signatures/stateport-runner.sigstore.json" "$tmp/image-bundles/stateport-runner.sigstore.json" "image signature: stateport-runner"
check "27495cadb8ba7065a7f071aa0956741aaa5f0b5424e2af97ba62b887b6bfac04" "$tmp/image-bundles/stateport-runner.sigstore.json"
get "$RELEASE_ROOT/signatures/stateport-web.sigstore.json" "$tmp/image-bundles/stateport-web.sigstore.json" "image signature: stateport-web"
check "c2fa1c3a5963085f43aefdb80a7386b1acf1cb18156190080a1629309a7ed3a9" "$tmp/image-bundles/stateport-web.sigstore.json"
get "$RELEASE_ROOT/signatures/stateport-worker.sigstore.json" "$tmp/image-bundles/stateport-worker.sigstore.json" "image signature: stateport-worker"
check "d648fff90b6731e903f6061451344c4a78ed3c26fb7148e5e7e5858d06ea4a96" "$tmp/image-bundles/stateport-worker.sigstore.json"
manifest_carrier stateport-api ghcr.io/lennertvhoy/stateport-api@sha256:bfd04f5c9d59f08418557cef0345c7fe30e0e78718fc22cc6d528e741c8ca895 sha256:bfd04f5c9d59f08418557cef0345c7fe30e0e78718fc22cc6d528e741c8ca895
manifest_carrier stateport-dev-workspace ghcr.io/lennertvhoy/stateport-dev-workspace@sha256:7d91f5bd383fb93cee979ed7226082c8c88f062b222d7f9f78534f4ce0ce06a0 sha256:7d91f5bd383fb93cee979ed7226082c8c88f062b222d7f9f78534f4ce0ce06a0
manifest_carrier stateport-execution-host ghcr.io/lennertvhoy/stateport-execution-host@sha256:fcbf04af84c590038da50c9799cea6c58953a8d3c84c87ef1433def028c3f6d7 sha256:fcbf04af84c590038da50c9799cea6c58953a8d3c84c87ef1433def028c3f6d7
manifest_carrier stateport-playwright ghcr.io/lennertvhoy/stateport-playwright@sha256:c51603a29f260b359ac1c002af15684264bfa9986fe502c8c9a1300139abcc59 sha256:c51603a29f260b359ac1c002af15684264bfa9986fe502c8c9a1300139abcc59
manifest_carrier stateport-runner ghcr.io/lennertvhoy/stateport-runner@sha256:0534422ca6b116fff08f675cfa0e22ffe9d3f52d95f3e14757b63988dab60160 sha256:0534422ca6b116fff08f675cfa0e22ffe9d3f52d95f3e14757b63988dab60160
manifest_carrier stateport-web ghcr.io/lennertvhoy/stateport-web@sha256:6984bfa338f2903b00d4a0329adf69c038806cd08346e108dd143024273cb704 sha256:6984bfa338f2903b00d4a0329adf69c038806cd08346e108dd143024273cb704
manifest_carrier stateport-worker ghcr.io/lennertvhoy/stateport-worker@sha256:46d04e8c274192eb980ebeb89ae177abbef1f409a9e6c0b6dddf2acdcb468a23 sha256:46d04e8c274192eb980ebeb89ae177abbef1f409a9e6c0b6dddf2acdcb468a23
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
  --channel alpha \
  --cosign "$tmp/cosign" \
  --installer-path "$tmp/installer" \
  --execution-host-receipt "$RECEIPT" \
  --state-root "$STATE_ROOT" \
  --yes \
  --prepare-execution-host
sudo -v
ensure_root_helper_parent / 0 0 sudo
sudo -n install -o root -g root -m 0555 "$tmp/provisioner" /usr/local/libexec/stateport-execution-host-provision
sudo -n /usr/local/libexec/stateport-execution-host-provision materialize \
  --execution-host-provisioner /usr/local/libexec/stateport-execution-host-provision \
  --execution-host-provisioner-digest "sha256:312ef592fb05bb45458b8f58e5551f0e5594bde2111d90555267494785da6d32" \
  --execution-host-provisioner-bytes "35615" \
  --updater-wheel "$tmp/updater" --updater-wheel-digest "sha256:cf083edb278b1d21ae8ec1062b6a81e73b133ef6d69243a9191612d832be2ae0" \
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
  --channel alpha \
  --cosign "$tmp/cosign" \
  --installer-path "$tmp/installer" \
  --execution-host-receipt "$RECEIPT" \
  --state-root "$STATE_ROOT" \
  --yes
printf "StatePort %s installed successfully for %s.\n" "$STATEPORT_VERSION" "$TARGET"
