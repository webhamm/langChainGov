#!/usr/bin/env bash
# Stop the LiteLLM proxy that up.sh started. Ollama and its models are left alone.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

if ! proxy_running; then
  rm -f "$PID_FILE"
  log "LiteLLM is not running; nothing to stop"
  exit 0
fi

pid="$(cat "$PID_FILE")"
log "stopping LiteLLM (pid $pid)"
# uvx runs litellm as a child process, so stop the children as well as uvx itself.
pkill -TERM -P "$pid" 2>/dev/null || true
kill -TERM "$pid" 2>/dev/null || true
for _ in $(seq 1 15); do
  kill -0 "$pid" 2>/dev/null || break
  sleep 1
done
if kill -0 "$pid" 2>/dev/null; then
  warn "still running after 15 s; sending SIGKILL"
  pkill -KILL -P "$pid" 2>/dev/null || true
  kill -KILL "$pid" 2>/dev/null || true
fi
rm -f "$PID_FILE"

holder="$(port_holder)"
[[ -z "$holder" ]] || warn ":$LLM_PORT is still held by pid $holder"
log "stopped. Ollama keeps running; to free the model's memory now: ollama stop $OLLAMA_TAG"
