# app/shared/exceptions.py


class BaseDomainException(Exception):
    """Base for all application domain exceptions."""

    code: str = "INTERNAL_ERROR"
    http_status: int = 500


class NotFoundError(BaseDomainException):
    code = "NOT_FOUND"
    http_status = 404


class ValidationError(BaseDomainException):
    code = "VALIDATION_ERROR"
    http_status = 400


class AuthenticationError(BaseDomainException):
    code = "AUTHENTICATION_FAILED"
    http_status = 401


class AuthorizationError(BaseDomainException):
    code = "FORBIDDEN"
    http_status = 403


class BusinessRuleError(BaseDomainException):
    """For 422 business rule violations (e.g. insufficient funds)."""

    code = "BUSINESS_RULE_VIOLATION"
    http_status = 422


class ConflictError(BaseDomainException):
    code = "CONFLICT"
    http_status = 409
