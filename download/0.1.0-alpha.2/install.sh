#!/bin/sh
# StatePort v0.1.0-alpha.2 one-command bootstrap.
# The small bootstrap downloads and verifies the immutable installer inputs,
# asks once for confirmation, and then hands control to the signed Python installer.
set -eu

VERSION="0.1.0-alpha.2"
SITE_ROOT="https://lennertvhoy.github.io/StatePort-Site"
RELEASE_ROOT="$SITE_ROOT/download/$VERSION"
COSIGN_VERSION="v3.1.2"
COSIGN_URL="https://github.com/sigstore/cosign/releases/download/$COSIGN_VERSION/cosign-linux-amd64"

INSTALLER_SHA256="beea6a856e7459c103c1dc59afd4b6b34b67d5df2ea5110d2b8e05ebc404e1f0"
RELEASE_INDEX_SHA256="9cd33eb7d93b5c70bec9f260824ce45877323ec85993a8b2824411e9b2e43000"
RELEASE_BUNDLE_SHA256="31ab4e44f276c370607ab6c90c6af224d96329a9283c6fa60a616d05addf7bbb"
COSIGN_SHA256="f7622ed3cf22e55e1ae6377c080979ff77a22da9981c11df222a2e444991e7cf"
TRUST_KEY_ID="stateport-alpha-private-2026-08"
TRUST_KEY_FINGERPRINT="sha256:23c965bfec8e56f3075ae3bdcf4b08ef28060522d89261a31fa7d361e05553d8"

say() { printf '%s\n' "$*"; }
fail() { printf 'StatePort install: %s\n' "$*" >&2; exit 1; }

[ "$(uname -s 2>/dev/null || true)" = "Linux" ] || fail "Linux is required."
case "$(uname -m 2>/dev/null || true)" in
  x86_64|amd64) ;;
  *) fail "v$VERSION currently ships only for Linux AMD64." ;;
esac
[ "$(id -u)" -ne 0 ] || fail "Run this as your normal user, not as root."
command -v curl >/dev/null 2>&1 || fail "curl is required to start the bootstrap."
command -v sha256sum >/dev/null 2>&1 || fail "sha256sum is required (normally provided by coreutils)."

OS_ID=""
OS_VERSION=""
if [ -r /etc/os-release ]; then
  # shellcheck disable=SC1091
  . /etc/os-release
  OS_ID=${ID:-}
  OS_VERSION=${VERSION_ID:-}
fi
if [ "$OS_ID" != "ubuntu" ] || [ "$OS_VERSION" != "24.04" ]; then
  fail "the signed v$VERSION target is Ubuntu 24.04 AMD64. The containers are Linux-portable, but Debian/Fedora/Arch/openSUSE require a new capability-based signed target; this bootstrap will not bypass the release contract."
fi

need_setup=0
command -v python3 >/dev/null 2>&1 || need_setup=1
command -v podman >/dev/null 2>&1 || need_setup=1
python_ok=0
if command -v python3 >/dev/null 2>&1; then
  if python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 12) else 1)' >/dev/null 2>&1; then
    python_ok=1
  else
    need_setup=1
  fi
fi

if [ "$need_setup" -eq 1 ]; then
  [ -r /dev/tty ] || fail "Python 3.12 and rootless Podman are required. Install python3, python3-venv, podman, uidmap, slirp4netns, and fuse-overlayfs, then retry."
  printf '\nStatePort needs Python 3.12, venv support, and rootless Podman.\nInstall the Ubu[ќHXЪШYЩ\ИЪ]ЭYИ›ЭПИЮKУ—H	И‹Щ]‹ЭB€Q”ПH™XY\€[њЭЩ\€Щ]‹ЭH[њЭЩ\ЏH€‚€Ш\ЩH‰[њЭЩ\€€[‚€__Y\ЯQTКB€ЫЫ[X[™]€ЭYИ‹Щ]‹Ыќ[Џ‰ЊHZ[њЭYИ\И™\]Z\™YИ[њЭ[Z\ЬЪ[™ИXЪШYЩ\Л€‚€ЭYИ[ќ€P’PS—С”“У•S‘[›Ыљ[ќ\XЭ]™H\YЩ]\]B€ЭYИ[ќ€P’PS—С”“У•S‘[›Ыљ[ќ\XЭ]™H\YЩ][њЭ[^H€]ЫЊИ]ЫЊЛ]™[ќ€ЩX[€ZYX\Ы\њ™]њИќ\ЩK[Э™\›^YњИќ\Л]\Щ\‹\Щ\ЬЪ[Ы‚€ОВ€
ЉHZ[њ™\™\]Z\Ъ]H[њЭ[][Ы€Ш\ИXЫ[™Y€€ОВ€\ШXВ™љB‚ЫЫ[X[™]€]ЫЊИ‹Щ]‹Ыќ[Џ‰ЊHZ[њ]ЫЊИ\ИЭ[[]Z[X›K€‚њ]ЫЊИXИ	Ъ[\ЬќЮ\ОИZ\ЩHЮ\Э[Q^]
Y€Ю\Лќ™\њЪ[Ы—Ъ[™›ИЏH
ЛLЉH[ЩHJIИ€Z[”]Ы€ЛЊL€Ь€™]Щ\€\И™\]Z\™Y€‚ЫЫ[X[™]€ЩX[€‹Щ]‹Ыќ[Џ‰ЊHZ[”ЩX[€\ИЭ[[]Z[X›K€‚‚ќ[X\ЪИНВќЫЬљЩ\ЏI
ZЭ[\Y‰ХTTЋ‹KЭ\KЬЭ]\ЬќZ[њЭ[–ЉHZ[ЫЭ[›ЭЬ™X]HHљ]]H[\Ь\ћH\™XЭЬћK€‚ЫX[ќ\

HИ›H\™€‰ЫЬљЩ\€ЋИBќ\ЫX[ќ\VUTS•T“B‚™™]Ъ

HВ€\›IB€\Э[][ЫЏI‚€Э\›KYZ[K\Ъ[[ќK\ЪЭЛY\њ›Ь€K[ШШ][Ы€€K\›ЭИ	ПZЙИK]ЭЊKЊ€K\™]ћHИKXЫЫ›™XЭ][Y[Э]Њ€K[Э]]‰\Э[][Ы€€‰\›‚џB‚ќ™\љYћJ
HВ€^XЭYIB€]I‚€љ[ќ€	Й\И	\Ч‰И‰^XЭY€‰]€ЪLЌMњЭ[HKXЪXЪИK\Э]\И€Z[ЪXЪЬЭ[H™\љYљXШ][Ы€Z[Y›Ь€	
\Щ[[YH‰]ЉK€‚џB‚њШ^H‘ЭЫ›ШY[™ИHЪYЫ™YЭ]TЬќ	‘T”ТSУ€›ЫЭЭ\[њ]Л‹‹€‚™™]Ъ‰‘SPTСWФ“УХЬЭ]\ЬќZ[њЭ[\€€‰ЫЬљЩ\‹ЬЭ]\ЬќZ[њЭ[\€‚ќ™\љYћH‰S”ХST—ФТLЌM€€‰ЫЬљЩ\‹ЬЭ]\ЬќZ[њЭ[\€‚‚™™]Ъ‰‘SPTСWФ“УХЬ™[X\ЩKZ[™^њЪYЬЭЬ™KљњЫЫ€€‰ЫЬљЩ\‹Ь™[X\ЩKZ[™^њЪYЬЭЬ™KљњЫЫ€‚ќ™\љYћH‰‘SPTСWР•S‘WФТLЌM€€‰ЫЬљЩ\‹Ь™[X\ЩKZ[™^њЪYЬЭЬ™KљњЫЫ€‚‚™™]Ъ‰ТUWФ“УХШ\ЬЩ]ЛЬЭ]\ЬќX[K\™[X\ЩKњX€€‰ЫЬљЩ\‹ЬЭ]\ЬќX[K\™[X\ЩKњX€‚‚™™]Ъ‰УФТQУ—ХT“€‰ЫЬљЩ\‹ШЫЬЪYЫ€‚ќ™\љYћH‰УФТQУ—ФТLЌM€€‰ЫЬљЩ\‹ШЫЬЪYЫ€‚Ъ[ЩМ‰ЫЬљЩ\‹ЬЭ]\ЬќZ[њЭ[\€€‰ЫЬљЩ\‹ШЫЬЪYЫ€‚‚љY€И‰ФХUTФ•ТS”ХSЦQTО‹LH€OHЊH€NИ[‚€И\€Щ]‹ЭHHZ[ЫЫ™љ\›X][Ы€™\]Z\™\ИH\›Z[[И™\ќ[€[ќ\XЭ]™[HЬ€Щ]ХUTФ•ТS”ХSЦQTПLK€‚€Ш]‹Щ]‹ЭHSСЊ‚‚”Э]TЬќ	‘T”ТSУ€Ъ[™H[њЭ[Y›Ь€HЭ\њ™[ќ\Щ\‹‚‹HЬЭ€Xќ[ќHЌЊSQЌ‹Hќ[ќ[YN€›ЫЭ\ЬИЩX[€
ИЮ\Э[Y\Щ\€]XY]В‹H™]ЫЬљО€ЫЬXЪИЫ›HћHY][‹HЭ]N€	ЦЧФХUWТУQN‹IУQKЛ›ШШ[ЬЭ]_KЬЭ]\Ьќ‹HЭ]\О€[HШ[™Y]NИЫX[‹Z[њЭ[[X[€XШЩ\[ЩH\ИЭ[[™[™В‚•\H[њЭ[ИЫЫќ[ќYN€‘SСЊ‚€Q”ПH™XY\€[њЭЩ\€Щ]‹ЭH[њЭЩ\ЏH€‚€И‰[њЭЩ\€€Hљ[њЭ[€HZ[љ[њЭ[][Ы€Ш\И›ЭЫЫ™љ\›YY€‚™љB‚њШ^H•™\љYљYY›ЫЭЭ\[њ]Л€Э\ќ[™ИHЪYЫ™Y[њЭ[\‹‹‹€‚њ]ЫЊИ‰ЫЬљЩ\‹ЬЭ]\ЬќZ[њЭ[\€€€K\™[X\ЩKZ[™^‰‘SPTСWФ“УХЬ™[X\ЩKZ[™^љњЫЫ€€€K\™[X\ЩKZ[™^\ЪLЌM€‰‘SPTСWТS‘VФТLЌM€€€KXќ[™K\›ЫЭ‰ЫЬљЩ\€€€K]ќ\Э\X›XЛZЩ^H‰ЫЬљЩ\‹ЬЭ]\ЬќX[K\™[X\ЩKњX€€€K]ќ\ЭZЩ^KZY‰•TХТСVWТQ€€K]ќ\ЭZЩ^KYљ[™Щ\њљ[ќ‰•TХТСVWС’S‘СT”’S•€€K]\]\‹]ЪY[‰‘SPTСWФ“УХЬЭ]\Ьќ]\]\€€€KXЫЫ\ЬЩH‰‘SPTСWФ“УХШЫЫ\ЬЩKћX[[€€K\ЫЭ\ЩKX\Ъ]™H‰‘SPTСWФ“УХЬЭ]\Ьќ\ЫЭ\ЩKќ\€€€K\™[X\ЩK[›Э\И‰‘SPTСWФ“УХЬ™[X\ЩK[›Э\Л›Y€€KZЫ›ЭЫ‹[[Z]][ЫњИ‰‘SPTСWФ“УХЪЫ›ЭЫ‹[[Z]][ЫњЛ›Y€€KXЪ[›™[[H€KXЫЬЪYЫ€‰ЫЬљЩ\‹ШЫЬЪYЫ€€€KZ[њЭ[\‹\]‰ЫЬљЩ\‹ЬЭ]\ЬќZ[њЭ[\€€€K^Y\В