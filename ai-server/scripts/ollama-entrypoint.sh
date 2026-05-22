#!/bin/sh
# Ollama 컨테이너 entrypoint
# - 백그라운드로 ollama serve 띄우고
# - OLLAMA_MODEL 모델이 없으면 한 번 pull한 뒤
# - foreground로 ollama 프로세스를 유지한다.

set -e

MODEL="${OLLAMA_MODEL:-qwen3:1.7b}"

echo "[ollama-entrypoint] starting ollama serve in background"
ollama serve &
SERVE_PID=$!

# ollama serve 가 응답할 때까지 대기 (최대 60초)
echo "[ollama-entrypoint] waiting for ollama API to be ready"
for i in $(seq 1 30); do
  if ollama list >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

# 모델 존재 여부 확인 후 pull
if ollama list 2>/dev/null | awk 'NR>1 {print $1}' | grep -Fxq "$MODEL"; then
  echo "[ollama-entrypoint] model already present: $MODEL"
else
  echo "[ollama-entrypoint] pulling model: $MODEL"
  ollama pull "$MODEL" || {
    echo "[ollama-entrypoint] failed to pull $MODEL"
    kill "$SERVE_PID" 2>/dev/null || true
    exit 1
  }
fi

echo "[ollama-entrypoint] ready: $MODEL"
# 시그널/종료 처리를 위해 ollama serve를 foreground로 유지
wait "$SERVE_PID"
