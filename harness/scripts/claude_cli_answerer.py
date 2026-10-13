"""Answer one step's prompts with a Claude model, one isolated CLI call per prompt.

Same interface as ollama_answerer.py:  python claude_cli_answerer.py <prompts.json> <out.json> [model]

Each prompt is sent in its own `claude -p` invocation (no tools, no session persistence), so no
answer shares a context with any other vignette, condition or replicate -- the isolated-call
counterpart of the batched sub-agent dispatch used for endpoints A and B. Every attempt is
logged with its start time, duration, session id and the model the CLI reports. Decoding
parameters are not exposed by the CLI and are recorded as unavailable. Retry policy: one retry
with the identical request on a parse failure (FMA_RETRY_POLICY=same semantics).
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from datetime import datetime, timezone

DEFAULT_MODEL = "claude-haiku-4-5"
TIMEOUT_S = 180


def _call(model: str, system: str, user: str, schema: dict) -> tuple[dict | None, dict]:
    cmd = ["claude", "-p", "--model", model, "--output-format", "json",
           "--no-session-persistence", "--disable-slash-commands", "--tools", "",
           "--system-prompt", system, "--json-schema", json.dumps(schema), user]
    meta = {"t_start": datetime.now(timezone.utc).isoformat()}
    t0 = time.time()
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", timeout=TIMEOUT_S)
        out = json.loads(res.stdout or "{}")
    except Exception as exc:  # timeout or unparseable CLI output
        meta.update(duration_s=time.time() - t0, error=str(exc)[:200])
        return None, meta
    meta.update(duration_s=time.time() - t0, session_id=out.get("session_id"),
                models_reported=sorted((out.get("modelUsage") or {}).keys()),
                is_error=out.get("is_error"), error=None if not out.get("is_error") else str(out.get("result"))[:200])
    if out.get("is_error"):
        return None, meta
    action = out.get("structured_output")
    if action is None:
        txt = out.get("result") or ""
        s, e = txt.find("{"), txt.rfind("}")
        try:
            action = json.loads(txt[s:e + 1]) if s != -1 and e > s else None
        except json.JSONDecodeError:
            action = None
    return action, meta


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print(__doc__)
        return 2
    prompts_path, out_path = argv[1], argv[2]
    model = argv[3] if len(argv) > 3 else DEFAULT_MODEL
    spec = json.load(open(prompts_path, encoding="utf-8"))
    schema, step = spec["schema"], spec.get("step", "?")
    instr = spec.get("dispatch_instruction", "")
    system = instr % (step, json.dumps(schema)) if "%s" in instr else (instr or "Reply with JSON only.")
    answers, failed, retried, attempts = [], [], [], {}
    for p in spec["prompts"]:
        log = []
        action, meta = _call(model, system, p["prompt"], schema)
        log.append(dict(meta, n=1, parsed=action is not None))
        first = action
        if action is None:
            retried.append(p["id"])
            action, meta = _call(model, system, p["prompt"], schema)
            log.append(dict(meta, n=2, parsed=action is not None))
        attempts[p["id"]] = {"attempts": log, "first_action": first}
        if action is None:
            failed.append(p["id"])
            continue
        answers.append({"id": p["id"], "action": action})
    json.dump({"answers": answers, "attempts": attempts, "provenance": {
        "model": model, "dispatch": "isolated claude -p call per prompt", "decoding": "not exposed by the CLI",
        "retry_policy": "same", "retried_ids": retried, "failed_ids": failed}},
        open(out_path, "w", encoding="utf-8"), indent=1)
    print("  step %s: %d answered, %d unanswered" % (step, len(answers), len(failed)))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
