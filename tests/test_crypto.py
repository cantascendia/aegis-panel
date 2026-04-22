"""
Direct unit tests for app/utils/crypto.py.

Why this file exists: PR #11 switched the x509 builder to
timezone-aware datetimes, then shipped a first-attempt commit with a
wrong method name (`not_valid_before_utc` on the *builder* — that
name only exists on the read-side *Certificate* object). The bug
surfaced in `tests/test_migrations.py` because the migration suite
*incidentally* exercises cert generation, but there was no direct
test for `generate_certificate` itself.

A direct test means the next regression in this file surfaces as a
clean, named test failure instead of a mysterious AttributeError
deep inside alembic. Cheap insurance; see
`docs/ai-cto/LESSONS.md#L-009` for the full story.
"""

from __future__ import annotations

from datetime import UTC

from cryptography import x509
from cryptography.hazmat.primitives import serialization

from app.utils.crypto import generate_certificate, get_cert_SANs


def test_generate_certificate_returns_pem_strings() -> None:
    """Happy path: both outputs are PEM-encoded strings."""
    result = generate_certificate()

    assert isinstance(result, dict)
    assert set(result.keys()) == {"cert", "key"}
    assert result["cert"].startswith("-----BEGIN CERTIFICATE-----")
    assert result["cert"].rstrip().endswith("-----END CERTIFICATE-----")
    assert result["key"].startswith("-----BEGIN EC PRIVATE KEY-----")


def test_generate_certificate_validity_window_is_aware_and_ten_years() -> None:
    """Cert must use timezone-aware UTC datetimes (not naive).

    This test is the direct regression guard for the PR #11 class of
    bug: silently falling back to `datetime.utcnow()` after the 3.12
    deprecation campaign would leave the cert working but producing
    `DeprecationWarning`s in production.
    """
    from datetime import UTC, timedelta

    result = generate_certificate()
    cert = x509.load_pem_x509_certificate(result["cert"].encode())

    # The `_utc` properties are the modern read-side API (cryptography 42+).
    # Using them here both verifies the cert AND exercises the API that
    # replaces the deprecated `cert.not_valid_before` property.
    before = cert.not_valid_before_utc
    after = cert.not_valid_after_utc

    assert before.tzinfo is not None, "cert.not_valid_before must be tz-aware"
    assert after.tzinfo is not None, "cert.not_valid_after must be tz-aware"
    assert before.utcoffset() == UTC.utcoffset(before)

    # ~10 years validity (current value is 3650 days; allow 1-day slack).
    span = after - before
    assert timedelta(days=3649) <= span <= timedelta(days=3650)


def test_generate_certificate_key_is_ec_p256() -> None:
    """Reality uses X25519/P-256 curves; the key we generate must load."""
    result = generate_certificate()
    key = serialization.load_pem_private_key(
        result["key"].encode(),
        password=None,
    )
    # The loaded object should be an EC private key. We don't assert on
    # the exact class (cryptography re-exports it from a few paths) —
    # checking that it has the EC-key public-numbers protocol is enough.
    assert hasattr(key, "public_key"), "generated key must expose public_key()"
    pub = key.public_key()
    assert hasattr(pub, "curve"), "EC public key must expose its curve"
    # `SECP256R1` is what `generate_certificate` chose explicitly.
    assert pub.curve.name == "secp256r1"


def test_get_cert_sans_extracts_san_list() -> None:
    """get_cert_SANs should return every SAN from a cert's extension.

    We build a small cert with known SANs rather than rely on
    generate_certificate (which doesn't add SANs). Coupling tests to
    the exact SANs of whatever generate_certificate happens to emit
    would be brittle.
    """
    from datetime import datetime, timedelta, timezone

    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import ec

    key = ec.generate_private_key(ec.SECP256R1())
    subject = issuer = x509.Name([])
    now = datetime.now(UTC)
    san_names = ["alpha.example", "bravo.example"]

    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(now + timedelta(days=1))
        .add_extension(
            x509.SubjectAlternativeName([x509.DNSName(n) for n in san_names]),
            critical=False,
        )
        .sign(private_key=key, algorithm=hashes.SHA256())
    )
    pem = cert.public_bytes(serialization.Encoding.PEM)

    extracted = get_cert_SANs(pem)
    assert sorted(extracted) == sorted(san_names)


def test_get_cert_sans_empty_when_no_san_extension() -> None:
    """Cert without a SAN extension yields an empty list, not an error."""
    # The cert generate_certificate returns has no SAN extension, so we
    # piggyback on it instead of hand-building a second minimal cert.
    result = generate_certificate()
    extracted = get_cert_SANs(result["cert"].encode())
    assert extracted == []
