#!/usr/bin/env python3
"""Bind immutable Alpha.11 bytes and its exact install-enabled mutable route."""

from __future__ import annotations

import sys


VERSIONED_BOOTSTRAP_URL = (
    "https://lennertvhoy.github.io/StatePort-Site/"
    "download/0.1.0-alpha.11/install.sh"
)
VERSIONED_BOOTSTRAP_SHA256 = "9aaea4790059579d22db4e5537485a84cc094d9f2b8b0bafc04c618b5e0052df"
VERSIONED_BOOTSTRAP_SIZE = 31_576
# The mutable public route and the versioned Alpha.11 bootstrap are byte-identical:
# the mutable route no longer carries a fail-closed launcher.
MUTABLE_BOOTSTRAP_SHA256 = VERSIONED_BOOTSTRAP_SHA256
MUTABLE_BOOTSTRAP_SIZE = VERSIONED_BOOTSTRAP_SIZE
RETAINED_ALPHA10_BOOTSTRAP_SHA256 = "afb807280e1588ce4903be79649a7b7dd69026177b18a7a98a95b01f54f74d5d"
RETAINED_ALPHA10_BOOTSTRAP_SIZE = 17_774
RETAINED_ALPHA10_INDEX_SHA256 = "2fc626fcab180f664f04f36d1fcceacaffa81ca96a658585f6684e3cf37abf89"
MANIFEST_DIGESTS = {
    "stateport-api": "bc15758766b9cceeb842b935415a12087bd5269c0cc5125ce939b4be0b0a11fc",
    "stateport-dev-workspace": "af767264b264cfbdc88ff3d4c32736fc6da9ebbb3e043c7450ebd5154b4d715d",
    "stateport-execution-host": "58f2e6b9541f06bc26bf23b509dc359c7886274c0a80af3e5a58d958550693e9",
    "stateport-playwright": "b7e9b2cbe65f80e99575e1baf09cc7f1900c6ed268cf81f15528baa84af64775",
    "stateport-runner": "b220a447485fbf2180d23f76899a37f1ba3347925b37bfdf725584387882b6ce",
    "stateport-web": "e09ab3f6aa6ac8316ed265c2d855ef35405253f0579d7033d1ff3f53cafc6591",
    "stateport-worker": "84c21888edbbcb200d1d9df8b5f2c5c957af15a21afb47135854d7eae49f07bc",
}
RETAINED_ALPHA10_MANIFEST_DIGESTS = {
    "stateport-api": "bfd04f5c9d59f08418557cef0345c7fe30e0e78718fc22cc6d528e741c8ca895",
    "stateport-dev-workspace": "7d91f5bd383fb93cee979ed7226082c8c88f062b222d7f9f78534f4ce0ce06a0",
    "stateport-execution-host": "fcbf04af84c590038da50c9799cea6c58953a8d3c84c87ef1433def028c3f6d7",
    "stateport-playwright": "c51603a29f260b359ac1c002af15684264bfa9986fe502c8c9a1300139abcc59",
    "stateport-runner": "0534422ca6b116fff08f675cfa0e22ffe9d3f52d95f3e14757b63988dab60160",
    "stateport-web": "6984bfa338f2903b00d4a0329adf69c038806cd08346e108dd143024273cb704",
    "stateport-worker": "46d04e8c274192eb980ebeb89ae177abbef1f409a9e6c0b6dddf2acdcb468a23",
}


def main() -> None:
    print("Alpha.11 installation is enabled; use the download page command.", file=sys.stderr)
    raise SystemExit(0)


if __name__ == "__main__":
    main()
