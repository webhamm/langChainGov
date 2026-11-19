#!/usr/bin/env bash
# End-to-end check of the local model stack through the real langchaingov CLI.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
cd "$REPO_ROOT"

litellm_live || die "LiteLLM is not answering on :$LLM_PORT. Run: make llm-up"
export LANGCHAINGOV_BASE_URL="http://localhost:$LLM_PORT/v1"

log "1/3 the proxy lists $LLM_MODEL_NAME"
uv run --quiet langchaingov models | grep -qxF "$LLM_MODEL_NAME" ||
  die "$LLM_MODEL_NAME is not in 'langchaingov models'. Is another proxy on :$LLM_PORT?"

log "2/3 a chat round trip"
reply="$(uv run --quiet langchaingov chat --model "$LLM_MODEL_NAME" "Reply with exactly one word: ready")"
[[ -n "${reply//[[:space:]]/}" ]] || die "the model returned an empty reply"
log "    reply: $reply"

# Ollama's /api/ps reports the window each loaded model is actually served with.
log "3/3 the served context window"
expected="$(awk '$1 == "PARAMETER" && $2 == "num_ctx" { print $3 }' "$OLLAMA_MODELFILE")"
served="$(curl -fsS -m 3 "$OLLAMA_URL/api/ps" |
  jq -r --arg tag "$OLLAMA_TAG" '.models[] | select(.name == $tag) | .context_length // empty')"
[[ -n "$served" ]] || die "$OLLAMA_TAG is not loaded in Ollama, or Ollama did not report its context"
[[ "$served" == "$expected" ]] || die "served context is $served, but the Modelfile asks for $expected"
log "    $OLLAMA_TAG is served with context $served"

log "smoke test passed"
