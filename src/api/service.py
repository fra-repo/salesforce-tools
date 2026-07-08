"""Backend service helpers for the TypeScript frontend."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from src.config import AppConfig
from src.core.exceptions import ValidationError
from src.core.sf_cli import SalesforceCliManager
from src.core.soql_validator import SOQLValidator
from src.operations.data_extractor import SalesforceDataExtractor
from src.operations.data_exporter import DataExporter

UI_DISCOVERY: Dict[str, Any] = {
    "hasWebUi": False,
    "summary": (
        "La UI corrente è una GUI desktop Python basata su tkinter/customtkinter; "
        "non sono presenti template HTML né framework web nel repository."
    ),
    "activeUi": [
        {
            "path": "salesforce_tool.py",
            "kind": "desktop shell",
            "details": "Entry point CustomTkinter che compone la sidebar e le tre schermate principali.",
        },
        {
            "path": "src/ui/massive_query_app.py",
            "kind": "desktop screen",
            "details": "Schermata Massive Query con org selector, query SOQL, bind values e export.",
        },
        {
            "path": "src/ui/viewer_app.py",
            "kind": "desktop screen",
            "details": "Visualizzatore locale di file CSV/JSON con filtro, paginazione e vista raw.",
        },
        {
            "path": "src/ui/limit_monitor_app.py",
            "kind": "desktop screen",
            "details": "Monitor limiti Salesforce con gauge visuali e selezione org.",
        },
        {
            "path": "src/ui/modern_components.py",
            "kind": "desktop ui kit",
            "details": "Libreria di componenti e tema per la GUI desktop esistente.",
        },
    ],
    "legacyUi": [
        {
            "path": "massive_query_salesforce.py",
            "kind": "legacy standalone desktop",
            "details": "Versione standalone storica del Massive Query Tool.",
        },
        {
            "path": "salesforce_viewer.py",
            "kind": "legacy standalone desktop",
            "details": "Versione standalone storica del Data Viewer.",
        },
        {
            "path": "platform_limit.py",
            "kind": "legacy standalone desktop",
            "details": "Versione standalone storica del monitor limiti.",
        },
    ],
    "notUi": [
        {
            "path": "src/core",
            "kind": "backend/core",
            "details": "Wrapper CLI Salesforce, validazioni ed eccezioni; logica senza UI.",
        },
        {
            "path": "src/operations",
            "kind": "backend/services",
            "details": "Estrazione dati ed export multi-formato; servizi riusabili dalla UI web.",
        },
        {
            "path": "src/config.py",
            "kind": "config",
            "details": "Configurazione persistente condivisa, non una UI.",
        },
    ],
    "futureUiEntryPoints": [
        {
            "path": "src/core/sf_cli.py",
            "details": "Punto di integrazione naturale per org discovery, query SOQL e chiamate CLI riusabili via HTTP.",
        },
        {
            "path": "src/operations/data_extractor.py",
            "details": "Adatto a diventare il service backend per la schermata Massive Query web.",
        },
        {
            "path": "src/operations/data_exporter.py",
            "details": "Può continuare a gestire export server-side per CSV/JSON/Excel.",
        },
    ],
}


def split_bind_values(raw_text: str) -> List[str]:
    """Split textarea bind values using the same delimiters as the desktop UI."""
    values = []
    normalized = raw_text.replace(",", "\n").replace(";", "\n").replace("\t", "\n")
    for token in normalized.splitlines():
        cleaned = token.strip().strip("'\"")
        if cleaned:
            values.append(cleaned)
    return values


def normalize_org_alias(label: str) -> str:
    """Normalize an org label like 'alias (user@example.com)' to the CLI target alias."""
    return label.split(" (", 1)[0].strip()


def normalize_limits(raw_limits: Any) -> List[Dict[str, Any]]:
    """Normalize Salesforce limits payload into a consistent structure for the web UI."""
    if isinstance(raw_limits, dict):
        entries = raw_limits.get("result", raw_limits)
        if isinstance(entries, dict):
            entries = [entries]
    elif isinstance(raw_limits, list):
        entries = raw_limits
    else:
        entries = []

    normalized: List[Dict[str, Any]] = []
    for item in entries:
        if not isinstance(item, dict):
            continue
        name = item.get("name") or item.get("Name") or item.get("LIMIT_NAME") or "N/A"
        used = item.get("usato") or item.get("Usato") or item.get("used") or item.get("Used") or 0
        total = (
            item.get("massimo")
            or item.get("Massimo")
            or item.get("total")
            or item.get("Total")
            or item.get("max")
            or item.get("Max")
            or 0
        )
        try:
            used_value = int(used) if used else 0
            total_value = int(total) if total else 0
        except (TypeError, ValueError):
            used_value = 0
            total_value = 0
        percentage = (used_value / total_value * 100) if total_value > 0 else 0
        normalized.append(
            {
                "name": name,
                "used": used_value,
                "total": total_value,
                "percentage": round(percentage, 1),
            }
        )
    return normalized




def resolve_output_dir(raw_output_dir: str, default_output_dir: str) -> Path:
    """Resolve output directory while constraining writes to the current workspace."""
    workspace_root = Path.cwd().resolve()
    candidate = Path(raw_output_dir or default_output_dir).expanduser()
    if not candidate.is_absolute():
        candidate = (workspace_root / candidate).resolve()
    else:
        candidate = candidate.resolve()

    try:
        candidate.relative_to(workspace_root)
    except ValueError as exc:
        raise ValidationError(
            "La cartella output deve trovarsi all'interno della repository corrente"
        ) from exc

    return candidate


def build_app_state(config: AppConfig | None = None) -> Dict[str, Any]:
    """Build a frontend-friendly app state payload."""
    current = config or AppConfig.load()
    return {
        "appName": "Salesforce Tools Suite",
        "version": "2.0",
        "uiDiscovery": UI_DISCOVERY,
        "defaults": {
            "chunkSize": current.chunk_size,
            "outputDir": current.default_output_dir,
            "exportFormats": current.export_formats,
            "theme": current.theme,
            "pageSize": current.page_size,
        },
        "features": [
            {
                "id": "massive-query",
                "title": "Massive Query",
                "status": "migrated-initial",
                "notes": "Collegato ai servizi Python esistenti per org discovery, query SOQL ed export server-side.",
            },
            {
                "id": "viewer",
                "title": "Data Viewer",
                "status": "migrated-initial",
                "notes": "Porting web client-side di upload file, filtro globale, paginazione e raw view.",
            },
            {
                "id": "limits",
                "title": "Platform Limits",
                "status": "migrated-initial",
                "notes": "Collegato al backend Python tramite adapter HTTP minimale.",
            },
            {
                "id": "future-roadmap",
                "title": "Schema Browser / Saved Queries",
                "status": "todo",
                "notes": "Placeholder derivato dal backlog: richiede API dedicate non ancora presenti nel backend.",
            },
        ],
    }


def execute_massive_query(payload: Dict[str, Any], config: AppConfig | None = None) -> Dict[str, Any]:
    """Execute the core Massive Query workflow for the web frontend."""
    current = config or AppConfig.load()
    org_alias = normalize_org_alias(str(payload.get("orgAlias", "")).strip())
    soql = str(payload.get("soql", "")).strip()
    bind_values = split_bind_values(str(payload.get("bindValues", "")))
    chunk_size = int(payload.get("chunkSize") or current.chunk_size)
    output_dir = resolve_output_dir(
        str(payload.get("outputDir") or ""),
        current.default_output_dir,
    )
    export_formats = payload.get("exportFormats") or current.export_formats

    if not org_alias:
        raise ValidationError("Seleziona un org")

    SOQLValidator.validate_soql(soql)
    SOQLValidator.check_bind_values_in_query(soql)

    if not bind_values:
        raise ValidationError("Nessun valore di bind")

    cli_manager = SalesforceCliManager()
    extractor = SalesforceDataExtractor(cli_manager, org_alias)
    exporter = DataExporter(output_dir)
    structure = extractor.parse_soql_structure(soql)
    chunks = extractor.chunk_bind_values(bind_values, chunk_size)

    all_records: List[Dict[str, Any]] = []
    for chunk in chunks:
        all_records.extend(extractor.execute_query(soql, chunk))

    headers, flat_rows = extractor.process_records_for_export(all_records, structure)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = f"extract_{timestamp}"

    exported_files: List[str] = []
    if "csv" in export_formats:
        exported_files.append(str(exporter.export_csv(headers, flat_rows, base_name)))
    if "json" in export_formats:
        exported_files.append(str(exporter.export_json(all_records, base_name, flat=False)))
    if "xlsx" in export_formats:
        exported_files.append(str(exporter.export_xlsx(headers, flat_rows, base_name)))

    return {
        "orgAlias": org_alias,
        "chunkCount": len(chunks),
        "bindValueCount": len(bind_values),
        "recordCount": len(all_records),
        "headers": headers,
        "previewRows": flat_rows[:10],
        "exportedFiles": exported_files,
        "outputDir": str(output_dir.resolve()),
    }
