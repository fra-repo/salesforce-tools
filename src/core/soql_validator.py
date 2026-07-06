"""SOQL query validation and sanitization.

This module provides validators for SOQL queries to ensure safety,
correctness, and adherence to Salesforce limits.
"""

import re
from typing import List, Tuple
from .exceptions import ValidationError, QueryLimitExceeded


class SOQLValidator:
    """Validates SOQL queries for correctness and safety.

    Checks:
    - Required clauses (SELECT, FROM)
    - Dangerous operations (DELETE, DROP)
    - Query size limits
    - Bind variable placeholders
    """

    # Dangerous keywords that should not appear in queries
    DANGEROUS_KEYWORDS = {"DELETE", "DROP", "TRUNCATE", "ALTER", "CREATE"}

    # SOQL size limit
    MAX_SOQL_LENGTH = 18000

    @staticmethod
    def validate_soql(soql: str, check_size: bool = True) -> Tuple[bool, str]:
        """Validate SOQL query syntax and safety.

        Args:
            soql: SOQL query string
            check_size: If True, validate against size limit

        Returns:
            Tuple of (is_valid, error_message)

        Raises:
            ValidationError: If validation fails
        """
        if not soql or not soql.strip():
            raise ValidationError("soql", "Query SOQL non può essere vuota")

        soql_upper = soql.upper()

        # Check for required clauses
        if "SELECT" not in soql_upper:
            raise ValidationError(
                "soql", "Query SOQL deve contenere la clausola SELECT"
            )

        if "FROM" not in soql_upper:
            raise ValidationError(
                "soql", "Query SOQL deve contenere la clausola FROM"
            )

        # Check for dangerous keywords
        for keyword in SOQLValidator.DANGEROUS_KEYWORDS:
            if keyword in soql_upper:
                raise ValidationError(
                    "soql",
                    f"Query SOQL non può contenere '{keyword}'. Sono supportate solo query SELECT.",
                )

        # Check query size
        if check_size and len(soql) > SOQLValidator.MAX_SOQL_LENGTH:
            raise QueryLimitExceeded(len(soql), SOQLValidator.MAX_SOQL_LENGTH)

        return True, ""

    @staticmethod
    def validate_bind_values(bind_values: List[str]) -> Tuple[bool, str]:
        """Validate bind values list.

        Args:
            bind_values: List of bind value strings

        Returns:
            Tuple of (is_valid, error_message)

        Raises:
            ValidationError: If validation fails
        """
        if not bind_values:
            raise ValidationError(
                "bind_values", "Lista valori di bind non può essere vuota"
            )

        if not isinstance(bind_values, list):
            raise ValidationError(
                "bind_values", "Valori di bind devono essere una lista"
            )

        if len(bind_values) > 10000:
            raise ValidationError(
                "bind_values",
                f"Troppi valori di bind ({len(bind_values)}). Massimo 10000.",
            )

        return True, ""

    @staticmethod
    def validate_chunk_size(chunk_size: int) -> Tuple[bool, str]:
        """Validate chunk size for bulk operations.

        Args:
            chunk_size: Number of records per chunk

        Returns:
            Tuple of (is_valid, error_message)

        Raises:
            ValidationError: If validation fails
        """
        if chunk_size <= 0:
            raise ValidationError(
                "chunk_size", "Dimensione chunk deve essere > 0"
            )

        if chunk_size > 2000:
            raise ValidationError(
                "chunk_size",
                f"Dimensione chunk troppo grande ({chunk_size}). Massimo 2000.",
            )

        return True, ""

    @staticmethod
    def check_bind_values_in_query(soql: str) -> bool:
        """Check if query contains bind value placeholder.

        Args:
            soql: SOQL query string

        Returns:
            True if query contains ':bind_values' placeholder

        Raises:
            ValidationError: If placeholder is missing
        """
        if ":bind_values" not in soql and "(:bind_values)" not in soql:
            raise ValidationError(
                "soql",
                "Query SOQL deve contenere il placeholder ':bind_values' o '(:bind_values)' dove inserire i filtri.",
            )
        return True


class SOQLSanitizer:
    """Sanitizes and escapes SOQL strings for safe execution."""

    @staticmethod
    def escape_string(value: str) -> str:
        """Escape string for SOQL execution.

        Handles single quotes by escaping with backslash.

        Args:
            value: String to escape

        Returns:
            Escaped string safe for SOQL
        """
        if not isinstance(value, str):
            value = str(value)
        # Escape single quotes
        return value.replace("'", "\\")

    @staticmethod
    def format_bind_value(value: str) -> str:
        """Format a bind value for inclusion in SOQL query.

        Args:
            value: Raw value string

        Returns:
            Formatted value with quotes and escaping
        """
        escaped = SOQLSanitizer.escape_string(value)
        return f"'{escaped}'"

    @staticmethod
    def format_bind_values_for_query(values: List[str]) -> str:
        """Format list of bind values for SOQL IN clause.

        Args:
            values: List of values

        Returns:
            Formatted string like ('val1', 'val2', ...)
        """
        formatted = [SOQLSanitizer.format_bind_value(v) for v in values]
        return "(" + ",".join(formatted) + ")"

    @staticmethod
    def clean_metadata(record: any) -> any:
        """Remove Salesforce metadata fields from record.

        Args:
            record: Record dict or nested structure

        Returns:
            Cleaned record without 'attributes' fields
        """
        if isinstance(record, dict):
            return {
                k: SOQLSanitizer.clean_metadata(v)
                for k, v in record.items()
                if k != "attributes"
            }
        elif isinstance(record, list):
            return [SOQLSanitizer.clean_metadata(item) for item in record]
        return record
