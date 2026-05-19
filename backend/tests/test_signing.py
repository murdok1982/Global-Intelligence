"""
Unit tests for the Ed25519 report-signing service.

These tests cover the contract surface exposed to the rest of the
backend:

* keypair generation persists a usable PEM pair to disk
* a signed report round-trips through verify()
* mutating any field of the canonical payload invalidates the
  signature
* rotate() generates a new keypair AND archives the old public key
* canonical_payload is stable (same input → identical bytes)
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

import pytest

from app.services.signing import (
    ReportSigner,
    SigningUnavailableError,
)


# ---------------------------------------------------------------------------
# Lightweight fake report (avoids spinning up SQLAlchemy for crypto tests)
# ---------------------------------------------------------------------------


@dataclass
class _FakeReport:
    id: uuid.UUID
    classification: int
    tlp: str
    org_id: uuid.UUID | None
    executive_summary: str
    content_json: str | None
    content_markdown: str | None
    report_date: datetime | None
    created_at: datetime | None


def _make_report(**overrides) -> _FakeReport:
    base = dict(
        id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        classification=0,
        tlp="TLP:CLEAR",
        org_id=None,
        executive_summary="Hello world.",
        content_json='{"foo": "bar"}',
        content_markdown=None,
        report_date=datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc),
        created_at=datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc),
    )
    base.update(overrides)
    return _FakeReport(**base)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_generate_keypair_writes_pem_files(tmp_path) -> None:
    priv, pub = ReportSigner.generate_keypair(tmp_path)
    assert priv.is_file()
    assert pub.is_file()
    assert b"BEGIN PRIVATE KEY" in priv.read_bytes()
    assert b"BEGIN PUBLIC KEY" in pub.read_bytes()


def test_sign_and_verify_roundtrip(tmp_path) -> None:
    priv, pub = ReportSigner.generate_keypair(tmp_path)
    signer = ReportSigner(str(priv), str(pub))
    assert signer.available
    report = _make_report()

    signature = signer.sign(report)
    assert signer.verify(report, signature) is True


def test_verify_fails_on_modified_field(tmp_path) -> None:
    priv, pub = ReportSigner.generate_keypair(tmp_path)
    signer = ReportSigner(str(priv), str(pub))
    report = _make_report()
    signature = signer.sign(report)

    tampered = _make_report(executive_summary="Hello world. Tampered.")
    assert signer.verify(tampered, signature) is False


def test_canonical_payload_is_stable(tmp_path) -> None:
    priv, pub = ReportSigner.generate_keypair(tmp_path)
    signer = ReportSigner(str(priv), str(pub))
    a = _make_report()
    b = _make_report()
    assert signer.canonical_payload(a) == signer.canonical_payload(b)


def test_fingerprint_is_deterministic_from_pubkey(tmp_path) -> None:
    priv, pub = ReportSigner.generate_keypair(tmp_path)
    signer_a = ReportSigner(str(priv), str(pub))
    signer_b = ReportSigner(str(priv), str(pub))
    assert signer_a.fingerprint == signer_b.fingerprint
    assert len(signer_a.fingerprint) == 16


def test_missing_keys_state_grade_off_falls_back_to_ephemeral(monkeypatch) -> None:
    # The module-level singleton was initialized under STATE_GRADE_MODE
    # false (see conftest), so building a fresh signer with missing
    # paths must produce an ephemeral key in that mode too.
    from app.core import config as cfg

    monkeypatch.setattr(cfg.settings, "STATE_GRADE_MODE", False, raising=False)
    signer = ReportSigner("/definitely/does/not/exist.pem", "/nope.pem")
    assert signer.available is True
    assert signer.ephemeral is True
    report = _make_report()
    sig = signer.sign(report)
    assert signer.verify(report, sig)


def test_missing_keys_state_grade_on_marks_unavailable(monkeypatch) -> None:
    from app.core import config as cfg

    monkeypatch.setattr(cfg.settings, "STATE_GRADE_MODE", True, raising=False)
    signer = ReportSigner("/definitely/does/not/exist.pem", "/nope.pem")
    assert signer.available is False
    with pytest.raises(SigningUnavailableError):
        signer.sign(_make_report())


def test_rotate_archives_old_key(tmp_path) -> None:
    priv = tmp_path / "ed25519_private.pem"
    pub = tmp_path / "ed25519_public.pem"
    ReportSigner.generate_keypair(tmp_path)
    signer = ReportSigner(str(priv), str(pub))

    old_fp = signer.fingerprint
    new_fp, archived_fp, pem = signer.rotate()
    assert new_fp != old_fp
    assert archived_fp == old_fp
    assert "BEGIN PUBLIC KEY" in pem

    archive_path = tmp_path / "archive" / f"{old_fp}.pem"
    assert archive_path.is_file()
    # New keypair is persisted to the original paths.
    assert pub.is_file() and priv.is_file()


def test_verify_payload_independent_of_report(tmp_path) -> None:
    priv, pub = ReportSigner.generate_keypair(tmp_path)
    signer = ReportSigner(str(priv), str(pub))
    report = _make_report()
    sig = signer.sign(report)
    payload = signer.canonical_payload(report)
    assert signer.verify_payload(payload, sig) is True
    assert signer.verify_payload(payload + b"extra", sig) is False
