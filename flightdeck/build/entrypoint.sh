#!/usr/bin/env bash
set -euo pipefail

# Ensure runtime dirs exist (volumes / fresh containers).
mkdir -p /run/sshd /var/log/nginx

# Hand off to supervisord which manages sshd, mcp, nginx, nextjs.
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf
