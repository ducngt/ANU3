from __future__ import annotations


class KernelError(Exception):
    """Base exception for deterministic Kernel failures."""

    code = "KERNEL_ERROR"


class RepositoryConflict(KernelError):
    code = "RESOURCE_CONFLICT"

    def __init__(self, resource_type: str, resource_id: str):
        self.resource_type = resource_type
        self.resource_id = resource_id
        super().__init__(f"{resource_type} already exists: {resource_id}")


class DomainValidationError(KernelError, ValueError):
    code = "DOMAIN_VALIDATION_FAILED"

    def __init__(self, message: str, reason_codes: list[str] | None = None):
        self.reason_codes = reason_codes or []
        super().__init__(message + (": " + ",".join(self.reason_codes) if self.reason_codes else ""))


class AuthenticationError(KernelError):
    code = "AUTHENTICATION_FAILED"

    def __init__(self, message: str, reason_codes: list[str] | None = None):
        self.reason_codes = reason_codes or []
        super().__init__(message + (": " + ",".join(self.reason_codes) if self.reason_codes else ""))
