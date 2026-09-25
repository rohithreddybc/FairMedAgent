"""Drive the instability-floor replicates against a local Ollama model.

The loop is the pilot's: the harness emits one step's prompts, the answerer answers them, the
harness ingests and advances. Only the reference condition is dispatched, because the floor is
measured by re-running an identical condition and nothing else needs to be spent.

    python run_ollama_floor.py <dir> <model> [first_rep] [last_rep]
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
SCRATCH = os.environ.get("FMA_SCRATCH", os.path.join(HERE, "_scratch"))
REF = "ref_white_man_private"


def _run(args: list[str]) -> int:
    env = dict(os.environ, FMA_VIGNETTE_SET="v2")
    return subprocess.call([sys.executable] + args, env=env)


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print(__doc__)
        return 2
    root, model = argv[1], argv[2]
    first = int(argv[3]) if len(argv) > 3 else 1
    last = int(argv[4]) if len(argv) > 4 else 6

    os.makedirs(SCRATCH, exist_ok=True)
    t0 = time.time()

    for rep in range(first, last + 1):
        rep_dir = os.path.join(root, "rep%02d" % rep)
        state = os.path.join(rep_dir, "state.json")
        if not os.path.exists(state):
            print("no state for rep%02d, skipping" % rep)
            continue

        for step in range(1, 6):
            base = os.path.join(SCRATCH, "r%02d_s%d.json" % (rep, step))
            if _run([os.path.join(HERE, "pilot_driver.py"), "emit", state, base]) != 0:
                print("emit failed at rep%02d step%d" % (rep, step))
                return 1

            split = base.replace(".json", "__%s.json" % REF)
            if not os.path.exists(split):
                print("no reference split at rep%02d step%d" % (rep, step))
                return 1

            ans = os.path.join(SCRATCH, "r%02d_s%d_ans.json" % (rep, step))
            print("rep%02d step%d" % (rep, step), flush=True)
            _run([os.path.join(HERE, "ollama_answerer.py"), split, ans, model])

            if _run([os.path.join(HERE, "pilot_driver.py"), "ingest", state, ans]) != 0:
                print("ingest failed at rep%02d step%d" % (rep, step))
                return 1

        out = os.path.join(rep_dir, "trajectories.json")
        _run([os.path.join(HERE, "pilot_driver.py"), "finish", state, out])
        print("rep%02d done (%.0f min elapsed)" % (rep, (time.time() - t0) / 60), flush=True)

    print("all replicates finished in %.0f min" % ((time.time() - t0) / 60))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
