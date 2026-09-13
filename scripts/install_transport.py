#!/usr/bin/env python3
"""Bind immutable Alpha.16 bytes and the exact Alpha.17 mutable install route."""

from __future__ import annotations

import sys


VERSIONED_BOOTSTRAP_URL = (
    "https://lennertvhoy.github.io/StatePort-Site/"
    "download/0.1.0-alpha.17/bootstrap.sh"
)
VERSIONED_BOOTSTRAP_SHA256 = "2278267220fdb069180723ac2982db7a4f4de3309167ec2fe5e95e6da2741b98"
VERSIONED_BOOTSTRAP_SIZE = 32_806
# The Alpha.16 predecessor bytes stay pinned as immutable retained history.
RETAINED_ALPHA16_BOOTSTRAP_SHA256 = "6feedf5273547f4a98f5d8edb6fe24e729104ad822c4d58da70cb1f0fdad417a"
RETAINED_ALPHA16_BOOTSTRAP_SIZE = 32_081
RETAINED_ALPHA16_INDEX_SHA256 = "8dad6399e66956d1dcb5aebb5a5119c6001617b3279902f0746857b5e6bfac47"
# The mutable one-command route now serves the Alpha.17 signed candidate. Its
# bytes must equal the versioned Alpha.17 bootstrap; Alpha.16 remains an
# immutable pinned predecessor. Every release input is digest-pinned inside
# the bootstrap; no mutable repair layer is applied.
MUTABLE_BOOTSTRAP_URL = (
    "https://lennertvhoy.github.io/StatePort-Site/"
    "download/0.1.0-alpha.17/bootstrap.sh"
)
MUTABLE_BOOTSTRAP_SHA256 = "2278267220fdb069180723ac2982db7a4f4de3309167ec2fe5e95e6da2741b98"
MUTABLE_BOOTSTRAP_SIZE = 32_806
RETAINED_ALPHA11_BOOTSTRAP_SHA256 = "9aaea4790059579d22db4e5537485a84cc094d9f2b8b0bafc04c618b5e0052df"
RETAINED_ALPHA11_BOOTSTRAP_SIZE = 31_576
RETAINED_ALPHA11_INDEX_SHA256 = "8a26f7d36b5c6883c314db7323c4a79a497e0973e0ec671c02c6b38f0f533f2c"
RETAINED_ALPHA10_BOOTSTRAP_SHA256 = "afb807280e1588ce4903be79649a7b7dd69026177b18a7a98a95b01f54f74d5d"
RETAINED_ALPHA10_BOOTSTRAP_SIZE = 17_774
RETAINED_ALPHA10_INDEX_SHA256 = "2fc626fcab180f664f04f36d1fcceacaffa81ca96a658585f6684e3cf37abf89"
MANIFEST_DIGESTS = {
    "stateport-api": "63d7c8f4eaa5e6742db8d73a9dd5f93594511c4e6010c06aa09e09c5bef31c57",
    "stateport-dev-workspace": "e1d054da25bcf404fbf7ee57f8686901dbc31bd3d244162a2b401d8157bfdd02",
    "stateport-execution-host": "27b70d981709099a5ce8a7999a9160f8aad96c43edf2b1a5b4b8b0c96a858def",
    "stateport-playwright": "307892a7e0d5b46803b00a74b8ecc3ee96e3fd6a4829be237328b99df78c1a24",
    "stateport-runner": "5782579c7ee235ca27b0002a03ba064b14f1654bcf1b0153c60275bfd5872a0c",
    "stateport-web": "a0288e7eff247655c9e0ccbf71fc9652caad3c1fdba640c69b35cb85f8e10289",
    "stateport-worker": "38e90db24ccc31d6a7368d577eafe3872ebf11b2db7a814e95e0d22fb3fd1637",
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
