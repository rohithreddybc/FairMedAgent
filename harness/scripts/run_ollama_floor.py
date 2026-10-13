"""Drive the instability-floor replicates against a local Ollama model.

The loop is the pilot's: the harness emits one step's prompts, the answerer answers them, the
harness ingests and advances. Only the reference condition is dispatched, because the floor is
measured by re-running an identical condition and nothing else needs to be spent.

    python run_ollama_floor.py <dir> <model> [first_rep] [last_rep]
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
SCRATCH = os.environ.get("FMA_SCRATCH", os.path.join(HERE, "_scratch"))
REF = "ref_white_man_private"
# FMA_CONDITION selects the single condition id to dispatch (default: the reference, the original
# behaviour). Prompt templates and the dispatch instruction are the harness's, identical for every
# condition; only the condition's descriptor rendering differs. The rep state must have been
# initialised with controls ("init <state> 1") when a control condition is dispatched.
COND = os.environ.get("FMA_CONDITION", REF)
# FMA_ORDER_LOG, when set, is a JSON-lines file that receives one record per dispatched step
# (condition, replicate, step, UTC start and end), so order and elapsed time can be audited.
ORDER_LOG = os.environ.get("FMA_ORDER_LOG")


def _utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


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

            split = base.replace(".json", "__%s.json" % COND)
            if not os.path.exists(split):
                print("no split for %s at" % COND + " rep%02d step%d" % (rep, step))
                return 1

            ans = os.path.join(SCRATCH, "r%02d_s%d_ans.json" % (rep, step))
            print("rep%02d step%d" % (rep, step), flush=True)
            # FMA_ANSWERER selects the backend (default: the local Ollama answerer); the
            # hosted-endpoint check uses groq_answerer.py with the same loop.
            answerer = os.environ.get("FMA_ANSWERER", "ollama_answerer.py")
            t_start = _utc()
            _run([os.path.join(HERE, answerer), split, ans, model])
            if ORDER_LOG:
                with open(ORDER_LOG, "a", encoding="utf-8") as f:
                    f.write(json.dumps({"model": model, "condition": COND, "rep": rep, "step": step,
                                        "temperature": os.environ.get("FMA_TEMPERATURE"),
                                        "t_start": t_start, "t_end": _utc()}) + "\n")
            if os.path.exists(ans):
                os.makedirs(os.path.join(rep_dir, "answers"), exist_ok=True)
                shutil.copyfile(ans, os.path.join(rep_dir, "answers", "s%d.json" % step))

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
