# Docker Challenge Quick Start

This repository contains a self-contained Docker-based security challenge. The same workflow can be used for similar challenge projects: build the image, start the container, connect to the exposed port, and reset when needed.

## Requirements

- Docker Desktop or Docker Engine
- Bash-compatible shell
- Optional: `nmap`, `curl`, and `ssh` for local testing

## Build

From the challenge directory:

```bash
./scripts/flightdeck.sh build
```

The build creates the Docker image and generates fresh challenge secrets and flags. Rebuilding the image changes those generated values.

## Run

```bash
./scripts/flightdeck.sh run
```

By default, the challenge is exposed on host port `8080`:

```text
http://localhost:8080/
```

To use a different host port:

```bash
FLIGHTDECK_PORT=9000 ./scripts/flightdeck.sh run
```

Then browse to:

```text
http://localhost:9000/
```

## Hostname-Based Challenges

Some challenges may use virtual hosts. If the challenge hints at a hostname, add it to your local hosts file.

Example:

```bash
sudo sh -c 'printf "\n127.0.0.1 flightdeck.ai www.flightdeck.ai\n" >> /etc/hosts'
```

Then open:

```text
http://flightdeck.ai:8080/
```

If you changed the port, use that port instead.

## Play

Start with normal enumeration:

```bash
nmap -sV -sC -p 8080 localhost
curl -i http://localhost:8080/
```

If the challenge uses a hostname:

```bash
curl -i -H 'Host: flightdeck.ai' http://localhost:8080/
```

Some challenges may multiplex multiple protocols on the same exposed port. For example, HTTP and SSH may both be reachable on the same host port after you discover credentials:

```bash
ssh -p 8080 <user>@localhost
```

## Reset

There are two reset modes.

Soft reset: recreate the container from the existing image. This wipes runtime changes but keeps the same generated flags and credentials.

```bash
./scripts/flightdeck.sh softreset
```

Full reset: rebuild the image, regenerate secrets and flags, and restart the container.

```bash
./scripts/flightdeck.sh reset
```

## Stop

```bash
./scripts/flightdeck.sh stop
```

## Logs And Debugging

Tail challenge logs:

```bash
./scripts/flightdeck.sh logs
```

Open a root shell inside the running container:

```bash
./scripts/flightdeck.sh shell
```

Show container status:

```bash
./scripts/flightdeck.sh status
```

## Maintainer Notes

Some challenge repositories include an author-only answer key inside the running container. For FlightDeck, it can be printed with:

```bash
./scripts/flightdeck.sh answerkey
```

Do not expose answer keys or walkthrough files to players unless the event format allows it.

## Common Issues

If the web page is unreachable, confirm the container is running:

```bash
docker ps
```

If a hostname does not resolve, verify `/etc/hosts`:

```bash
dscacheutil -q host -a name flightdeck.ai
```

On macOS, flush DNS cache if needed:

```bash
sudo dscacheutil -flushcache
sudo killall -HUP mDNSResponder
```

If port `8080` is already in use, run on another port:

```bash
FLIGHTDECK_PORT=9000 ./scripts/flightdeck.sh run
```
