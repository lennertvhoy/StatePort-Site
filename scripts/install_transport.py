#!/usr/bin/env python3
"""Bind immutable Alpha.16 bytes and the exact Alpha.21 mutable install route."""

from __future__ import annotations

import sys


VERSIONED_BOOTSTRAP_URL = (
    "https://lennertvhoy.github.io/StatePort-Site/"
    "download/0.1.0-alpha.21/bootstrap.sh"
)
VERSIONED_BOOTSTRAP_SHA256 = "5fc574f25072f1c801cd40a098126eb230934e8af4f18f8e5c1518955d0cc9e0"
VERSIONED_BOOTSTRAP_SIZE = 33_067
# The Alpha.16 predecessor bytes stay pinned as immutable retained history.
RETAINED_ALPHA16_BOOTSTRAP_SHA256 = "6feedf5273547f4a98f5d8edb6fe24e729104ad822c4d58da70cb1f0fdad417a"
RETAINED_ALPHA16_BOOTSTRAP_SIZE = 32_081
RETAINED_ALPHA16_INDEX_SHA256 = "8dad6399e66956d1dcb5aebb5a5119c6001617b3279902f0746857b5e6bfac47"
# The mutable one-command route now serves the Alpha.21 signed candidate. Its
# bytes must equal the versioned Alpha.21 bootstrap; Alpha.16 remains an
# immutable pinned predecessor. Every release input is digest-pinned inside
# the bootstrap; no mutable repair layer is applied.
MUTABLE_BOOTSTRAP_URL = (
    "https://lennertvhoy.github.io/StatePort-Site/"
    "download/0.1.0-alpha.21/bootstrap.sh"
)
MUTABLE_BOOTSTRAP_SHA256 = "5fc574f25072f1c801cd40a098126eb230934e8af4f18f8e5c1518955d0cc9e0"
MUTABLE_BOOTSTRAP_SIZE = 33_067
RETAINED_ALPHA11_BOOTSTRAP_SHA256 = "9aaea4790059579d22db4e5537485a84cc094d9f2b8b0bafc04c618b5e0052df"
RETAINED_ALPHA11_BOOTSTRAP_SIZE = 31_576
RETAINED_ALPHA11_INDEX_SHA256 = "8a26f7d36b5c6883c314db7323c4a79a497e0973e0ec671c02c6b38f0f533f2c"
RETAINED_ALPHA10_BOOTSTRAP_SHA256 = "afb807280e1588ce4903be79649a7b7dd69026177b18a7a98a95b01f54f74d5d"
RETAINED_ALPHA10_BOOTSTRAP_SIZE = 17_774
RETAINED_ALPHA10_INDEX_SHA256 = "2fc626fcab180f664f04f36d1fcceacaffa81ca96a658585f6684e3cf37abf89"
MANIFEST_DIGESTS = {
    "stateport-api": "520b7d01402fae2dad43d80ff984d6daa2e389ac71d7519a81e617e9627e8779",
    "stateport-dev-workspace": "da91bc358a6a0408ec27be0f4f35b9d0fc22bf49f3346e22cff2bad8e91d3646",
    "stateport-execution-host": "a938b384de1e73574e4369decf9c0de46319329151f10e64f08d87b57e3a44f6",
    "stateport-playwright": "fa2bd392415752e9648f9e541b1d3ec8f5e3656c1107a8f678b49cc0845bcac7",
    "stateport-runner": "61eb0be882a99ec929cc40929a8ff9d5d414c6a7a3e13bf54d20ed3d5c0eaed4",
    "stateport-web": "7d535d2b03b523826e4411b507d56b6e3765284cdd33c6b9eec14e8e5d5ca9ee",
    "stateport-worker": "7407cca5a86b1b96a3ed06d9464c2e4dd18be9955c47fc3c1039e1bf5a04eaea",
}
# Retained immutable Alpha.16 image manifests (nested-repo era).
RETAINED_ALPHA16_MANIFEST_DIGESTS = {
    "stateport-api": "95c3adccacfaabfb70430d299a578c33ebafa2f0fb16ab129d0ac271847a3c73",
    "stateport-dev-workspace": "fee3e363718c71222fdcacfd63fa61088ecae66da727c617a92ca9fc3e635e43",
    "stateport-execution-host": "221ddc06dd59cd3c5810b2d38a0eb5c44aaaa4bb522abcdc8b5ed0e4d2b3793e",
    "stateport-playwright": "885f078be50869a958f7867c74b75760dc7bafef33579877ef769d4cc2e182fe",
    "stateport-runner": "38086218681ba5b64adece703cda8eed817a692c7f0436faccbe6bfae4143885",
    "stateport-web": "bbb120242e44e77b79de85d924021b3a2950ed6ff304061c6a6f8482f98b486d",
    "stateport-worker": "a4367aa99b222a80fe420afa1e48c937bda2a5c38bc2d6d5a202167a2d30fad3",
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
    print("Alpha.16 installation is enabled; use the download page command.", file=sys.stderr)
    raise SystemExit(0)


if __name__ == "__main__":
    main()
