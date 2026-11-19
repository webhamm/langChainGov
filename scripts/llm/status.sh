#!/usr/bin/env bash
# Report on each piece of the local model stack. Exits 1 if anything is down or missing.
set -uo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

problems=0
ok() { printf '  ok    %s\n' "$*"; }
bad() {
  printf '  FAIL  %s\n' "$*"
  problems=$((problems + 1))
}

echo "Ollama"
if ollama_up; then
  ok "reachable at $OLLAMA_URL (version $(ollama --version | awk '{ print $NF }'))"
  for name in "$OLLAMA_BASE_MODEL" "$OLLAMA_TAG"; do
    if has_model "$name"; then ok "model $name present"; else bad "model $name missing (run: make llm-up)"; fi
  done
  echo "  loaded models (CONTEXT is the window actually served):"
  ollama ps | sed 's/^/    /'
else
  bad "not reachable at $OLLAMA_URL (run: brew services start ollama)"
fi

echo "LiteLLM"
if proxy_running; then ok "running, pid $(cat "$PID_FILE")"; else bad "not running (run: make llm-up)"; fi
if litellm_live; then
  ok "answering on :$LLM_PORT"
else
  holder="$(port_holder)"
  if [[ -n "$holder" ]]; then
    bad ":$LLM_PORT is held by pid $holder but /health/liveliness does not answer"
  else
    bad "nothing answering on :$LLM_PORT"
  fi
fi

exit $((problems > 0))
