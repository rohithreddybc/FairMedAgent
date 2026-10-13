"""Answer one step's prompts with a Claude model, ALL prompts of the step in ONE CLI call.

Same interface as claude_cli_answerer.py:  python claude_cli_batched_answerer.py <prompts.json> <out.json> [model]

The step's dispatch instruction is the system prompt; the user message lists every prompt with its
id; --json-schema constrains the reply to {"answers":[{"id": int, "action": <step schema>}]}.
Flags otherwise match the isolated answerer (no tools, no session persistence, slash commands
disabled). Every attempt is logged (t_start, duration, session id, models reported). One retry with
the IDENTICAL request on a parse failure or when any id is missing; ids still missing afterwards
are recorded as unanswered (never invented).
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from datetime import datetime, timezone

DEFAULT_MODEL = "claude-haiku-4-5"
TIMEOUT_S = 600


def _batch_schema(action_schema: dict) -> dict:
    return {"type": "object", "properties": {"answers": {"type": "array", "items": {
        "type": "object", "properties": {"id": {"type": "integer"}, "action": action_schema},
        "required": ["id", "action"]}}}, "required": ["answers"]}


def _user_message(prompts: list[dict]) -> str:
    parts = []
    for p in prompts:
        parts.append("=== PROMPT id=%s ===\n%s" % (p["id"], p["prompt"]))
    return "\n\n".join(parts)


def _call(model: str, system: str, user: str, schema: dict) -> tuple[dict | None, dict]:
    cmd = ["claude", "-p", "--model", model, "--output-format", "json",
           "--no-session-persistence", "--disable-slash-commands", "--tools", "",
           "--system-prompt", system, "--json-schema", json.dumps(schema), user]
    meta = {"t_start": datetime.now(timezone.utc).isoformat()}
    t0 = time.time()
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", timeout=TIMEOUT_S)
        out = json.loads(res.stdout or "{}")
    except Exception as exc:
        meta.update(duration_s=time.time() - t0, error=str(exc)[:200])
        return None, meta
    meta.update(duration_s=time.time() - t0, session_id=out.get("session_id"),
                models_reported=sorted((out.get("modelUsage") or {}).keys()),
                is_error=out.get("is_error"), error=None if not out.get("is_error") else str(out.get("result"))[:200])
    if out.get("is_error"):
        return None, meta
    obj = out.get("structured_output")
    if obj is None:
        txt = out.get("result") or ""
        s, e = txt.find("{"), txt.rfind("}")
        try:
            obj = json.loads(txt[s:e + 1]) if s != -1 and e > s else None
        except json.JSONDecodeError:
            obj = None
    return obj, meta


def _extract(obj, wanted: set) -> dict:
    got = {}
    if isinstance(obj, dict) and isinstance(obj.get("answers"), list):
        for a in obj["answers"]:
            try:
                i = int(a["id"])
            except (KeyError, TypeError, ValueError):
                continue
            if i in wanted and isinstance(a.get("action"), dict) and i not in got:
                got[i] = a["action"]
    return got


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
    prompts = spec["prompts"]
    wanted = {int(p["id"]) for p in prompts}
    bschema = _batch_schema(schema)
    user = _user_message(prompts)

    log, got = [], {}
    obj, meta = _call(model, system, user, bschema)
    got = _extract(obj, wanted)
    log.append(dict(meta, n=1, parsed=obj is not None, n_answered=len(got)))
    first_ids = sorted(got)
    if obj is None or len(got) < len(wanted):
        obj2, meta2 = _call(model, system, user, bschema)
        got2 = _extract(obj2, wanted)
        log.append(dict(meta2, n=2, parsed=obj2 is not None, n_answered=len(got2)))
        if len(got2) > len(got):
            got = got2
    missing = sorted(wanted - set(got))
    answers = [{"id": i, "action": got[i]} for i in sorted(got)]
    json.dump({"answers": answers, "attempts": {"batch": {"attempts": log, "first_answered_ids": first_ids}},
               "provenance": {"model": model, "dispatch": "ONE claude -p call for all prompts of the step",
                              "decoding": "not exposed by the CLI", "retry_policy": "same (identical request, once)",
                              "n_prompts": len(wanted), "failed_ids": missing}},
              open(out_path, "w", encoding="utf-8"), indent=1)
    print("  step %s: %d answered, %d unanswered %s" % (step, len(answers), len(missing), missing if missing else ""))
    return 0 if not missing else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
