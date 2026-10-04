# FlightDeck - HackTheBox-style single-container box.
# Chain: HTTP recon -> MCP JSON-RPC creds leak -> SSH foothold ->
#        internal enum -> React2Shell (CVE-2025-55182) privesc to root.
FROM debian:12-slim

ENV DEBIAN_FRONTEND=noninteractive

# ---- Base packages: ssh, nginx, python, supervisor, curl, node toolchain ----
RUN apt-get update && apt-get install -y --no-install-recommends \
        openssh-server \
        nginx \
        sslh \
        python3 \
        supervisor \
        curl \
        ca-certificates \
        procps \
        iproute2 \
        gnupg \
        xz-utils \
    && rm -rf /var/lib/apt/lists/*

# ---- Node.js 18 from official tarball ----
ENV NODE_VERSION=18.20.4
RUN set -eux; \
    arch="$(dpkg --print-architecture)"; \
    case "$arch" in \
        amd64) nodearch="x64" ;; \
        arm64) nodearch="arm64" ;; \
        *) echo "unsupported arch: $arch" >&2; exit 1 ;; \
    esac; \
    curl -fsSL "https://nodejs.org/dist/v${NODE_VERSION}/node-v${NODE_VERSION}-linux-${nodearch}.tar.xz" -o /tmp/node.tar.xz; \
    tar -xJf /tmp/node.tar.xz -C /usr/local --strip-components=1 --no-same-owner; \
    rm /tmp/node.tar.xz; \
    node --version; npm --version

# ---- sshd config: password auth on, root login off ----
RUN sed -i 's/#\?PasswordAuthentication.*/PasswordAuthentication yes/' /etc/ssh/sshd_config \
    && sed -i 's/#\?PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config \
    && sed -i 's/#\?UsePAM.*/UsePAM yes/' /etc/ssh/sshd_config

# ---- Front (nginx) ----
RUN rm -f /etc/nginx/sites-enabled/default
COPY front/nginx.conf /etc/nginx/nginx.conf
COPY front/index.html /var/www/flightdeck/index.html
COPY front/robots.txt /var/www/flightdeck/robots.txt
COPY front/flightdeck-ai /var/www/flightdeck-ai

# ---- MCP server ----
COPY mcp/server.py /opt/flightdeck/mcp/server.py

# ---- Vulnerable Next.js admin panel (pinned vulnerable versions) ----
WORKDIR /opt/flightdeck-admin
COPY nextapp/package.json ./package.json
COPY nextapp/next.config.js ./next.config.js
COPY nextapp/app ./app
# Install EXACT pinned versions (no caret resolution) and build.
RUN npm install --no-audit --no-fund --save-exact --legacy-peer-deps \
        next@15.0.0 react@19.0.0 react-dom@19.0.0 \
    && npm run build

# ---- Supervisor + entrypoint ----
COPY build/supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY build/entrypoint.sh /usr/local/bin/entrypoint.sh
COPY build/gen-secrets.sh /usr/local/bin/gen-secrets.sh
RUN chmod +x /usr/local/bin/entrypoint.sh /usr/local/bin/gen-secrets.sh

# ---- Generate per-build secrets, user, and flags (ONCE, at build) ----
RUN /usr/local/bin/gen-secrets.sh

# Only HTTP is exposed to the player. 22 and 3000 stay internal.
EXPOSE 80

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
