#!/bin/sh
# StatePort v0.1.0-alpha.5 Windows 11 + WSL2 + Ubuntu 24.04 bootstrap.
set -eu
VERSION="0.1.0-alpha.5"
RELEASE_ROOT="https://lennertvhoy.github.io/StatePort-Site/download/0.1.0-alpha.5"
PROBE_ROOT="https://lennertvhoy.github.io/StatePort-Site/download/alpha5-manifests"
TARGET="wsl2-ubuntu2404-linux-amd64-rootless-podman-quadlet"
STATE_ROOT="${STATEPORT_STATE_ROOT:-$HOME/.local/state/stateport-install}"
RECEIPT="/var/lib/stateport-provisioning/receipts/execution-host-provisioning-receipt.json"
COSIGN_URL="https://github.com/sigstore/cosign/releases/download/v3.1.2/cosign-linux-amd64"
fail() { printf "StatePort install: %s\n" "$*" >&2; exit 1; }
mode=install
case "${1-}" in --transport-probe) mode=probe; shift ;; "") ;; *) fail "Usage: $0 [--transport-probe]" ;; esac
[ "$#" -eq 0 ] || fail "Usage: $0 [--transport-probe]"
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
if [ "$mode" = probe ]; then
  command -v curl >/dev/null 2>&1 || fail "curl is required for the transport probe."
  command -v sha256sum >/dev/null 2>&1 || fail "sha256sum is required for the transport probe."
  umask 077
  tmp=$(mktemp -d "${TMPDIR:-/tmp}/stateport-alpha5-probe.XXXXXX") || fail "Cannot create a private probe directory."
  trap 'rm -rf "$tmp"' EXIT HUP INT TERM
  get() { curl -fsSL --proto "=https" --tlsv1.2 --retry 3 -o "$2" "$1"; }
  check() { printf "%s  %s\n" "$1" "$2" | sha256sum -c --status || fail "Checksum failed: $2"; }
  get "$PROBE_ROOT/stateport-api.json" "$tmp/stateport-api.manifest.json"
  check "a5c639880195ba6dc57fa9c13378fdf0cdb0361f08cbddea7b7e90f476906af8" "$tmp/stateport-api.manifest.json"
  get "$PROBE_ROOT/stateport-dev-workspace.json" "$tmp/stateport-dev-workspace.manifest.json"
  check "1a9eecc2a087620e7139570e09c08b4ce6c17a8369d2b428551809dff3fda886" "$tmp/stateport-dev-workspace.manifest.json"
  get "$PROBE_ROOT/stateport-execution-host.json" "$tmp/stateport-execution-host.manifest.json"
  check "02d3ce6d6dfdacc164b947c1c88ebf6c64e0a103b05fbd420454083db589efb2" "$tmp/stateport-execution-host.manifest.json"
  get "$PROBE_ROOT/stateport-playwright.json" "$tmp/stateport-playwright.manifest.json"
  check "a5e8bc89bd193bd149dcad3de03366796bcc8f903f019e9e599f928dfaed9096" "$tmp/stateport-playwright.manifest.json"
  get "$PROBE_ROOT/stateport-runner.json" "$tmp/stateport-runner.manifest.json"
  check "45b5aaf0cd18699a66371ed800683ad5740b491d1442d9c1edd90d87089786ae" "$tmp/stateport-runner.manifest.json"
  get "$PROBE_ROOT/stateport-web.json" "$tmp/stateport-web.manifest.json"
  check "57f625f36c590c1440d70f07a3aa1bee6b31c2a9c942285c897c7934635fccf1" "$tmp/stateport-web.manifest.json"
  get "$PROBE_ROOT/stateport-worker.json" "$tmp/stateport-worker.manifest.json"
  check "ac835bf5449d1f7843734a8cbb9f4a332e9b01e6066f06599798a6964539e551" "$tmp/stateport-worker.manifest.json"
  printf "StatePort Alpha.5 transport probe passed: bootstrap syntax and 7 exact image manifests verified; installer was not executed.\n"
  exit 0
fi
command -v sudo >/dev/null 2>&1 || fail "sudo is required."
printf "StatePort %s will install the WSL2 runtime and signed alpha. Type install: " "$VERSION" >/dev/tty
IFS= read -r answer </dev/tty || answer=
[ "$answer" = install ] || fail "Installation not confirmed."
sudo -v
sudo apt-get update
sudo apt-get install -y ca-certificates curl python3 python3-venv podman skopeo uidmap slirp4netns fuse-overlayfs dbus-user-session
sudo loginctl enable-linger "$USER"
command -v curl >/dev/null 2>&1 || fail "curl installation failed."
command -v skopeo >/dev/null 2>&1 || fail "skopeo installation failed."
command -v tar >/dev/null 2>&1 || fail "tar is required."
command -v sha256sum >/dev/null 2>&1 || fail "sha256sum is required."
umask 077
tmp=$(mktemp -d "${TMPDIR:-/tmp}/stateport-wsl2-install.XXXXXX") || fail "Cannot create a private temporary directory."
trap 'rm -rf "$tmp"' EXIT HUP INT TERM
mkdir -m 700 "$tmp/image-bundles" "$tmp/image-manifests" "$tmp/image-archives" "$tmp/image-carriers"
get() { curl -fsSL --proto "=https" --tlsv1.2 --retry 3 -o "$2" "$1"; }
check() { printf "%s  %s\n" "$1" "$2" | sha256sum -c --status || fail "Checksum failed: $2"; }
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
  tar -cf "$tmp/image-archives/$image_id.oci.tar" -C "$carrier" index.json "blobs/sha256/$digest_hex"
}
get "$RELEASE_ROOT/stateport-installer" "$tmp/installer"
check "c1eea13b239c03dde7c405821d7ace5c215581dbe6a98257d68c7be74a6d0dcf" "$tmp/installer"
get "$RELEASE_ROOT/stateport-execution-host-provision" "$tmp/provisioner"
check "7d4d3d8c24a916d76d40391d3ec3b2c80cd2b11bea4952e3036ab7884f7a0163" "$tmp/provisioner"
get "$RELEASE_ROOT/stateport-updater" "$tmp/updater"
check "dd1302c4330c4c80515ce9bdcfdfb5e5a3bab5fc25a6a569be830936dde90a61" "$tmp/updater"
get "$RELEASE_ROOT/release-index.json" "$tmp/release-index.json"
check "4613fcad48ea1a2e7dd4350d61baa333efbc734b1fcba1a1c9ca62994d562b71" "$tmp/release-index.json"
get "$RELEASE_ROOT/release-index.sigstore.json" "$tmp/release-index.sigstore.json"
check "838c3106177b335e1a6a48a681cd173697c39a7bf6ac4908b6a05a5f5369eb82" "$tmp/release-index.sigstore.json"
get "$RELEASE_ROOT/stateport-alpha-2026-08-cosign.pub" "$tmp/release.pub"
check "f473c7447f329d84d6bf2219e8674edbf250a1fffbd393677e08ca16a9d6a99b" "$tmp/release.pub"
get "$COSIGN_URL" "$tmp/cosign"
check "f7622ed3cf22e55e1ae6377c080979ff77a22da9981c11df222a2e444991e7cf" "$tmp/cosign"
chmod 700 "$tmp/installer" "$tmp/cosign"
mkdir -m 700 "$tmp/predecessor-bundle"
get "$RELEASE_ROOT/predecessor-bundle/release-index.sigstore.json" "$tmp/predecessor-bundle/release-index.sigstore.json"
check "e4fb2c0f274ed88e34a5904c2d85feb3dcc231a7a5d794072fff158a29178208" "$tmp/predecessor-bundle/release-index.sigstore.json"
get "$RELEASE_ROOT/signatures/stateport-api.sigstore.json" "$tmp/image-bundles/stateport-api.sigstore.json"
check "9a715230a1fafad9df8b616aa426ccbf502e633416e45119d49315216763f0c2" "$tmp/image-bundles/stateport-api.sigstore.json"
get "$RELEASE_ROOT/signatures/stateport-dev-workspace.sigstore.json" "$tmp/image-bundles/stateport-dev-workspace.sigstore.json"
check "90986669e3203d694b3938f40b1b569c8c57119f47479f11cc16a9270d371be7" "$tmp/image-bundles/stateport-dev-workspace.sigstore.json"
get "$RELEASE_ROOT/signatures/stateport-execution-host.sigstore.json" "$tmp/image-bundles/stateport-execution-host.sigstore.json"
check "d845859f56fed10eceeaa942d161d6fec76e44f52b818eb304aa0b01ae2e59aa" "$tmp/image-bundles/stateport-execution-host.sigstore.json"
get "$RELEASE_ROOT/signatures/stateport-playwright.sigstore.json" "$tmp/image-bundles/stateport-playwright.sigstore.json"
check "176c2472074c61326349424d0aafc0092fc75720f7c9282228811c5e779979a0" "$tmp/image-bundles/stateport-playwright.sigstore.json"
get "$RELEASE_ROOT/signatures/stateport-runner.sigstore.json" "$tmp/image-bundles/stateport-runner.sigstore.json"
check "0754ca07855b686c338f0d6e60f94373709d9d7f2cb36ae135c8a3041ab8c153" "$tmp/image-bundles/stateport-runner.sigstore.json"
get "$RELEASE_ROOT/signatures/stateport-web.sigstore.json" "$tmp/image-bundles/stateport-web.sigstore.json"
check "3a6a9bb097f1a2e74ff275881d1b5fe95d6e7ea2230cc6ff447c056522476d2b" "$tmp/image-bundles/stateport-web.sigstore.json"
get "$RELEASE_ROOT/signatures/stateport-worker.sigstore.json" "$tmp/image-bundles/stateport-worker.sigstore.json"
check "5a475197d0c389cdaf6b58346572346313b790bd2ca9f94ead99ead69222d1b1" "$tmp/image-bundles/stateport-worker.sigstore.json"
manifest_carrier stateport-api ghcr.io/lennertvhoy/stateport-api@sha256:a5c639880195ba6dc57fa9c13378fdf0cdb0361f08cbddea7b7e90f476906af8 sha256:a5c639880195ba6dc57fa9c13378fdf0cdb0361f08cbddea7b7e90f476906af8
manifest_carrier stateport-dev-workspace ghcr.io/lennertvhoy/stateport-dev-workspace@sha256:1a9eecc2a087620e7139570e09c08b4ce6c17a8369d2b428551809dff3fda886 sha256:1a9eecc2a087620e7139570e09c08b4ce6c17a8369d2b428551809dff3fda886
manifest_carrier stateport-execution-host ghcr.io/lennertvhoy/stateport-execution-host@sha256:02d3ce6d6dfdacc164b947c1c88ebf6c64e0a103b05fbd420454083db589efb2 sha256:02d3ce6d6dfdacc164b947c1c88ebf6c64e0a103b05fbd420454083db589efb2
manifest_carrier stateport-playwright ghcr.io/lennertvhoy/stateport-playwright@sha256:a5e8bc89bd193bd149dcad3de03366796bcc8f903f019e9e599f928dfaed9096 sha256:a5e8bc89bd193bd149dcad3de03366796bcc8f903f019e9e599f928dfaed9096
manifest_carrier stateport-runner ghcr.io/lennertvhoy/stateport-runner@sha256:45b5aaf0cd18699a66371ed800683ad5740b491d1442d9c1edd90d87089786ae sha256:45b5aaf0cd18699a66371ed800683ad5740b491d1442d9c1edd90d87089786ae
manifest_carrier stateport-web ghcr.io/lennertvhoy/stateport-web@sha256:57f625f36c590c1440d70f07a3aa1bee6b31c2a9c942285c897c7934635fccf1 sha256:57f625f36c590c1440d70f07a3aa1bee6b31c2a9c942285c897c7934635fccf1
manifest_carrier stateport-worker ghcr.io/lennertvhoy/stateport-worker@sha256:ac835bf5449d1f7843734a8cbb9f4a332e9b01e6066f06599798a6964539e551 sha256:ac835bf5449d1f7843734a8cbb9f4a332e9b01e6066f06599798a6964539e551
python3 "$tmp/installer" \
  --release-index "$tmp/release-index.json" \
  --bundle-root "$tmp" \
  --trust-public-key "$tmp/release.pub" \
  --trust-key-id stateport-alpha-private-2026-08 \
  --trust-key-fingerprint sha256:3dca6219e41310c6a95a8189669aacad3198e6c84489946406b8f986e1f4211a \
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
sudo -n install -o root -g root -m 0555 "$tmp/provisioner" /usr/local/libexec/stateport-execution-host-provision
sudo -n /usr/local/libexec/stateport-execution-host-provision materialize \
  --execution-host-provisioner /usr/local/libexec/stateport-execution-host-provision \
  --execution-host-provisioner-digest "sha256:7d4d3d8c24a916d76d40391d3ec3b2c80cd2b11bea4952e3036ab7884f7a0163" \
  --execution-host-provisioner-bytes "32475" \
  --updater-wheel "$tmp/updater" --updater-wheel-digest "sha256:dd1302c4330c4c80515ce9bdcfdfb5e5a3bab5fc25a6a569be830936dde90a61" \
  --release-index "$tmp/release-index.json" --bundle-root "$tmp" \
  --cosign "$tmp/cosign" --cosign-digest "sha256:f7622ed3cf22e55e1ae6377c080979ff77a22da9981c11df222a2e444991e7cf" \
  --trust-public-key "$tmp/release.pub" --trust-public-key-digest "sha256:f473c7447f329d84d6bf2219e8674edbf250a1fffbd393677e08ca16a9d6a99b" \
  --trust-key-id "stateport-alpha-private-2026-08" --trust-key-fingerprint "sha256:3dca6219e41310c6a95a8189669aacad3198e6c84489946406b8f986e1f4211a"
sudo -n /usr/local/libexec/stateport-execution-host-provision provision \
  --release-index "$tmp/release-index.json" --plan "$STATE_ROOT/execution-host-provisioning-plan.json" \
  --cosign /usr/local/lib/stateport/tools/cosign \
  --trust-public-key /etc/stateport/alpha-2026-08-cosign.pub \
  --trust-key-id "stateport-alpha-private-2026-08" --trust-key-fingerprint "sha256:3dca6219e41310c6a95a8189669aacad3198e6c84489946406b8f986e1f4211a" \
  --channel alpha --bundle-root "$STATE_ROOT/updater/bundles" --receipt-out "$RECEIPT"
python3 "$tmp/installer" \
  --release-index "$tmp/release-index.json" \
  --bundle-root "$tmp" \
  --trust-public-key "$tmp/release.pub" \
  --trust-key-id stateport-alpha-private-2026-08 \
  --trust-key-fingerprint sha256:3dca6219e41310c6a95a8189669aacad3198e6c84489946406b8f986e1f4211a \
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
printf "StatePort %s installed successfully for %s.\n" "$VERSION" "$TARGET"
