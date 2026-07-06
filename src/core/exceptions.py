"""Custom exceptions for Salesforce Tools.

Structured exception hierarchy for error handling.
"""


class SalesforceError(Exception):
    """Base exception for all Salesforce-related errors."""

    pass


class CliNotFound(SalesforceError):
    """Raised when Salesforce CLI is not found or not installed."""

    pass


class OrgNotFound(SalesforceError):
    """Raised when requested organization is not authenticated."""

    pass


class QueryLimitExceeded(SalesforceError):
    """Raised when SOQL query exceeds Salesforce limits."""

    pass


class QueryExecutionError(SalesforceError):
    """Raised when SOQL query execution fails."""

    pass


class ValidationError(SalesforceError):
    """Raised when input validation fails."""

    pass


class ExportError(SalesforceError):
    """Raised when data export fails."""

    pass
