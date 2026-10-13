#!/usr/bin/env bash
# Interleaved temperature check for the four local models (rerun of the block-ordered comparison in
# run_v3_all.sh, where every default-sampling arm ran before every temperature-0 arm). Reference
# condition, sixteen vignettes, five steps, FMA_RETRY_POLICY=same. For each model, replicate r runs
# one default-sampling replicate and one temperature-0 replicate back to back; default goes first on
# odd r and temperature 0 on even r (R=6 per arm, so each arm is first three times). Models run one
# after another. Every dispatched step is time-stamped in experiments/temp_il_order_log.jsonl.
# Resumable: a replicate is done when its trajectories.json exists; an unfinished one is
# re-initialised. Output: experiments/temp_il_<model>_{default,t0}/rep01..rep06
cd "$(dirname "$0")/.."
export FMA_VIGNETTE_SET=v2 FMA_RETRY_POLICY=same FMA_ORDER_LOG=experiments/temp_il_order_log.jsonl
MODELS="llama:llama3.1:8b-instruct-q4_K_M mistral:mistral:7b-instruct qwen3:qwen3:4b-instruct-2507-q8_0 phi3:phi3:mini"
run_one() {  # name model arm r
  local name="$1" model="$2" arm="$3" r="$4"
  local dir="experiments/temp_il_${name}_${arm}"; local rd="$dir/rep$r"
  [ -f "$rd/trajectories.json" ] && return
  rm -rf "$rd"; mkdir -p "$rd"
  python harness/scripts/pilot_driver.py init "$rd/state.json" 0 >/dev/null
  if [ "$arm" = t0 ]; then
    FMA_TEMPERATURE=0 FMA_SCRATCH="experiments/_scratch_temp_il_${name}_t0" \
      python harness/scripts/run_ollama_floor.py "$dir" "$model" "$((10#$r))" "$((10#$r))"
  else
    env -u FMA_TEMPERATURE FMA_SCRATCH="experiments/_scratch_temp_il_${name}_default" \
      python harness/scripts/run_ollama_floor.py "$dir" "$model" "$((10#$r))" "$((10#$r))"
  fi
}
for pair in $MODELS; do
  name="${pair%%:*}"; model="${pair#*:}"
  for r in 01 02 03 04 05 06; do
    if [ $((10#$r % 2)) -eq 1 ]; then
      run_one "$name" "$model" default $r; run_one "$name" "$model" t0 $r
    else
      run_one "$name" "$model" t0 $r; run_one "$name" "$model" default $r
    fi
    echo "temp_il $name rep$r done $(date -u +%FT%TZ)"
  done
  for arm in default t0; do python harness/scripts/attempt_summary.py "experiments/temp_il_${name}_${arm}"; done
done
echo "temp_il all done $(date -u +%FT%TZ)"
