"""Salesforce Data Export Module.

Handles export to CSV, JSON, and Excel formats.
"""

import csv
import json
from pathlib import Path
from typing import List, Dict, Any
import logging

try:
    from openpyxl import Workbook
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False

from ..core.exceptions import ExportError

logger = logging.getLogger(__name__)


class DataExporter:
    """Export data to multiple formats."""

    def __init__(self, output_dir: Path):
        """Initialize exporter.

        Args:
            output_dir: Directory for export files
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"DataExporter initialized: {self.output_dir}")

    def export_csv(
        self, headers: List[str], rows: List[List[str]], base_name: str
    ) -> Path:
        """Export data to CSV.

        Args:
            headers: Column headers
            rows: Data rows
            base_name: Base filename (without extension)

        Returns:
            Path to exported file

        Raises:
            ExportError: If export fails
        """
        try:
            filepath = self.output_dir / f"{base_name}.csv"

            with open(filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(headers)
                writer.writerows(rows)

            logger.info(f"CSV exported: {filepath} ({len(rows)} rows)")
            return filepath

        except Exception as e:
            logger.error(f"CSV export failed: {e}")
            raise ExportError(f"Errore export CSV: {e}")

    def export_json(
        self,
        records: List[Dict[str, Any]],
        base_name: str,
        flat: bool = True,
    ) -> Path:
        """Export data to JSON.

        Args:
            records: List of records
            base_name: Base filename (without extension)
            flat: If True, flatten nested objects

        Returns:
            Path to exported file

        Raises:
            ExportError: If export fails
        """
        try:
            filepath = self.output_dir / f"{base_name}.json"

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(records, f, indent=2, ensure_ascii=False)

            logger.info(f"JSON exported: {filepath} ({len(records)} records)")
            return filepath

        except Exception as e:
            logger.error(f"JSON export failed: {e}")
            raise ExportError(f"Errore export JSON: {e}")

    def export_xlsx(
        self, headers: List[str], rows: List[List[str]], base_name: str
    ) -> Path:
        """Export data to Excel.

        Args:
            headers: Column headers
            rows: Data rows
            base_name: Base filename (without extension)

        Returns:
            Path to exported file

        Raises:
            ExportError: If export fails or openpyxl not installed
        """
        if not OPENPYXL_AVAILABLE:
            raise ExportError("openpyxl non installato. Installa con: pip install openpyxl")

        try:
            filepath = self.output_dir / f"{base_name}.xlsx"

            wb = Workbook()
            ws = wb.active
            ws.title = "Data"

            # Write headers
            ws.append(headers)

            # Write rows
            for row in rows:
                ws.append(row)

            # Auto-adjust column widths
            for col_idx, header in enumerate(headers, 1):
                max_length = len(header)
                for row in rows:
                    if col_idx <= len(row):
                        max_length = max(max_length, len(str(row[col_idx - 1])))
                ws.column_dimensions[chr(64 + col_idx)].width = min(max_length + 2, 50)

            wb.save(filepath)

            logger.info(f"XLSX exported: {filepath} ({len(rows)} rows)")
            return filepath

        except Exception as e:
            logger.error(f"XLSX export failed: {e}")
            raise ExportError(f"Errore export XLSX: {e}")
