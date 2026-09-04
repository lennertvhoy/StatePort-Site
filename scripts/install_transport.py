#!/usr/bin/env python3
"""Bind immutable Alpha.15 bytes and its exact install-enabled mutable route."""

from __future__ import annotations

import sys


VERSIONED_BOOTSTRAP_URL = (
    "https://lennertvhoy.github.io/StatePort-Site/"
    "download/0.1.0-alpha.15/bootstrap.sh"
)
VERSIONED_BOOTSTRAP_SHA256 = "a045d3d0c6478bae04b20923fe7e98025e46ea4c6b10f69667cc46852cf3a51f"
VERSIONED_BOOTSTRAP_SIZE = 31_763
# Alpha.15 deliberately serves identical bootstrap bytes at the mutable
# one-command route and the immutable versioned route. Every release input is
# digest-pinned inside the bootstrap; no mutable repair layer is applied.
MUTABLE_BOOTSTRAP_SHA256 = VERSIONED_BOOTSTRAP_SHA256
MUTABLE_BOOTSTRAP_SIZE = VERSIONED_BOOTSTRAP_SIZE
RETAINED_ALPHA11_BOOTSTRAP_SHA256 = "9aaea4790059579d22db4e5537485a84cc094d9f2b8b0bafc04c618b5e0052df"
RETAINED_ALPHA11_BOOTSTRAP_SIZE = 31_576
RETAINED_ALPHA11_INDEX_SHA256 = "8a26f7d36b5c6883c314db7323c4a79a497e0973e0ec671c02c6b38f0f533f2c"
RETAINED_ALPHA10_BOOTSTRAP_SHA256 = "afb807280e1588ce4903be79649a7b7dd69026177b18a7a98a95b01f54f74d5d"
RETAINED_ALPHA10_BOOTSTRAP_SIZE = 17_774
RETAINED_ALPHA10_INDEX_SHA256 = "2fc626fcab180f664f04f36d1fcceacaffa81ca96a658585f6684e3cf37abf89"
MANIFEST_DIGESTS = {
    "stateport-api": "507691145e9900022e7be30222a12a34389f12b1855fddc1e6e65f6989314c52",
    "stateport-dev-workspace": "13b4b2c52f26f30c3a42f264ba80fb0bdc476da4b946c4d93878b55b1d3a6a64",
    "stateport-execution-host": "7766a32d32471c48b153bf7ec96401728757460e20fe79c639ac93ec2c4c0d3a",
    "stateport-playwright": "c4b31ba99602d23202f4c8f8ce4995ac025aa4d96143381277a3b28a93deed45",
    "stateport-runner": "1cf5bea27ffed6b909d3384c45d32fb1e728c7dc9000ffdddf8090085b781a81",
    "stateport-web": "fadb99f743acd10971c576e212d74c85a4ae879eba5f4ac3a980cf9156222a5e",
    "stateport-worker": "8930a946988627fa9cebd900b86043460a9e34e5252c7ad2f5601629621694ed",
}
RETAINED_ALPHA11_MANIFEST_DIGESTS = {
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
    print("Alpha.15 installation is enabled; use the download page command.", file=sys.stderr)
    raise SystemExit(0)


if __name__ == "__main__":
    main()
