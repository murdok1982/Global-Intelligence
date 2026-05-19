"""
MFA unit tests — TOTP generation/verification + recovery code consumption.

These tests exercise the pure helper functions and the recovery-code
consumption flow without spinning up the full FastAPI app.
"""

from __future__ import annotations

import secrets
import time
from datetime import datetime

import pyotp
import pytest
from passlib.context import CryptContext
from sqlalchemy import select

from app.auth.mfa import TOTPService, generate_recovery_codes
from app.models.auth import MFARecoveryCode
from app.models.user import User


_bcrypt = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _safe_bcrypt_hash(plain: str) -> str:
    """Wrap bcrypt hashing so passlib/bcrypt version skew doesn't fail tests.

    Newer ``bcrypt`` releases (5.x) trip a passlib 1.7.4 self-check.
    When passlib is unavailable, fall back to the underlying ``bcrypt``
    library directly — the resulting hash is still verifiable via
    ``passlib`` later because both produce the same ``$2b$...`` format.
    """
    try:
        return _bcrypt.hash(plain)
    except Exception:
        import bcrypt as _native_bcrypt

        return _native_bcrypt.hashpw(
            plain.encode("utf-8"), _native_bcrypt.gensalt(rounds=4)
        ).decode("ascii")


def _safe_bcrypt_verify(plain: str, hashed: str) -> bool:
    try:
        return _bcrypt.verify(plain, hashed)
    except Exception:
        import bcrypt as _native_bcrypt

        try:
            return _native_bcrypt.checkpw(
                plain.encode("utf-8"), hashed.encode("ascii")
            )
        except Exception:
            return False


def test_totp_service_generate_and_verify():
    svc = TOTPService(
        issuer="Test",
        encryption_key_hex=secrets.token_hex(32),
    )
    secret = svc.generate_secret()
    assert len(secret) > 0
    code = pyotp.TOTP(secret).now()
    assert svc.verify_code(secret, code) is True
    assert svc.verify_code(secret, "000000") is False
    assert svc.verify_code(secret, "abcdef") is False
    assert svc.verify_code(secret, "") is False


def test_totp_service_encrypt_roundtrip():
    svc = TOTPService(encryption_key_hex=secrets.token_hex(32))
    secret = svc.generate_secret()
    blob = svc.encrypt_secret(secret)
    assert blob != secret
    assert svc.decrypt_secret(blob) == secret


def test_totp_service_encrypt_rejects_tamper():
    svc = TOTPService(encryption_key_hex=secrets.token_hex(32))
    blob = svc.encrypt_secret(svc.generate_secret())
    tampered = blob[:-4] + "AAAA"
    with pytest.raises(RuntimeError):
        svc.decrypt_secret(tampered)


def test_provisioning_uri_contains_issuer_and_email():
    svc = TOTPService(issuer="StateIntel", encryption_key_hex=secrets.token_hex(32))
    secret = svc.generate_secret()
    uri = svc.provisioning_uri("agent@example.gov", secret)
    assert uri.startswith("otpauth://totp/")
    assert "StateIntel" in uri
    assert "agent%40example.gov" in uri or "agent@example.gov" in uri


def test_generate_recovery_codes_has_correct_shape():
    codes = generate_recovery_codes(count=5, length=10)
    assert len(codes) == 5
    for c in codes:
        left, right = c.split("-")
        assert len(left) == 5 and len(right) == 5
        # All from the safe alphabet.
        for ch in left + right:
            assert ch in "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


@pytest.mark.asyncio
async def test_recovery_code_consumed_after_use(db_session):
    """Storing recovery codes hashed and marking them used works end-to-end."""
    # Insert a fake user (foreign key required). Use a stub hash so
    # we don't depend on passlib<->bcrypt at unit-test time — the
    # value never gets verified in this test path.
    user = User(
        email="agent@example.gov",
        hashed_password="$2b$12$" + "a" * 53,
    )
    db_session.add(user)
    await db_session.flush()

    plain_code = "ABCDE-12345"
    code_hash = _safe_bcrypt_hash(plain_code)
    db_session.add(MFARecoveryCode(user_id=user.id, code_hash=code_hash))
    await db_session.commit()

    # First use: verifies and gets marked used.
    result = await db_session.execute(
        select(MFARecoveryCode).where(MFARecoveryCode.user_id == user.id)
    )
    row = result.scalars().first()
    assert row.used_at is None
    assert _safe_bcrypt_verify(plain_code, row.code_hash)
    row.used_at = datetime.utcnow()
    await db_session.commit()

    # Second lookup: there is no unused code left.
    result = await db_session.execute(
        select(MFARecoveryCode).where(
            MFARecoveryCode.user_id == user.id,
            MFARecoveryCode.used_at.is_(None),
        )
    )
    assert result.scalars().first() is None


def test_challenge_token_roundtrip(monkeypatch):
    """The challenge token must round-trip and reject tampered payloads."""
    from app.auth.challenge import (
        create_mfa_challenge_token,
        decode_mfa_challenge_token,
    )

    token = create_mfa_challenge_token("user-123")
    payload = decode_mfa_challenge_token(token)
    assert payload["sub"] == "user-123"
    assert payload["type"] == "mfa_challenge"

    import jwt as _jwt

    with pytest.raises(_jwt.PyJWTError):
        decode_mfa_challenge_token(token + "tamper")
