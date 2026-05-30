# app/shared/exceptions.py


class BaseDomainException(Exception):
    """Base for all application domain exceptions."""

    code: str = "INTERNAL_ERROR"
    http_status: int = 500

    def __init__(self, message: str = ""):
        self.message = message
        super().__init__(message)


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


class RateLimitError(BaseDomainException):
    """Raised when the login rate limit is exceeded."""

    code = "RATE_LIMIT_EXCEEDED"
    http_status = 429


class AccountLockedError(BaseDomainException):
    """Raised when an account is locked after too many failures.

    Attributes:
        locked_until: ISO 8601 datetime string indicating when the lockout expires.
    """

    code = "ACCOUNT_LOCKED"
    http_status = 423

    def __init__(self, message: str = "", locked_until: str = ""):
        self.locked_until = locked_until
        super().__init__(message)
