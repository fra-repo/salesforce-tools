"""Salesforce SOQL query validator and sanitizer.

Validation and sanitization utilities for SOQL queries.
"""

import re
from typing import List
from .exceptions import ValidationError, QueryLimitExceeded


class SOQLValidator:
    """Validates SOQL queries."""

    # SOQL query limits
    MAX_QUERY_LENGTH = 18000  # Salesforce limit
    MAX_BIND_VALUES = 2000
    MIN_QUERY_LENGTH = 20

    @staticmethod
    def validate_soql(soql: str) -> None:
        """Validate SOQL query format.

        Args:
            soql: SOQL query string

        Raises:
            ValidationError: If query is invalid
            QueryLimitExceeded: If query exceeds limits
        """
        if not soql or len(soql.strip()) < SOQLValidator.MIN_QUERY_LENGTH:
            raise ValidationError("Query SOQL troppo corta")

        soql_upper = soql.upper().strip()
        if not soql_upper.startswith("SELECT"):
            raise ValidationError("Query deve iniziare con SELECT")

        if len(soql) > SOQLValidator.MAX_QUERY_LENGTH:
            raise QueryLimitExceeded(
                f"Query supera il limite di {SOQLValidator.MAX_QUERY_LENGTH} caratteri. "
                f"Lunghezza attuale: {len(soql)}"
            )

    @staticmethod
    def check_bind_values_in_query(soql: str) -> bool:
        """Check if query uses bind values.

        Args:
            soql: SOQL query string

        Returns:
            True if query contains bind variables (e.g., :var_name)
        """
        return ":" in soql

    @staticmethod
    def extract_bind_variable_names(soql: str) -> List[str]:
        """Extract bind variable names from SOQL query.

        Args:
            soql: SOQL query string

        Returns:
            List of bind variable names
        """
        pattern = r":(\w+)"
        matches = re.findall(pattern, soql)
        return list(set(matches))  # Remove duplicates


class SOQLSanitizer:
    """Sanitizes input for safe SOQL usage."""

    @staticmethod
    def escape_string(value: str) -> str:
        """Escape string for SOQL.

        Args:
            value: String to escape

        Returns:
            Escaped string safe for SOQL
        """
        # Escape single quotes by doubling them
        escaped = value.replace("'", "''")
        return escaped

    @staticmethod
    def format_bind_values_for_query(values: List[str]) -> dict:
        """Format bind values for SOQL query.

        Args:
            values: List of bind values

        Returns:
            Dict suitable for SOQL query execution
        """
        if len(values) > SOQLValidator.MAX_BIND_VALUES:
            raise ValidationError(
                f"Troppi bind values: {len(values)}. Max: {SOQLValidator.MAX_BIND_VALUES}"
            )

        return {"bind_values": values}

    @staticmethod
    def sanitize_identifier(identifier: str) -> str:
        """Sanitize Salesforce identifier (field/object names).

        Args:
            identifier: Identifier to sanitize

        Returns:
            Sanitized identifier
        """
        # Only allow alphanumeric, underscore, dot
        if not re.match(r"^[a-zA-Z0-9_.]*$", identifier):
            raise ValidationError(f"Invalid identifier: {identifier}")
        return identifier
