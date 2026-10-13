#!/usr/bin/env bash
# Interleaved dispatch comparison for claude-haiku-4-5, reference condition, sixteen vignettes, R=10.
# For each replicate r, one ISOLATED replicate (one `claude -p` call per prompt,
# claude_cli_answerer.py) and one BATCHED replicate (one call per step carrying all sixteen prompts,
# claude_cli_batched_answerer.py) are run back to back; the arm that goes first alternates (iso first
# on odd r, batched first on even r) so time drift does not align with arm. Resumable: a replicate
# is done when its trajectories.json exists; an unfinished one is re-initialised from scratch.
cd "$(dirname "$0")/.."
export FMA_VIGNETTE_SET=v2
ISO=experiments/floor16_haiku_il_iso; BATCH=experiments/floor16_haiku_il_batch
run_one() {  # arm dir answerer
  local arm="$1" dir="$2" ans="$3" r="$4"
  local rd="$dir/rep$r"
  [ -f "$rd/trajectories.json" ] && return
  rm -rf "$rd"; mkdir -p "$rd"
  python harness/scripts/pilot_driver.py init "$rd/state.json" 0 >/dev/null
  FMA_ANSWERER="$ans" FMA_SCRATCH="experiments/_scratch_haiku_il_$arm" \
    python harness/scripts/run_ollama_floor.py "$dir" claude-haiku-4-5 "$((10#$r))" "$((10#$r))"
}
for r in 01 02 03 04 05 06 07 08 09 10; do
  if [ $((10#$r % 2)) -eq 1 ]; then
    run_one iso "$ISO" claude_cli_answerer.py $r; run_one batch "$BATCH" claude_cli_batched_answerer.py $r
  else
    run_one batch "$BATCH" claude_cli_batched_answerer.py $r; run_one iso "$ISO" claude_cli_answerer.py $r
  fi
  echo "interleaved rep$r done $(date -u +%FT%TZ)"
done
python harness/scripts/attempt_summary.py "$ISO"
echo "haiku interleaved done $(date -u +%FT%TZ)"
