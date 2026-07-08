"""Threaded stdlib HTTP server for the TypeScript frontend."""

from __future__ import annotations

import json
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from src.api.service import build_app_state, execute_massive_query, normalize_limits, normalize_org_alias
from src.config import AppConfig
from src.core.exceptions import SalesforceError
from src.core.sf_cli import SalesforceCliManager


def _friendly_error_message(exc: Exception) -> str:
    message = str(exc).strip()
    if message:
        return message
    if type(exc).__name__ == "CliNotFound":
        return "Salesforce CLI non trovata. Installa 'sf' o 'sfdx' per usare org discovery, query e limiti live."
    return type(exc).__name__


class SalesforceToolsApiHandler(BaseHTTPRequestHandler):
    """Serve a minimal JSON API for the React frontend."""

    server_version = "SalesforceToolsApi/1.0"

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(HTTPStatus.NO_CONTENT)
        self._send_common_headers()
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/api/health":
                config = AppConfig.load()
                cli_available = True
                cli_error = None
                try:
                    cli = SalesforceCliManager()
                    org_count = len(cli.discover_org_aliases())
                except Exception as exc:  # pragma: no cover - environment dependent
                    cli_available = False
                    cli_error = _friendly_error_message(exc)
                    org_count = 0
                self._send_json(
                    {
                        "status": "ok",
                        "cliAvailable": cli_available,
                        "cliError": cli_error,
                        "orgCount": org_count,
                        **build_app_state(config),
                    }
                )
                return

            if parsed.path == "/api/orgs":
                try:
                    cli = SalesforceCliManager()
                    items = cli.discover_org_aliases()
                    error = None
                except Exception as exc:
                    items = []
                    error = _friendly_error_message(exc)
                self._send_json({"items": items, "error": error})
                return

            if parsed.path == "/api/limits":
                query = parse_qs(parsed.query)
                org = normalize_org_alias((query.get("org") or [""])[0])
                if not org:
                    self._send_error_json(HTTPStatus.BAD_REQUEST, "Missing org parameter")
                    return
                cli = SalesforceCliManager()
                result = cli._run_command(["org", "list", "limits", "--target-org", org, "--json"])
                if not result["success"]:
                    self._send_error_json(HTTPStatus.BAD_GATEWAY, result.get("stderr", "Unknown error"))
                    return
                raw_payload = json.loads(result["stdout"])
                self._send_json({"items": normalize_limits(raw_payload), "orgAlias": org})
                return

            self._send_error_json(HTTPStatus.NOT_FOUND, "Endpoint not found")
        except SalesforceError as exc:
            self._send_error_json(HTTPStatus.BAD_REQUEST, str(exc))
        except Exception as exc:  # pragma: no cover - exercised manually
            self._send_error_json(HTTPStatus.INTERNAL_SERVER_ERROR, str(exc))

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        try:
            if parsed.path != "/api/massive-query/execute":
                self._send_error_json(HTTPStatus.NOT_FOUND, "Endpoint not found")
                return
            payload = self._read_json_body()
            result = execute_massive_query(payload)
            self._send_json(result, status=HTTPStatus.CREATED)
        except SalesforceError as exc:
            self._send_error_json(HTTPStatus.BAD_REQUEST, str(exc))
        except Exception as exc:  # pragma: no cover - exercised manually
            self._send_error_json(HTTPStatus.INTERNAL_SERVER_ERROR, str(exc))

    def _read_json_body(self) -> dict:
        content_length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(content_length) if content_length > 0 else b"{}"
        if not raw_body:
            return {}
        return json.loads(raw_body.decode("utf-8"))

    def _send_common_headers(self) -> None:
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _send_json(self, payload: dict, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self._send_common_headers()
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_error_json(self, status: HTTPStatus, message: str) -> None:
        self._send_json({"error": message}, status=status)

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return


def main() -> None:
    host = os.environ.get("SALESFORCE_TOOLS_API_HOST", "127.0.0.1")
    port = int(os.environ.get("SALESFORCE_TOOLS_API_PORT", "8000"))
    server = ThreadingHTTPServer((host, port), SalesforceToolsApiHandler)
    print(f"Salesforce Tools API listening on http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
