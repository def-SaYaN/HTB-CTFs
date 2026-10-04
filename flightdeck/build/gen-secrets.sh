#!/usr/bin/env bash
# Generate per-build secrets and flags, write them where services + users expect.
# Runs ONCE at image build time (see Dockerfile). Every built image is unique.
set -euo pipefail

SVC_USER="svc-mcp"
SECRETS_DIR="/opt/flightdeck"
SECRETS_FILE="${SECRETS_DIR}/secrets.env"

rand() { head -c 32 /dev/urandom | base64 | tr -dc 'A-Za-z0-9' | head -c "${1:-16}"; }

SVC_PASS="$(rand 18)"
DEPLOY_TOKEN="staging-$(rand 6 | tr 'A-Z' 'a-z')"
USER_FLAG="FLIGHTDECK{$(rand 24)}"
ROOT_FLAG="FLIGHTDECK{$(rand 24)}"

mkdir -p "${SECRETS_DIR}"
cat > "${SECRETS_FILE}" <<EOF
SVC_USER=${SVC_USER}
SVC_PASS=${SVC_PASS}
DEPLOY_TOKEN=${DEPLOY_TOKEN}
EOF
chmod 600 "${SECRETS_FILE}"
chown root:root "${SECRETS_FILE}"

# Create the foothold user with the generated password, no sudo.
if ! id "${SVC_USER}" >/dev/null 2>&1; then
    useradd -m -s /bin/bash "${SVC_USER}"
fi
echo "${SVC_USER}:${SVC_PASS}" | chpasswd

# Flags
echo "${USER_FLAG}" > "/home/${SVC_USER}/user.txt"
chown "${SVC_USER}:${SVC_USER}" "/home/${SVC_USER}/user.txt"
chmod 640 "/home/${SVC_USER}/user.txt"

echo "${ROOT_FLAG}" > /root/root.txt
chmod 600 /root/root.txt

# Breadcrumb for the player after foothold: a hint toward the internal panel.
cat > "/home/${SVC_USER}/notes.txt" <<EOF
Reminder from ops:
- The admin panel (flightdeck-admin) runs locally on 127.0.0.1:3000.
- It was pinned to an old Next.js for "stability". Never got patched.
- It runs as root (bad, I know). Ticket OPS-412 still open.
- The old App Router endpoints accept multipart Server Action requests.
EOF
chown "${SVC_USER}:${SVC_USER}" "/home/${SVC_USER}/notes.txt"

mkdir -p "/home/${SVC_USER}/ops"
cat > "/home/${SVC_USER}/ops/OPS-412.txt" <<EOF
OPS-412 - flightdeck-admin runtime risk

Status: deferred
Owner: platform

Observations:
- flightdeck-admin is still using the App Router + React Server Components.
- package.json shows Next.js/React pins from the pre-patch window.
- The endpoint accepts multipart/form-data Server Action traffic.
- Security review mentioned unsafe React Flight deserialization and references
  containing strings like resolved_model, __proto__, constructor, and thenable.
- Do not put this behind the public gateway until patched.

Useful local checks:
  curl -i http://127.0.0.1:3000/api/health
  curl -s http://127.0.0.1:3000/api/test
  grep -R "resolved_model\|constructor:constructor\|Flight" /opt/flightdeck-admin 2>/dev/null
EOF
chown -R "${SVC_USER}:${SVC_USER}" "/home/${SVC_USER}/ops"

cat > "/home/${SVC_USER}/ops/rsc-payload-notes.txt" <<EOF
React Flight parser notes from the review:

- The server receives chunked model data in multipart fields named 0, 1, 2...
- Some chunks are treated as resolved_model values and parsed as JSON.
- Thenables are special: a parsed object with a then property can be invoked.
- The dangerous chain described in the advisory was:
    attacker-controlled chunk -> thenable -> prototype/constructor traversal -> Function constructor
- The review did not include a final exploit payload. Build one in a throwaway file and test against 127.0.0.1:3000.
EOF
chown "${SVC_USER}:${SVC_USER}" "/home/${SVC_USER}/ops/rsc-payload-notes.txt"

# Record the answer key for the box author (NOT readable by the player user).
cat > "${SECRETS_DIR}/ANSWER_KEY.txt" <<EOF
=== FlightDeck answer key (author only) ===
svc user      : ${SVC_USER}
svc password  : ${SVC_PASS}
deploy token  : ${DEPLOY_TOKEN}
user.txt      : ${USER_FLAG}
root.txt      : ${ROOT_FLAG}
EOF
chmod 600 "${SECRETS_DIR}/ANSWER_KEY.txt"

echo "[gen-secrets] done. svc-pass and flags generated."
