"""Digest-bound StatePort release and update contracts."""

from dataclasses import dataclass
import re
from typing import Final

from .cosign import (
    CosignVerificationError,
    CosignVerifier,
    bundle_slot,
    public_key_der_spki_fingerprint,
    retain_bundle,
    signature_bundle_name,
)
from .contract import (
    ReleaseContractError,
    AuthoritySourceResolver,
    ReleaseIndex,
    ReleaseVerificationPolicy,
    PinnedPublicKeyIdentity,
    SignatureVerificationProof,
    SignatureVerifier,
    SignerIdentity,
    UpdaterReleaseEnvelope,
    ValidatedContract,
    VerifiedRelease,
    canonical_digest,
    canonical_json_bytes,
    image_set_digest,
    installer_directive_digest,
    release_identity_from_verified,
    reverify_updater_release_envelope,
    load_release_index,
    load_release_index_file,
    quadlet_bundle_digest,
    materialize_verified_quadlet_bundle,
    materialize_accepted_quadlet_bundle,
    owner_materialization_spec_digest,
    derive_revision_authority_proofs,
    plan_stable_host_service_transition,
    record_revision_port_activation_recheck,
    reserve_revision_port_allocation,
    render_accepted_activation,
    revision_contract_digest,
    render_quadlet_bundle,
    render_stable_host_quadlet_bundle,
    service_set_digest,
    topology_digest,
    signed_payload_bytes,
    signature_verification_proof_set,
    signature_verification_proof_set_digest,
    to_updater_release_envelope,
    validate_contract_document,
    validate_install_receipt,
    validate_revision_contract,
    validate_release_index,
    validate_release_provenance,
    validate_update_failure_evidence,
    validate_update_authority_link,
    validate_update_plan,
    validate_update_receipt,
    validate_update_status,
    update_plan_digest,
    update_policy_digest,
    verify_release_index,
    verify_quadlet_bundle,
    verify_stable_host_quadlet_bundle,
    validate_activation_pointer_transition,
)

PORTABLE_LINUX_TARGET_ID: Final = "linux-amd64-rootless-podman-quadlet"
PODMAN_MINIMUM: Final = (4, 9, 3)
VALIDATED_LINUX_BASELINES: Final = frozenset({("ubuntu", "24.04")})


@dataclass(frozen=True)
class LinuxHostObservation:
    """Observed host facts; distribution identity is evidence, not authority."""

    kernel: str
    architecture: str
    os_id: str
    version_id: str
    cgroup_version: str
    podman_version: str
    rootless: bool
    quadlet: bool
    systemd_user: bool
    subuid_configured: bool
    subgid_configured: bool


@dataclass(frozen=True)
class LinuxHostDecision:
    """Capability eligibility kept separate from clean-install qualification."""

    eligible: bool
    target_id: str
    support_tier: str
    refusal_codes: tuple[str, ...]
    warnings: tuple[str, ...]
    observation: LinuxHostObservation

    def to_dict(self) -> dict[str, object]:
        return {
            "formatVersion": "stateport.linux-host-capability-decision/v1",
            "eligible": self.eligible,
            "targetId": self.target_id,
            "supportTier": self.support_tier,
            "refusalCodes": list(self.refusal_codes),
            "warnings": list(self.warnings),
            "observation": {
                "kernel": self.observation.kernel,
                "architecture": self.observation.architecture,
                "osId": self.observation.os_id,
                "versionId": self.observation.version_id,
                "cgroupVersion": self.observation.cgroup_version,
                "podmanVersion": self.observation.podman_version,
                "rootless": self.observation.rootless,
                "quadlet": self.observation.quadlet,
                "systemdUser": self.observation.systemd_user,
                "subuidConfigured": self.observation.subuid_configured,
                "subgidConfigured": self.observation.subgid_configured,
            },
        }


def parse_host_semantic_version(value: str) -> tuple[int, int, int] | None:
    """Return a leading semantic version while accepting vendor suffixes."""

    match = re.match(r"^\s*(\d+)\.(\d+)\.(\d+)(?:\D.*)?$", value)
    if match is None:
        return None
    major, minor, patch = (int(part) for part in match.groups())
    return major, minor, patch


def evaluate_linux_host(observation: LinuxHostObservation) -> LinuxHostDecision:
    """Qualify a host by required behavior, never by distribution branding.

    Eligibility means the runtime contract is present. It does not mean that
    exact distribution/version has a clean-install acceptance receipt. That
    evidence distinction is represented by ``support_tier``.
    """

    refusals: list[str] = []
    warnings: list[str] = []

    if observation.kernel.lower() != "linux":
        refusals.append("linux_kernel_required")
    if observation.architecture not in {"amd64", "x86_64"}:
        refusals.append("linux_amd64_required")
    if observation.cgroup_version != "v2":
        refusals.append("cgroup_v2_required")

    podman_version = parse_host_semantic_version(observation.podman_version)
    if podman_version is None:
        refusals.append("podman_version_unparseable")
    elif podman_version < PODMAN_MINIMUM:
        refusals.append("podman_version_too_old")

    if not observation.rootless:
        refusals.append("rootless_podman_required")
    if not observation.quadlet:
        refusals.append("quadlet_required")
    if not observation.systemd_user:
        refusals.append("systemd_user_required")
    if not observation.subuid_configured:
        refusals.append("subuid_mapping_required")
    if not observation.subgid_configured:
        refusals.append("subgid_mapping_required")

    baseline = (observation.os_id.lower(), observation.version_id)
    if refusals:
        support_tier = "ineligible"
    elif baseline in VALIDATED_LINUX_BASELINES:
        support_tier = "validated_baseline"
    else:
        support_tier = "compatible_unvalidated"
        warnings.append(
            "host capabilities match, but this distribution/version lacks a clean-install acceptance receipt"
        )

    return LinuxHostDecision(
        eligible=not refusals,
        target_id=PORTABLE_LINUX_TARGET_ID,
        support_tier=support_tier,
        refusal_codes=tuple(refusals),
        warnings=tuple(warnings),
        observation=observation,
    )


__all__ = [
    "ReleaseContractError",
    "AuthoritySourceResolver",
    "CosignVerificationError",
    "CosignVerifier",
    "ReleaseIndex",
    "ReleaseVerificationPolicy",
    "PinnedPublicKeyIdentity",
    "SignatureVerificationProof",
    "SignatureVerifier",
    "SignerIdentity",
    "UpdaterReleaseEnvelope",
    "ValidatedContract",
    "VerifiedRelease",
    "LinuxHostObservation",
    "LinuxHostDecision",
    "PORTABLE_LINUX_TARGET_ID",
    "PODMAN_MINIMUM",
    "VALIDATED_LINUX_BASELINES",
    "parse_host_semantic_version",
    "evaluate_linux_host",
    "canonical_digest",
    "canonical_json_bytes",
    "image_set_digest",
    "installer_directive_digest",
    "release_identity_from_verified",
    "reverify_updater_release_envelope",
    "load_release_index",
    "load_release_index_file",
    "quadlet_bundle_digest",
    "materialize_verified_quadlet_bundle",
    "materialize_accepted_quadlet_bundle",
    "owner_materialization_spec_digest",
    "derive_revision_authority_proofs",
    "plan_stable_host_service_transition",
    "record_revision_port_activation_recheck",
    "reserve_revision_port_allocation",
    "render_accepted_activation",
    "revision_contract_digest",
    "render_quadlet_bundle",
    "render_stable_host_quadlet_bundle",
    "service_set_digest",
    "topology_digest",
    "signed_payload_bytes",
    "signature_verification_proof_set",
    "signature_verification_proof_set_digest",
    "to_updater_release_envelope",
    "validate_contract_document",
    "validate_install_receipt",
    "validate_revision_contract",
    "validate_release_index",
    "validate_release_provenance",
    "validate_update_failure_evidence",
    "validate_update_authority_link",
    "validate_update_plan",
    "validate_update_receipt",
    "validate_update_status",
    "update_plan_digest",
    "update_policy_digest",
    "bundle_slot",
    "public_key_der_spki_fingerprint",
    "retain_bundle",
    "signature_bundle_name",
    "verify_release_index",
    "verify_quadlet_bundle",
    "verify_stable_host_quadlet_bundle",
    "validate_activation_pointer_transition",
]
