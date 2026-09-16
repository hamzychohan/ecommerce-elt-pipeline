#!/usr/bin/env bash
# Ensure Docker is available before running docker compose.
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info() { printf "${GREEN}==>${NC} %s\n" "$*"; }
warn() { printf "${YELLOW}warning:${NC} %s\n" "$*"; }
fail() { printf "${RED}error:${NC} %s\n" "$*" >&2; exit 1; }

if docker info >/dev/null 2>&1; then
  info "Docker daemon is running."
  docker compose version
  exit 0
fi

warn "Docker daemon is not reachable."

if ! command -v colima >/dev/null 2>&1; then
  fail "Colima is not installed. Install Docker Desktop or run: brew install colima docker"
fi

info "Attempting to start Colima..."

if colima status 2>&1 | grep -q "colima is running"; then
  info "Colima is running but Docker socket is missing. Resetting context..."
  docker context use colima >/dev/null 2>&1 || true
  if docker info >/dev/null 2>&1; then
    info "Docker is now available via Colima."
    exit 0
  fi
fi

CPU_BRAND="$(sysctl -n machdep.cpu.brand_string 2>/dev/null || echo unknown)"
START_ARGS=(start --cpu 2 --memory 4 --disk 20)

if echo "$CPU_BRAND" | grep -qi intel; then
  warn "Intel Mac detected. Using QEMU VM type (VZ requires macOS 15.5+)."
  if ! command -v qemu-img >/dev/null 2>&1; then
    fail "qemu-img not found. Run: brew install qemu"
  fi
  START_ARGS+=(--vm-type qemu)
fi

colima "${START_ARGS[@]}"
docker context use colima >/dev/null 2>&1 || true

if docker info >/dev/null 2>&1; then
  info "Docker is ready."
  docker compose version
else
  fail "Colima started but Docker is still unavailable. Try: colima delete && ./scripts/setup-docker.sh"
fi
