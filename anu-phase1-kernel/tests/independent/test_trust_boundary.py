from pathlib import Path

from anu_kernel.db import Base

ROOT = Path(__file__).resolve().parents[2]


def test_trust_registry_never_stores_private_keys():
    columns = {c.name for c in Base.metadata.tables["trust_credential"].columns}
    assert "public_key_pem" in columns
    assert "private_key" not in columns
    assert "private_key_pem" not in columns


def test_authentication_adapter_does_not_import_authority_repository():
    source = (ROOT / "src" / "anu_kernel" / "authn.py").read_text(encoding="utf-8")
    assert "AuthorityGrant" not in source
    assert "evaluate_authority" not in source
    assert "Authorization" in source or "Authorization/authority" in source


def test_signature_verification_requires_authority_for_institutional_validity():
    source = (ROOT / "src" / "anu_kernel" / "trust.py").read_text(encoding="utf-8")
    assert "institutional_valid = credential_valid and cryptographically_valid and role_valid and authority_valid" in source


def test_runtime_engine_is_lazy_for_migration_tooling():
    source = (ROOT / "src" / "anu_kernel" / "db.py").read_text(encoding="utf-8")
    assert "\nengine = make_engine()\n" not in source
    assert "def get_runtime_engine" in source
