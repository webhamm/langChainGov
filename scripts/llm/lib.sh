# Shared settings and helpers for the local model stack scripts. Sourced, not run.
#
# Every default can be overridden from the environment, e.g. `LLM_PORT=4001 make llm-up`
# (then point LANGCHAINGOV_BASE_URL at the same port). tests/test_llm_stack.py checks
# that these defaults agree with infra/ollama/*.Modelfile and infra/litellm/config.yaml.

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

# Ollama: the base model, the tag built from our Modelfile, and where Ollama listens.
OLLAMA_URL="${OLLAMA_URL:-http://localhost:11434}"
OLLAMA_BASE_MODEL="${OLLAMA_BASE_MODEL:-llama3.2:3b}"
OLLAMA_TAG="${OLLAMA_TAG:-langchaingov-llama3.2-3b:32k}"
OLLAMA_MODELFILE="${OLLAMA_MODELFILE:-$REPO_ROOT/infra/ollama/llama3.2-3b-32k.Modelfile}"
export OLLAMA_HOST="${OLLAMA_HOST:-$OLLAMA_URL}"  # so the ollama CLI talks to the same server

# LiteLLM: the model name it exposes, its port, pinned version, config, and the .env it reads.
LLM_MODEL_NAME="${LLM_MODEL_NAME:-llama3.2-3b-32k}"
LLM_PORT="${LLM_PORT:-4000}"
LITELLM_VERSION="${LITELLM_VERSION:-1.110.1}"
LITELLM_CONFIG="${LITELLM_CONFIG:-$REPO_ROOT/infra/litellm/config.yaml}"
ENV_FILE="${ENV_FILE:-$REPO_ROOT/.env}"

# The proxy runs in the background; its pid and log live here (git-ignored).
# Named by port, so a proxy on another LLM_PORT is never mistaken for this one.
RUN_DIR="$REPO_ROOT/.run"
PID_FILE="$RUN_DIR/litellm-$LLM_PORT.pid"
LOG_FILE="$RUN_DIR/litellm-$LLM_PORT.log"

log() { printf '==> %s\n' "$*"; }
warn() { printf 'warn: %s\n' "$*" >&2; }
die() {
  printf 'error: %s\n' "$*" >&2
  exit 1
}

ollama_up() { curl -fsS -m 3 "$OLLAMA_URL/api/version" >/dev/null 2>&1; }

# True when `ollama list` has exactly this NAME (first column).
has_model() { ollama list 2>/dev/null | awk 'NR > 1 { print $1 }' | grep -qxF "$1"; }

# True when the proxy we started is still alive.
proxy_running() { [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; }

# PID of whatever listens on the proxy port, empty when the port is free.
port_holder() { lsof -nP -iTCP:"$LLM_PORT" -sTCP:LISTEN -t 2>/dev/null | head -n 1 || true; }

# LiteLLM's unauthenticated liveness probe.
litellm_live() { curl -fsS -m 2 "http://localhost:$LLM_PORT/health/liveliness" >/dev/null 2>&1; }
