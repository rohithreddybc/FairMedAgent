"""Summarise attempt-level logs written by ollama_answerer.py.

    python attempt_summary.py <run_dir>...

A run dir holds rep*/answers/s*.json. Per run dir this prints total prompts, first-attempt
failures, retries, final failures and the temperature values seen, and writes
attempt_summary.json next to the reps.
"""
from __future__ import annotations

import glob
import json
import os
import sys


def summarise(run_dir: str) -> dict:
    total = first_fail = retries = final_fail = 0
    temps, policies, files = set(), set(), 0
    for path in sorted(glob.glob(os.path.join(run_dir, "rep*", "answers", "s*.json"))):
        d = json.load(open(path, encoding="utf-8"))
        files += 1
        policies.add((d.get("provenance") or {}).get("retry_policy", "unlogged"))
        for rec in d.get("attempts", []):
            total += 1
            att = rec["attempts"]
            first_fail += not att[0]["parsed"]
            retries += len(att) > 1
            final_fail += not att[-1]["parsed"]
            temps.update(a["temperature"] for a in att)
    return {"run_dir": run_dir, "answer_files": files, "prompts": total,
            "first_attempt_failures": first_fail, "retries": retries,
            "final_failures": final_fail,
            "temperatures_seen": sorted(temps, key=lambda t: (t is not None, t or 0)),
            "retry_policies": sorted(policies)}


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 2
    for run_dir in argv[1:]:
        s = summarise(run_dir)
        json.dump(s, open(os.path.join(run_dir, "attempt_summary.json"), "w",
                          encoding="utf-8"), indent=1)
        print("%s: %d prompts, %d first-attempt failures, %d retries, %d final failures, "
              "temperatures %s, policy %s"
              % (run_dir, s["prompts"], s["first_attempt_failures"], s["retries"],
                 s["final_failures"], s["temperatures_seen"], s["retry_policies"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
