#!/usr/bin/env bash
# FlightDeck lifecycle helper: build / run / reset / stop / logs / answerkey.
# Usage: ./scripts/flightdeck.sh <command>
set -euo pipefail

IMAGE="flightdeck:latest"
NAME="flightdeck"
PORT="${FLIGHTDECK_PORT:-8080}"      # host port -> container :80 (HTTP + SSH via sslh)
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

build() {
    echo "[build] building ${IMAGE} (regenerates secrets + flags)..."
    docker build --no-cache -t "${IMAGE}" "${ROOT_DIR}"
    echo "[build] done."
}

run() {
    stop || true
    echo "[run] starting ${NAME} on http://localhost:${PORT} (HTTP + SSH share this one port)..."
    docker run -d --name "${NAME}" -p "${PORT}:80" "${IMAGE}"
    echo "[run] up. Player entrypoint: http://localhost:${PORT}"
    echo "[run] SSH after creds leak: ssh -p ${PORT} svc-mcp@localhost"
}

# Full reset: rebuild image (new secrets/flags) and restart the container.
reset() {
    echo "[reset] full reset: new secrets, flags, and clean state."
    build
    run
    echo "[reset] complete."
}

# Soft reset: recreate container from the current image (same flags) -> wipes
# any player changes but keeps the same secrets. Fast.
softreset() {
    echo "[softreset] recreating container from existing image (same flags)..."
    stop || true
    run
    echo "[softreset] complete."
}

stop() {
    if docker ps -a --format '{{.Names}}' | grep -q "^${NAME}$"; then
        echo "[stop] removing container ${NAME}..."
        docker rm -f "${NAME}" >/dev/null
    fi
}

logs() {
    docker logs -f "${NAME}"
}

# Print the author answer key (creds + flags) from inside the running container.
answerkey() {
    docker exec "${NAME}" cat /opt/flightdeck/ANSWER_KEY.txt
}

shell() {
    docker exec -it "${NAME}" /bin/bash
}

status() {
    docker ps --filter "name=${NAME}"
}

case "${1:-}" in
    build)      build ;;
    run)        run ;;
    reset)      reset ;;
    softreset)  softreset ;;
    stop)       stop ;;
    logs)       logs ;;
    answerkey)  answerkey ;;
    shell)      shell ;;
    status)     status ;;
    *)
        cat <<USAGE
FlightDeck helper
  build       Build image (NEW secrets + flags each time)
  run         Run container (host :${PORT} -> container :80, HTTP + SSH)
  reset       Full reset: rebuild (new flags) + restart
  softreset   Recreate container from current image (same flags, wipes player changes)
  stop        Stop & remove container
  logs        Tail container logs
  answerkey   Print author answer key (creds + flags)
  shell       Root shell inside the container
  status      Show container status

Env: FLIGHTDECK_PORT (default 8080)
USAGE
        ;;
esac
