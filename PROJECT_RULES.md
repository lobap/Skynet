# Skynet Project Rules & Preferences

## General
- **Root Directory**: Keep it clean. Only `backend/`, `frontend/`, `docker/`, `scripts/`, and config files should exist here.
- **Scripts**: All utility scripts go in `scripts/`.

## Docker
- **Location**: All Docker config (`Dockerfile`, `compose`, `entrypoint`) lives in `docker/`.
- **Rebuild Protocol**:
  1. The `entrypoint.sh` automatically rebuilds frontend on startup.
  2. If changes do not appear, run `Remove-Item -Recurse -Force frontend/dist` on host.
  3. Restart container: `docker restart skynet_hive_mind`.

## UI/UX
- **Visuals**: High-end glassmorphism, responsive, "wow" factor.
- **Positronic Brain**: Crystalline Cube artifact, transparent/reactive.

## Agent Behavior
- **Terminal Output**: Stream real shell commands and LLM thoughts.
- **Efficiency**: No infinite loops. Force exit after `reply_to_user`.
