#!/usr/bin/env python3
"""
FlightDeck MCP server - a minimal, protocol-accurate JSON-RPC 2.0 / MCP endpoint.

Transport: plain HTTP POST of JSON-RPC 2.0 messages to /mcp (easy to drive with curl).
This intentionally leaks SSH credentials via one of its "tools" once the player
discovers the correct environment token from the runbook tool.

Not production code. Deliberately insecure for a CTF-style lab.
"""
import json
import os
import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# --- Lab secrets are injected at container build time via /opt/flightdeck/secrets.env ---
SECRETS_PATH = os.environ.get("FLIGHTDECK_SECRETS", "/opt/flightdeck/secrets.env")


def load_secrets():
    data = {}
    try:
        with open(SECRETS_PATH) as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                data[k.strip()] = v.strip()
    except FileNotFoundError:
        pass
    return data


SECRETS = load_secrets()
SSH_USER = SECRETS.get("SVC_USER", "svc-mcp")
SSH_PASS = SECRETS.get("SVC_PASS", "changeme")
# The puzzle token the player must find in read_runbook and pass to the creds tool.
DEPLOY_TOKEN = SECRETS.get("DEPLOY_TOKEN", "staging-7f3a")

PROTOCOL_VERSION = "2024-11-05"
SERVER_INFO = {"name": "flightdeck-devops-assistant", "version": "1.0.0"}

# ---------------------------------------------------------------------------
# Tool definitions (what tools/list returns) and their implementations.
# ---------------------------------------------------------------------------
TOOLS = [
    {
        "name": "get_server_time",
        "description": "Return the current server time in UTC. Useful to confirm connectivity.",
        "inputSchema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "list_services",
        "description": "List internal services registered with the DevOps assistant.",
        "inputSchema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "read_runbook",
        "description": "Read an internal operations runbook by name. Try 'deploy'.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Runbook name, e.g. 'deploy'."}
            },
            "required": ["name"],
        },
    },
    {
        "name": "check_deploy_credentials",
        "description": (
            "Fetch deploy credentials for a given environment. Requires a valid "
            "environment token (see the deploy runbook)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "environment": {"type": "string", "description": "Environment name."},
                "token": {"type": "string", "description": "Environment access token."},
            },
            "required": ["environment", "token"],
        },
    },
    {
        "name": "ping_host",
        "description": "Ping an internal host. Restricted to on-call operators.",
        "inputSchema": {
            "type": "object",
            "properties": {"host": {"type": "string"}},
            "required": ["host"],
        },
    },
]


def tool_get_server_time(args):
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    return _text(f"Server time (UTC): {now}")


def tool_list_services(args):
    services = (
        "Registered services:\n"
        "  - mcp-devops-assistant   (this service)          :80/mcp   [public]\n"
        "  - flightdeck-admin       (Next.js admin panel)   127.0.0.1:3000 [internal, runs as root]\n"
        "  - edge-gateway           (HTTP/SSH multiplexer)  :80       [public]\n"
        "  - sshd                   (remote access)         :22       [behind gateway]\n"
        "\nNote: the admin panel is only reachable from the host itself. "
        "SSH is routed through the public gateway port."
    )
    return _text(services)


def tool_read_runbook(args):
    name = (args or {}).get("name", "")
    if name == "deploy":
        body = (
            "=== RUNBOOK: deploy ===\n"
            "1. Deploys are triggered from the staging environment.\n"
            "2. To pull deploy credentials, call check_deploy_credentials with:\n"
            f"       environment = \"staging\"\n"
            f"       token       = \"{DEPLOY_TOKEN}\"\n"
            "3. The service account svc-mcp is used for rsync + ssh deploys.\n"
            "4. TODO(ops): rotate the svc-mcp password, it has been static for months.\n"
        )
        return _text(body)
    return _text(
        "Unknown runbook. Available runbooks: ['deploy']. "
        "Try: read_runbook with name='deploy'."
    )


def tool_check_deploy_credentials(args):
    args = args or {}
    env = args.get("environment", "")
    token = args.get("token", "")
    if env != "staging":
        return _text("No credentials registered for that environment.")
    if token != DEPLOY_TOKEN:
        return _text("Invalid environment token. Check the deploy runbook.", is_error=True)
    creds = {
        "environment": "staging",
        "user": SSH_USER,
        "host": "flightdeck",
        "port": 80,
        "auth": "password",
        "password": SSH_PASS,
        "note": "rotate me (see deploy runbook TODO)",
    }
    return _text("Deploy credentials:\n" + json.dumps(creds, indent=2))


def tool_ping_host(args):
    return _text(
        "Error: unauthorized. ping_host is restricted to on-call operators.",
        is_error=True,
    )


TOOL_IMPL = {
    "get_server_time": tool_get_server_time,
    "list_services": tool_list_services,
    "read_runbook": tool_read_runbook,
    "check_deploy_credentials": tool_check_deploy_credentials,
    "ping_host": tool_ping_host,
}


def _text(text, is_error=False):
    """Shape a result like an MCP tools/call content block."""
    return {"content": [{"type": "text", "text": text}], "isError": is_error}


# ---------------------------------------------------------------------------
# JSON-RPC 2.0 dispatch
# ---------------------------------------------------------------------------
def handle_rpc(msg):
    if not isinstance(msg, dict) or msg.get("jsonrpc") != "2.0":
        return _err(None, -32600, "Invalid Request")

    method = msg.get("method")
    mid = msg.get("id")
    params = msg.get("params") or {}

    if method == "initialize":
        return _ok(mid, {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": SERVER_INFO,
        })

    if method == "notifications/initialized":
        return None  # notification, no response

    if method == "ping":
        return _ok(mid, {})

    if method == "tools/list":
        return _ok(mid, {"tools": TOOLS})

    if method == "tools/call":
        name = params.get("name")
        args = params.get("arguments", {})
        impl = TOOL_IMPL.get(name)
        if impl is None:
            return _err(mid, -32602, f"Unknown tool: {name}")
        try:
            return _ok(mid, impl(args))
        except Exception as exc:  # noqa: BLE001
            return _err(mid, -32603, f"Tool execution error: {exc}")

    return _err(mid, -32601, f"Method not found: {method}")


def _ok(mid, result):
    return {"jsonrpc": "2.0", "id": mid, "result": result}


def _err(mid, code, message):
    return {"jsonrpc": "2.0", "id": mid, "error": {"code": code, "message": message}}


class Handler(BaseHTTPRequestHandler):
    server_version = "ModelContextProtocol/1.0"

    def _send(self, code, payload):
        body = json.dumps(payload).encode() if payload is not None else b""
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("X-Powered-By", "ModelContextProtocol/1.0")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if body:
            self.wfile.write(body)

    def do_GET(self):
        # A friendly nudge if someone browses the endpoint instead of POSTing.
        self._send(200, {
            "service": "flightdeck-devops-assistant",
            "transport": "jsonrpc-2.0 over HTTP POST",
            "hint": "POST a JSON-RPC 2.0 'initialize' request here, then 'tools/list'.",
        })

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0) or 0)
        raw = self.rfile.read(length) if length else b""
        try:
            msg = json.loads(raw.decode() or "{}")
        except json.JSONDecodeError:
            self._send(200, _err(None, -32700, "Parse error"))
            return

        if isinstance(msg, list):  # batch
            out = [r for r in (handle_rpc(m) for m in msg) if r is not None]
            self._send(200, out)
            return

        resp = handle_rpc(msg)
        if resp is None:
            self._send(202, None)  # notification acknowledged
        else:
            self._send(200, resp)

    def log_message(self, fmt, *args):
        pass  # quiet


def main():
    port = int(os.environ.get("MCP_PORT", "9000"))
    httpd = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"[mcp] listening on 127.0.0.1:{port}", flush=True)
    httpd.serve_forever()


if __name__ == "__main__":
    main()
