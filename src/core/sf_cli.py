"""Centralized Salesforce CLI interface.

This module provides a unified wrapper around the Salesforce CLI (sf/sfdx),
handling command execution, org discovery, and error handling.
"""

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging

from .exceptions import (
    CliNotFound,
    AuthenticationError,
    OrgNotFound,
    QueryLimitExceeded,
    QueryExecutionError,
)

logger = logging.getLogger(__name__)
CLI_ARG_PATTERN = re.compile(r'^[A-Za-z0-9_@.,:=()<>%!/"\'\s-]+$')


class SalesforceCliManager:
    """Manages interaction with Salesforce CLI (sf/sfdx).

    This class handles:
    - CLI availability detection
    - Org alias discovery and caching
    - SOQL query execution with error handling
    - Org validation
    """

    # SOQL query size limit in Salesforce
    SOQL_SIZE_LIMIT = 18000
    # CLI timeout in seconds
    CLI_TIMEOUT = 40

    def __init__(self):
        """Initialize CLI manager.

        Raises:
            CliNotFound: If neither 'sf' nor 'sfdx' is available in PATH
        """
        self.sf_command = self._find_cli_command()
        self._org_cache: Dict[str, str] = {}  # username -> alias mapping
        self._aliases_cache: Optional[List[str]] = None
        logger.info(f"Salesforce CLI Manager initialized with command: {self.sf_command}")

    def _find_cli_command(self) -> str:
        """Find Salesforce CLI command in PATH.

        Tries in order: sf, sf.cmd (Windows), sfdx, sfdx.cmd (Windows)

        Returns:
            str: The CLI command name

        Raises:
            CliNotFound: If no CLI command is found
        """
        candidates = ("sf", "sf.cmd", "sfdx", "sfdx.cmd")
        for candidate in candidates:
            if shutil.which(candidate):
                logger.info(f"Found Salesforce CLI: {candidate}")
                return candidate
        raise CliNotFound()

    def _run_command(
        self, args: List[str], timeout: int = CLI_TIMEOUT
    ) -> Dict[str, Any]:
        """Execute Salesforce CLI command and return parsed JSON result.

        Args:
            args: Command arguments (e.g., ["org", "list", "--json"])
            timeout: Command timeout in seconds

        Returns:
            Dict with 'success', 'stdout', 'stderr', 'returncode'

        Raises:
            QueryExecutionError: If command fails
        """
        safe_args = []
        for arg in args:
            if not isinstance(arg, str):
                raise QueryExecutionError("", "Argomento CLI non valido", {"argument_type": type(arg).__name__})
            if not CLI_ARG_PATTERN.fullmatch(arg):
                raise QueryExecutionError("", "Argomento CLI contiene caratteri non validi", {"argument": arg})
            safe_args.append(arg)

        cmd = [self.sf_command] + safe_args
        logger.debug(f"Running: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                shell=False,
            )

            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
            }
        except subprocess.TimeoutExpired:
            logger.error(f"Command timeout after {timeout}s: {' '.join(cmd)}")
            raise QueryExecutionError(
                "",
                f"Comando Salesforce CLI timeout dopo {timeout}s",
                {"timeout": timeout, "command": " ".join(cmd)},
            )
        except Exception as e:
            logger.error(f"Command execution failed: {e}")
            raise QueryExecutionError("", str(e), {"exception": type(e).__name__})

    def discover_org_aliases(self, force_refresh: bool = False) -> List[str]:
        """Discover all authenticated Salesforce orgs.

        Uses a two-stage approach:
        1. Check local filesystem cache (~/.config/sf/ or ~/.sfdx/)
        2. Fallback to 'sf org list' CLI command if cache is empty

        Args:
            force_refresh: If True, skip cache and query CLI directly

        Returns:
            List of org aliases (sorted, deduplicated)

        Raises:
            CliNotFound: If Salesforce CLI not found
        """
        if self._aliases_cache and not force_refresh:
            logger.debug(f"Returning cached aliases: {len(self._aliases_cache)} orgs")
            return self._aliases_cache

        aliases = []
        alias_map = {}

        # Stage 1: Check filesystem cache
        aliases.extend(self._discover_from_filesystem(alias_map))

        # Stage 2: Fallback to CLI if no aliases found
        if not aliases:
            logger.info("No aliases found in filesystem cache, querying CLI...")
            aliases.extend(self._discover_from_cli())

        # Deduplicate and sort
        aliases = sorted(list(set(aliases)))
        self._aliases_cache = aliases
        logger.info(f"Discovered {len(aliases)} org aliases")
        return aliases

    def _discover_from_filesystem(self, alias_map: Dict[str, str]) -> List[str]:
        """Discover orgs from local filesystem cache.

        Args:
            alias_map: Dict to populate with username -> alias mappings

        Returns:
            List of discovered org aliases
        """
        aliases = []

        for alias_file in (
            Path.home() / ".config" / "sf" / "alias.json",
            Path.home() / ".sfdx" / "alias.json",
        ):
            if alias_file.exists():
                try:
                    with open(alias_file, "r", encoding="utf-8") as f:
                        alias_data = json.load(f)
                    self._collect_aliases_from_json(alias_data, alias_map, aliases)
                    logger.debug(f"Loaded aliases from {alias_file}: {len(aliases)}")
                except Exception as e:
                    logger.warning(f"Failed to read {alias_file}: {e}")

        # Scan org config directories for usernames
        for folder in (
            Path.home() / ".config" / "sf",
            Path.home() / ".sfdx",
        ):
            if folder.exists():
                for entry in folder.glob("*.json"):
                    if entry.name in {"alias.json", "config.json", "state.json", "stash.json"}:
                        continue
                    if entry.stem.startswith("log-"):
                        continue
                    if "@" in entry.stem:
                        alias = alias_map.get(entry.stem)
                        if alias:
                            aliases.append(f"{alias} ({entry.stem})")
                        else:
                            aliases.append(entry.stem)

        return aliases

    def _collect_aliases_from_json(
        self, data: Any, alias_map: Dict[str, str], aliases: List[str]
    ) -> None:
        """Parse alias JSON and populate mappings.

        Args:
            data: Parsed JSON data from alias file
            alias_map: Dict to populate with username -> alias
            aliases: List to populate with alias strings
        """
        if isinstance(data, dict):
            org_aliases = data.get("orgs", data)
            if isinstance(org_aliases, dict):
                for alias, username in org_aliases.items():
                    alias_map[username] = alias
                    aliases.append(f"{alias} ({username})")
            elif isinstance(org_aliases, list):
                for item in org_aliases:
                    if isinstance(item, dict):
                        alias = item.get("alias")
                        username = item.get("username")
                        if alias and username:
                            alias_map[username] = alias
                            aliases.append(f"{alias} ({username})")
                        elif alias:
                            aliases.append(alias)
                        elif username:
                            aliases.append(username)

    def _discover_from_cli(self) -> List[str]:
        """Discover orgs using 'sf org list' command.

        Returns:
            List of org aliases from CLI
        """
        aliases = []
        try:
            result = self._run_command(
                ["org", "list", "--skip-connection-status", "--json"]
            )

            if result["success"] and result["stdout"].strip():
                data = json.loads(result["stdout"])
                result_obj = data.get("result", {})

                for key in ("nonScratchOrgs", "scratchOrgs"):
                    for org in result_obj.get(key, []):
                        alias = org.get("alias")
                        username = org.get("username")
                        if alias and username:
                            aliases.append(f"{alias} ({username})")
                        elif alias:
                            aliases.append(alias)
                        elif username:
                            aliases.append(username)
            else:
                logger.warning(
                    f"CLI org list failed: {result.get('stderr', 'Unknown error')}"
                )
        except Exception as e:
            logger.error(f"Failed to query CLI for orgs: {e}")

        return aliases

    def validate_org(self, org_alias: str) -> bool:
        """Validate that org is authenticated and accessible.

        Args:
            org_alias: Organization alias or username

        Returns:
            True if org is valid, False otherwise
        """
        try:
            result = self._run_command(
                ["org", "display", "--target-org", org_alias, "--json"]
            )
            is_valid = result["success"] and result["returncode"] == 0
            logger.info(f"Org validation for '{org_alias}': {is_valid}")
            return is_valid
        except Exception as e:
            logger.warning(f"Org validation failed for '{org_alias}': {e}")
            return False

    def get_limits(self, org_alias: str) -> Any:
        """Retrieve platform limits for the target org."""
        if not self.validate_org(org_alias):
            raise OrgNotFound(org_alias)

        result = self._run_command(
            ["org", "list", "limits", "--target-org", org_alias, "--json"]
        )
        if not result["success"]:
            raise QueryExecutionError(org_alias, result.get("stderr", "Unknown error"), result)

        try:
            payload = json.loads(result["stdout"])
        except json.JSONDecodeError as e:
            raise QueryExecutionError(org_alias, f"Risposta CLI non valida: {e}", {"response": result})

        if isinstance(payload, dict):
            return payload.get("result", payload)
        return payload

    def execute_soql(
        self, soql: str, org_alias: str, validate_size: bool = True
    ) -> List[Dict[str, Any]]:
        """Execute SOQL query against target org.

        Args:
            soql: SOQL query string
            org_alias: Target organization alias
            validate_size: If True, check query size before execution

        Returns:
            List of record dictionaries

        Raises:
            OrgNotFound: If org is not authenticated
            QueryLimitExceeded: If query exceeds size limit
            QueryExecutionError: If query execution fails
        """
        # Validate org
        if not self.validate_org(org_alias):
            raise OrgNotFound(org_alias)

        # Validate query size
        if validate_size and len(soql) > self.SOQL_SIZE_LIMIT:
            raise QueryLimitExceeded(len(soql), self.SOQL_SIZE_LIMIT)

        logger.info(
            f"Executing SOQL ({len(soql)} chars) on org '{org_alias}'"
        )

        try:
            result = self._run_command(
                ["data", "query", "--query", soql, "--target-org", org_alias, "--json"]
            )

            if not result["success"]:
                error_msg = result.get("stderr", "Unknown error")
                raise QueryExecutionError(org_alias, error_msg, result)

            data = json.loads(result["stdout"])
            records = data.get("result", {}).get("records", [])
            logger.info(f"Query returned {len(records)} records")
            return records

        except QueryExecutionError:
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse CLI response: {e}")
            raise QueryExecutionError(
                org_alias, f"Risposta CLI non valida: {e}", {"response": result}
            )
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise QueryExecutionError(org_alias, str(e))

    def clear_cache(self) -> None:
        """Clear cached org data."""
        self._org_cache.clear()
        self._aliases_cache = None
        logger.info("Org cache cleared")
