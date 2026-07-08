"""Salesforce Data Extraction Module.

Handles SOQL query execution and data extraction with automatic chunking.
"""

import json
from typing import List, Dict, Any, Tuple, Optional
from pathlib import Path
import logging

from ..core.sf_cli import SalesforceCliManager
from ..core.exceptions import (
    QueryExecutionError,
    QueryLimitExceeded,
    ValidationError,
)
from ..core.soql_validator import SOQLValidator, SOQLSanitizer

logger = logging.getLogger(__name__)


class SalesforceDataExtractor:
    """Extract data from Salesforce with automatic chunking."""

    # Limits from Salesforce
    MAX_QUERY_LENGTH = 18000
    QUERY_OVERHEAD = 500  # Buffer for WHERE clause additions
    DEFAULT_CHUNK_SIZE = 200

    def __init__(self, sf_cli: SalesforceCliManager, org_alias: str):
        """Initialize extractor.

        Args:
            sf_cli: SalesforceCliManager instance
            org_alias: Salesforce org alias
        """
        self.sf_cli = sf_cli
        self.org_alias = org_alias
        logger.info(f"DataExtractor initialized for org: {org_alias}")

    def parse_soql_structure(self, soql: str) -> Dict[str, Any]:
        """Parse SOQL query structure without regex backtracking risks."""
        upper_soql = soql.upper()
        select_idx = upper_soql.find("SELECT ")
        from_idx = upper_soql.find(" FROM ", select_idx + len("SELECT "))

        fields: List[str] = []
        if select_idx != -1 and from_idx != -1 and from_idx > select_idx:
            fields_segment = soql[select_idx + len("SELECT ") : from_idx]
            fields = [field.strip() for field in fields_segment.split(",") if field.strip()]

        sobject = None
        if from_idx != -1:
            from_segment = soql[from_idx + len(" FROM ") :].strip()
            if from_segment:
                sobject = from_segment.split()[0].rstrip(",")

        return {
            "fields": fields,
            "sobject": sobject,
            "has_where": " WHERE " in upper_soql,
            "original_query": soql,
        }

    def chunk_bind_values(
        self, values: List[str], chunk_size: int = DEFAULT_CHUNK_SIZE
    ) -> List[List[str]]:
        """Chunk bind values for multiple queries.

        Args:
            values: List of bind values
            chunk_size: Size of each chunk

        Returns:
            List of value chunks
        """
        chunks = []
        for i in range(0, len(values), chunk_size):
            chunks.append(values[i : i + chunk_size])
        logger.info(f"Created {len(chunks)} chunks from {len(values)} values")
        return chunks

    def execute_query(
        self, soql: str, bind_values: List[str]
    ) -> List[Dict[str, Any]]:
        """Execute SOQL query with bind values.

        Args:
            soql: SOQL query with :bind_values placeholder
            bind_values: List of values to bind

        Returns:
            List of records

        Raises:
            QueryExecutionError: If query fails
            QueryLimitExceeded: If query is too long
        """
        try:
            # Validate query
            SOQLValidator.validate_soql(soql)

            # Build WHERE IN clause
            bind_str = ",".join(f"'{SOQLSanitizer.escape_string(v)}'" for v in bind_values)
            final_query = soql.replace(":bind_values", f"({bind_str})")

            # Check length
            if len(final_query) > self.MAX_QUERY_LENGTH:
                raise QueryLimitExceeded(
                    f"Query con bind values supera limite. Lunghezza: {len(final_query)}"
                )

            # Execute query
            result = self.sf_cli.execute_soql(final_query, self.org_alias)

            logger.info(f"Query executed: {len(result)} records")
            return result

        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise QueryExecutionError(f"Errore esecuzione query: {e}")

    def process_records_for_export(
        self, records: List[Dict[str, Any]], structure: Dict[str, Any]
    ) -> Tuple[List[str], List[List[str]]]:
        """Process records for export (flatten nested objects).

        Args:
            records: List of raw records from Salesforce
            structure: Parsed query structure

        Returns:
            Tuple of (headers, flat_rows)
        """
        if not records:
            return [], []

        # Flatten records
        flat_records = []
        all_keys = set()

        for record in records:
            flat = self._flatten_record(record)
            flat_records.append(flat)
            all_keys.update(flat.keys())

        # Sort headers
        headers = sorted(list(all_keys))

        # Convert to rows
        rows = [
            [str(record.get(h, "")) for h in headers] for record in flat_records
        ]

        logger.info(f"Processed {len(rows)} records with {len(headers)} fields")
        return headers, rows

    def _flatten_record(self, obj: Any, prefix: str = "") -> Dict[str, Any]:
        """Recursively flatten nested record.

        Args:
            obj: Object to flatten
            prefix: Current prefix for nested keys

        Returns:
            Flattened dict
        """
        result = {}

        if isinstance(obj, dict):
            for key, value in obj.items():
                if key == "attributes":  # Skip Salesforce metadata
                    continue

                new_key = f"{prefix}.{key}" if prefix else key

                if isinstance(value, (dict, list)):
                    result.update(self._flatten_record(value, new_key))
                else:
                    result[new_key] = value

        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                new_key = f"{prefix}[{i}]"
                result.update(self._flatten_record(item, new_key))
        else:
            result[prefix] = obj

        return result
