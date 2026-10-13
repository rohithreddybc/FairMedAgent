#!/usr/bin/env bash
# Isolated-call arm for the primary hosted model: claude-haiku-4-5, one `claude -p` call per prompt
# (harness/scripts/claude_cli_answerer.py), reference condition only, sixteen vignettes, R=10.
# Resumable: a replicate counts as done when its trajectories.json exists; an unfinished one is
# re-initialised from scratch.
cd "$(dirname "$0")/.."
export FMA_VIGNETTE_SET=v2 FMA_ANSWERER=claude_cli_answerer.py
DIR=experiments/floor16_haiku_iso
for r in 01 02 03 04 05 06 07 08 09 10; do
  rd="$DIR/rep$r"
  [ -f "$rd/trajectories.json" ] && continue
  rm -rf "$rd"; mkdir -p "$rd"
  python harness/scripts/pilot_driver.py init "$rd/state.json" 0 >/dev/null
  FMA_SCRATCH="experiments/_scratch_haiku_iso" python harness/scripts/run_ollama_floor.py "$DIR" claude-haiku-4-5 "$((10#$r))" "$((10#$r))"
done
python harness/scripts/attempt_summary.py "$DIR"
echo "haiku iso done $(date -u +%FT%TZ)"
