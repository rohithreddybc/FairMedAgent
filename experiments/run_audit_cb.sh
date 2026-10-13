#!/usr/bin/env bash
# Counterbalanced end-to-end audit validation (rerun of run_audit_val.sh). Reference, null
# (rerender_control, character-identical descriptor) and one demographic contrast
# (black_woman_medicaid), 16 vignettes, five steps, R=12, default sampling, FMA_RETRY_POLICY=same.
# Within each replicate the three conditions run back to back in an order taken from
# experiments/audit_cb_schedule.json: each of the six orders is used twice, so every condition
# occupies every within-replicate position four times. The schedule is fixed before any call
# (seeded shuffle, harness/scripts/audit_cb_schedule.py). Every dispatched step is time-stamped in
# experiments/audit_cb_order_log.jsonl (FMA_ORDER_LOG). Resumable: a (condition, replicate) is
# done when its trajectories.json exists; an unfinished one is re-initialised.
# Output: experiments/audit_cb_<model>_<condition>/rep01..rep12
cd "$(dirname "$0")/.."
export FMA_VIGNETTE_SET=v2 FMA_RETRY_POLICY=same FMA_ORDER_LOG=experiments/audit_cb_order_log.jsonl
declare -A COND=( [reference]=ref_white_man_private [null]=rerender_control [demographic]=black_woman_medicaid )
MODELS="llama:llama3.1:8b-instruct-q4_K_M qwen3:qwen3:4b-instruct-2507-q8_0"
for pair in $MODELS; do
  name="${pair%%:*}"; model="${pair#*:}"
  for r in 01 02 03 04 05 06 07 08 09 10 11 12; do
    order=$(python -c "import json;print(' '.join(json.load(open('experiments/audit_cb_schedule.json'))['orders']['$((10#$r))']))")
    for arm in $order; do
      dir="experiments/audit_cb_${name}_${arm}"; rd="$dir/rep$r"
      [ -f "$rd/trajectories.json" ] && continue
      rm -rf "$rd"; mkdir -p "$rd"
      python harness/scripts/pilot_driver.py init "$rd/state.json" 1 >/dev/null
      FMA_CONDITION="${COND[$arm]}" FMA_SCRATCH="experiments/_scratch_audit_cb_${name}_${arm}" \
        python harness/scripts/run_ollama_floor.py "$dir" "$model" "$((10#$r))" "$((10#$r))"
    done
    echo "audit_cb $name rep$r ($order) done $(date -u +%FT%TZ)"
  done
  for arm in reference null demographic; do python harness/scripts/attempt_summary.py "experiments/audit_cb_${name}_${arm}"; done
  echo "audit_cb $name done $(date -u +%FT%TZ)"
done
echo "audit_cb all done $(date -u +%FT%TZ)"
