#!/usr/bin/env bash
# Resumable driver for the v3 reruns (attempt-level logging, retries at the same decoding
# configuration). A replicate counts as done when its trajectories.json exists; an unfinished
# replicate is re-initialised from scratch so no partial state is reused. Default-sampling arms
# (R=10) run first, then the temperature-0 arms (R=5), all under the same Ollama install.
cd "$(dirname "$0")/.."
export FMA_VIGNETTE_SET=v2 FMA_RETRY_POLICY=same
MODELS="llama:llama3.1:8b-instruct-q4_K_M mistral:mistral:7b-instruct qwen3:qwen3:4b-instruct-2507-q8_0 phi3:phi3:mini"

run_arm() {  # dir model nreps
  local dir="$1" model="$2" n="$3"
  for r in $(seq -w 1 "$n"); do
    r=$(printf "%02d" "$((10#$r))")
    local rd="$dir/rep$r"
    [ -f "$rd/trajectories.json" ] && continue
    rm -rf "$rd"; mkdir -p "$rd"
    python harness/scripts/pilot_driver.py init "$rd/state.json" 0 >/dev/null
    python harness/scripts/run_ollama_floor.py "$dir" "$model" "$((10#$r))" "$((10#$r))"
  done
  python harness/scripts/attempt_summary.py "$dir"
}

for pair in $MODELS; do
  name="${pair%%:*}"; model="${pair#*:}"
  FMA_SCRATCH="experiments/_scratch_v3_${name}" run_arm "experiments/floor16v3_${name}" "$model" 10
done
echo "v3 default all done $(date -u +%FT%TZ)"
for pair in $MODELS; do
  name="${pair%%:*}"; model="${pair#*:}"
  FMA_TEMPERATURE=0 FMA_SCRATCH="experiments/_scratch_v3_${name}_t0" run_arm "experiments/floor16v3_${name}_t0" "$model" 5
done
echo "v3 t0 all done $(date -u +%FT%TZ)"
