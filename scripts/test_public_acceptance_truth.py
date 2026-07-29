from __future__ import annotations

import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

try:
    from scripts import validate_repo
except ModuleNotFoundError:  # Direct execution keeps only scripts/ on sys.path.
    import validate_repo


PENDING_COPY = "Agent validation passed; owner acceptance remains pending."


class PublicAcceptanceTruthTests(unittest.TestCase):
    def _write_fixture(self, root: Path, *, status: str, copy: str) -> None:
        (root / "PROJECT_STATE.yaml").write_text(
            "public_alpha_trust_successor:\n"
            "  behavioural_head: 0123456789abcdef0123456789abcdef01234567\n"
            "  acceptance:\n"
            f"    ownerAcceptance: {status}\n",
            encoding="utf-8",
        )
        (root / "index.html").write_text(f"<p>{PENDING_COPY}</p>", encoding="utf-8")
        (root / "details.html").write_text(f"<p>{copy}</p>", encoding="utf-8")

    def test_pending_candidate_rejects_affirmative_owner_claim(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._write_fixture(root, status="pending", copy="This journey is owner-accepted.")
            with patch.object(validate_repo, "ROOT", root):
                with self.assertRaisesRegex(AssertionError, "unsupported public acceptance claim"):
                    validate_repo.validate_public_acceptance_truth()

    def test_pending_candidate_requires_explicit_pending_copy(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._write_fixture(root, status="pending", copy="Agent-tested evidence only.")
            (root / "index.html").write_text("<p>Agent-tested evidence only.</p>", encoding="utf-8")
            with patch.object(validate_repo, "ROOT", root):
                with self.assertRaisesRegex(AssertionError, "owner acceptance remains pending"):
                    validate_repo.validate_public_acceptance_truth()

    def test_exact_accepted_state_can_use_acceptance_language(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._write_fixture(root, status="accepted", copy="This exact journey is owner-accepted.")
            with patch.object(validate_repo, "ROOT", root):
                validate_repo.validate_public_acceptance_truth()


if __name__ == "__main__":
    unittest.main()
