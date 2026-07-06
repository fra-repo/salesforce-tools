"""Data extraction operations for Salesforce.

Core business logic for extracting, processing, and chunking Salesforce data.
This module is independent of any UI framework.
"""

import re
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
import logging

from ..core.sf_cli import SalesforceCliManager
from ..core.soql_validator import SOQLValidator, SOQLSanitizer
from ..core.exceptions import QueryLimitExceeded, ValidationError

logger = logging.getLogger(__name__)


@dataclass
class SOQLStructure:
    """Represents the structure of a SOQL query."""

    flat_fields: List[str]
    subqueries: List[Dict[str, Any]]
    raw_soql: str


class SalesforceDataExtractor:
    """Extracts Salesforce data with automatic query chunking.

    Handles:
    - Query size validation and chunking
    - Subquery relationship parsing
    - Large-scale bulk queries with record streaming
    """

    # Maximum SOQL query length in Salesforce
    SOQL_SIZE_LIMIT = 18000

    def __init__(self, sf_cli: SalesforceCliManager, org_alias: str):
        """Initialize extractor.

        Args:
            sf_cli: SalesforceCliManager instance
            org_alias: Target organization alias
        """
        self.sf_cli = sf_cli
        self.org_alias = org_alias
        logger.info(f"Initialized DataExtractor for org: {org_alias}")

    def parse_soql_structure(self, soql: str) -> SOQLStructure:
        """Parse SOQL query to extract field and subquery structure.

        Args:
            soql: SOQL query string

        Returns:
            SOQLStructure with parsed fields and subqueries

        Raises:
            ValidationError: If SOQL parsing fails
        """
        # Normalize whitespace
        linear = re.sub(r"\s+", " ", soql)

        # Extract SELECT clause
        select_match = re.search(
            r"\bselect\b(.*)\bfrom\b", linear, re.IGNORECASE
        )
        if not select_match:
            raise ValidationError(
                "soql", "Impossibile estrarre la clausola SELECT dalla query"
            )

        select_body = select_match.group(1).strip()

        # Split by top-level commas (respecting parentheses)
        top_items = self._split_top_level_commas(select_body)

        flat_fields = []
        subqueries = []

        for item in top_items:
            item_clean = item.strip()
            if item_clean.startswith("(") and item_clean.endswith(")"):
                # Try to parse as subquery
                sq_pattern = r"^\(\s*select\s+(?P<fields>.+?)\s+from\s+(?P<relationship>[A-Za-z_][A-Za-z0-9_]*)\b"
                sq_match = re.match(sq_pattern, item_clean, re.IGNORECASE)

                if sq_match:
                    rel = sq_match.group("relationship").strip()
                    fields_str = sq_match.group("fields").strip()
                    fields = [
                        f.strip()
                        for f in self._split_top_level_commas(fields_str)
                        if f.strip()
                    ]
                    subqueries.append(
                        {
                            "relationship": rel,
                            "fields": fields,
                            "raw_item": item_clean,
                        }
                    )
                else:
                    flat_fields.append(item_clean)
            else:
                flat_fields.append(item_clean)

        logger.info(
            f"Parsed SOQL: {len(flat_fields)} flat fields, {len(subqueries)} subqueries"
        )
        return SOQLStructure(flat_fields, subqueries, soql)

    def _split_top_level_commas(self, text: str) -> List[str]:
        """Split string by commas at parenthesis depth 0.

        Args:
            text: Text to split

        Returns:
            List of items
        """
        items = []
        current = []
        depth = 0

        for ch in text:
            if ch == "(":
                depth += 1
                current.append(ch)
            elif ch == ")":
                depth = max(depth - 1, 0)
                current.append(ch)
            elif ch == "," and depth == 0:
                item = "".join(current).strip()
                if item:
                    items.append(item)
                current = []
            else:
                current.append(ch)

        tail = "".join(current).strip()
        if tail:
            items.append(tail)

        return items

    def chunk_bind_values(
        self, bind_values: List[str], chunk_size: int
    ) -> List[List[str]]:
        """Split bind values into chunks.

        Also handles automatic re-chunking if query exceeds size limits.

        Args:
            bind_values: List of values to bind
            chunk_size: Target chunk size

        Returns:
            List of value chunks
        """
        from collections import deque

        # Validate inputs
        SOQLValidator.validate_chunk_size(chunk_size)

        chunks = []
        queue = deque([
            (bind_values, f"C{idx+1}", 0)
            for idx, bind_values in enumerate(
                [bind_values[i : i + chunk_size] for i in range(0, len(bind_values), chunk_size)]
            )
        ])

        while queue:
            values, chunk_id, depth = queue.popleft()
            # Build test query to check size
            test_soql = self._build_test_soql(values)

            if len(test_soql) > self.SOQL_SIZE_LIMIT and len(values) > 1:
                # Too large, split in half
                half = len(values) // 2
                queue.appendleft((values[half:], f"{chunk_id}b", depth + 1))
                queue.appendleft((values[:half], f"{chunk_id}a", depth + 1))
            else:
                chunks.append(values)

        logger.info(f"Created {len(chunks)} chunks from {len(bind_values)} values")
        return chunks

    def _build_test_soql(self, values: List[str]) -> str:
        """Build test SOQL with given values.

        Args:
            values: Values to format

        Returns:
            Test SOQL string
        """
        formatted = SOQLSanitizer.format_bind_values_for_query(values)
        return f"SELECT Id FROM Account WHERE Id IN {formatted}"

    def execute_query(self, soql: str, chunk_values: List[str]) -> List[Dict[str, Any]]:
        """Execute SOQL query with bound values.

        Args:
            soql: SOQL query template with :bind_values placeholder
            chunk_values: Values to bind

        Returns:
            List of records
        """
        # Format bind values
        formatted_values = SOQLSanitizer.format_bind_values_for_query(chunk_values)

        # Replace placeholder
        final_soql = soql.replace(":bind_values", formatted_values)
        final_soql = re.sub(
            r"\(\s*:bind_values\s*\)", f"({formatted_values})", final_soql
        )

        # Execute
        records = self.sf_cli.execute_soql(final_soql, self.org_alias)
        return records

    def process_records_for_export(
        self, records: List[Dict[str, Any]], structure: SOQLStructure
    ) -> Tuple[List[str], List[Dict[str, str]]]:
        """Process records into flat structure for export.

        Handles subquery relationships and flattening.

        Args:
            records: Raw Salesforce records
            structure: SOQL structure info

        Returns:
            Tuple of (headers, flat_rows)
        """
        flat_fields = structure.flat_fields
        subqueries = structure.subqueries

        # Calculate max related counts
        max_related_counts = {}
        for sq in subqueries:
            rel = sq["relationship"]
            max_related_counts[rel] = 0

        for record in records:
            for sq in subqueries:
                rel = sq["relationship"]
                rel_key = next(
                    (k for k in record.keys() if k.lower() == rel.lower()), rel
                )
                sub_data = record.get(rel_key)
                if sub_data and isinstance(sub_data, dict):
                    sub_recs = sub_data.get("records", [])
                    if len(sub_recs) > max_related_counts[rel]:
                        max_related_counts[rel] = len(sub_recs)

        # Ensure at least 1 for each
        for sq in subqueries:
            if max_related_counts[sq["relationship"]] == 0:
                max_related_counts[sq["relationship"]] = 1

        # Build headers
        headers = list(flat_fields)
        for sq in subqueries:
            rel = sq["relationship"]
            for idx in range(max_related_counts[rel]):
                for sub_f in sq["fields"]:
                    headers.append(f"{rel}_{idx+1}_{sub_f}")

        # Flatten records
        flat_rows = []
        for record in records:
            row = {}

            # Flat fields
            for field in flat_fields:
                row[field] = self._extract_flat_value(record, field)

            # Subquery fields
            for sq in subqueries:
                rel = sq["relationship"]
                rel_key = next(
                    (k for k in record.keys() if k.lower() == rel.lower()), rel
                )
                sub_data = record.get(rel_key)
                sub_recs = []
                if sub_data and isinstance(sub_data, dict):
                    sub_recs = sub_data.get("records", [])

                for idx in range(max_related_counts[rel]):
                    has_rec = idx < len(sub_recs)
                    sub_rec = sub_recs[idx] if has_rec else {}
                    for sub_f in sq["fields"]:
                        col_name = f"{rel}_{idx+1}_{sub_f}"
                        row[col_name] = (
                            self._extract_flat_value(sub_rec, sub_f)
                            if has_rec
                            else ""
                        )

            flat_rows.append(row)

        logger.info(f"Processed {len(flat_rows)} records to flat format")
        return headers, flat_rows

    def _extract_flat_value(self, record_dict: Dict[str, Any], field_path: str) -> str:
        """Extract value from nested dict using dot notation.

        Args:
            record_dict: Record dictionary
            field_path: Field path (e.g., 'Account.Name')

        Returns:
            String value or empty string
        """
        parts = field_path.split(".")
        current = record_dict
        for p in parts:
            if isinstance(current, dict):
                matched_key = next(
                    (k for k in current.keys() if k.lower() == p.lower()), p
                )
                current = current.get(matched_key)
            else:
                return ""
        return "" if current is None else str(current)
