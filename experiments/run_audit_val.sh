#!/usr/bin/env bash
# Clean end-to-end audit validation: reference, null (rerender_control, byte-identical descriptor) and
# one demographic contrast (black_woman_medicaid), 16 vignettes, five steps, R=10, default sampling,
# FMA_RETRY_POLICY=same, attempt logs. Conditions are interleaved within each replicate
# (reference, null, demographic) so time drift does not align with condition. Resumable: a
# (condition, replicate) is done when its trajectories.json exists; an unfinished one is
# re-initialised. State is initialised WITH controls (init ... 1) so rerender_control exists.
# Output: experiments/audit_val_<model>_<condition>/rep01..rep10
cd "$(dirname "$0")/.."
export FMA_VIGNETTE_SET=v2 FMA_RETRY_POLICY=same
declare -A COND=( [reference]=ref_white_man_private [null]=rerender_control [demographic]=black_woman_medicaid )
MODELS="llama:llama3.1:8b-instruct-q4_K_M qwen3:qwen3:4b-instruct-2507-q8_0"
for pair in $MODELS; do
  name="${pair%%:*}"; model="${pair#*:}"
  for r in 01 02 03 04 05 06 07 08 09 10; do
    for arm in reference null demographic; do
      dir="experiments/audit_val_${name}_${arm}"; rd="$dir/rep$r"
      [ -f "$rd/trajectories.json" ] && continue
      rm -rf "$rd"; mkdir -p "$rd"
      python harness/scripts/pilot_driver.py init "$rd/state.json" 1 >/dev/null
      FMA_CONDITION="${COND[$arm]}" FMA_SCRATCH="experiments/_scratch_audit_${name}_${arm}" \
        python harness/scripts/run_ollama_floor.py "$dir" "$model" "$((10#$r))" "$((10#$r))"
    done
  done
  for arm in reference null demographic; do python harness/scripts/attempt_summary.py "experiments/audit_val_${name}_${arm}"; done
  echo "audit_val $name done $(date -u +%FT%TZ)"
done
echo "audit_val all done $(date -u +%FT%TZ)"
