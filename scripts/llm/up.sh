#!/usr/bin/env bash
# Stand up the local model stack: an Ollama model with a 32k window, behind a
# repo-owned LiteLLM proxy. Safe to re-run: every step checks before it acts.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

command -v ollama >/dev/null || die "ollama not found. Install it with: brew install ollama"
command -v uvx >/dev/null || die "uvx not found. Install uv with: brew install uv"

# 1. Ollama must already be serving (Homebrew runs it as a service).
ollama_up || die "Ollama is not answering at $OLLAMA_URL. Start it with: brew services start ollama"
log "Ollama $(ollama --version | awk '{ print $NF }') is up at $OLLAMA_URL"

# 2. Pull the base model once (about 2 GB).
if has_model "$OLLAMA_BASE_MODEL"; then
  log "base model $OLLAMA_BASE_MODEL is present"
else
  log "pulling $OLLAMA_BASE_MODEL"
  ollama pull "$OLLAMA_BASE_MODEL"
fi

# 3. Build our tag from the Modelfile. Re-creating is cheap (the weights are shared
#    with the base model) and picks up any Modelfile change, such as a new num_ctx.
log "building $OLLAMA_TAG from ${OLLAMA_MODELFILE#"$REPO_ROOT"/}"
if ! create_output="$(ollama create "$OLLAMA_TAG" -f "$OLLAMA_MODELFILE" 2>&1)"; then
  printf '%s\n' "$create_output" >&2
  die "ollama create failed (output above)"
fi

# 4. The proxy reads its master key from .env. Check the name only; never print values.
[[ -f "$ENV_FILE" ]] || die "$ENV_FILE not found. Copy .env.example to .env and set LITELLM_MASTER_KEY."
grep -q '^LITELLM_MASTER_KEY=.' "$ENV_FILE" || die "LITELLM_MASTER_KEY is not set in $ENV_FILE."

# 5. Start LiteLLM in the background unless ours is already running.
if proxy_running; then
  log "LiteLLM is already running (pid $(cat "$PID_FILE")) on :$LLM_PORT"
else
  holder="$(port_holder)"
  if [[ -n "$holder" ]]; then
    holder_cmd="$(ps -o comm= -p "$holder")"
    die ":$LLM_PORT is held by pid $holder (${holder_cmd##*/}). Stop it, or set LLM_PORT and LANGCHAINGOV_BASE_URL to another port."
  fi
  mkdir -p "$RUN_DIR"
  log "starting LiteLLM $LITELLM_VERSION on :$LLM_PORT (log: ${LOG_FILE#"$REPO_ROOT"/})"
  nohup uvx --env-file "$ENV_FILE" --from "litellm[proxy]==$LITELLM_VERSION" \
    litellm --config "$LITELLM_CONFIG" --port "$LLM_PORT" >"$LOG_FILE" 2>&1 &
  echo $! >"$PID_FILE"
fi

# 6. Wait until it answers. The first start can take a while if uvx has to install.
for _ in $(seq 1 120); do
  litellm_live && break
  if ! proxy_running; then
    tail -n 20 "$LOG_FILE" >&2 || true
    rm -f "$PID_FILE"
    die "LiteLLM exited during startup (log above)."
  fi
  sleep 1
done
litellm_live || die "LiteLLM did not answer within 120 s. See $LOG_FILE"

log "stack is up: model $LLM_MODEL_NAME at http://localhost:$LLM_PORT/v1"
if ! grep -q "^LANGCHAINGOV_MODEL=$LLM_MODEL_NAME\$" "$ENV_FILE"; then
  warn "set LANGCHAINGOV_MODEL=$LLM_MODEL_NAME in .env to make it the default model"
fi
log "next: make llm-smoke"
