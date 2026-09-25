from __future__ import annotations

import os
from datetime import datetime, timezone

import jwt
from jwt import InvalidTokenError
from sqlalchemy.orm import Session

from .contracts import AuthenticationContext, SubjectType
from .db import IdentityRecord
from .errors import AuthenticationError


def authenticate_bearer_token(session: Session, token: str) -> AuthenticationContext:
    """Validate external authentication evidence without granting institutional authority.

    The reference adapter validates a JWT from a configured IdP boundary and maps it
    to an existing ANU Identity/Credential reference. Authorization/authority are
    deliberately evaluated elsewhere by the PEP/PDP path.
    """
    secret = os.getenv("ANU_JWT_SECRET")
    issuer = os.getenv("ANU_JWT_ISSUER", "anu-reference-idp")
    audience = os.getenv("ANU_JWT_AUDIENCE", "anu-kernel")
    if not secret:
        raise AuthenticationError("authentication adapter is not configured", ["AUTHN_NOT_CONFIGURED"])
    try:
        claims = jwt.decode(token, secret, algorithms=["HS256"], issuer=issuer, audience=audience)
    except InvalidTokenError as exc:
        raise AuthenticationError("authentication failed", ["AUTHENTICATION_FAILED"]) from exc

    identity_id = claims.get("identity_id")
    subject_ref = claims.get("sub")
    credential_ref = claims.get("credential_ref")
    if not identity_id or not subject_ref or not credential_ref:
        raise AuthenticationError("authentication claims are incomplete", ["AUTHN_CLAIMS_INCOMPLETE"])

    identity = session.get(IdentityRecord, identity_id)
    if identity is None or identity.subject_id != subject_ref:
        raise AuthenticationError("identity mapping failed", ["IDENTITY_NOT_FOUND"])
    if identity.status != "ACTIVE" or identity.lifecycle_state != "ACTIVE":
        raise AuthenticationError("identity is inactive", ["IDENTITY_NOT_ACTIVE"])
    if credential_ref not in (identity.credential_refs or []):
        raise AuthenticationError("credential is not bound to identity", ["CREDENTIAL_NOT_BOUND_TO_IDENTITY"])

    return AuthenticationContext(
        identity_id=identity.identity_id,
        subject_ref=identity.subject_id,
        subject_type=SubjectType(identity.subject_type),
        credential_ref=credential_ref,
        authentication_method="JWT-HS256-REFERENCE-ADAPTER",
        assurance_level=identity.assurance_level,
        authenticated_at=datetime.now(timezone.utc),
        issuer=issuer,
    )
