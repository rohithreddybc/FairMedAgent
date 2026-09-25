"""Answer one emitted step of the instability study with a local Ollama model.

The harness keeps control: it emits the prompts and the schema each answer must satisfy, this
script answers them, and the harness validates and advances its own state. Nothing here
decides what the next prompt says, which is the property pilot_driver.py exists to preserve.

The point of this answerer is a third vendor. The floor reported for this benchmark was
measured on two models from one vendor family, so cross-model agreement could not distinguish
a property of the task from a property of that family. A locally hosted open-weight model from
a different lineage is the cheapest available test of that distinction, and it costs nothing to
run.

    python ollama_answerer.py <prompts.json> <answers.json> [model]

Ollama's native /api/chat is used rather than the OpenAI-compatible route, and the step schema
is passed through as a structured-output constraint so malformed answers are rare. Answers that
still fail to parse are retried once at a lower temperature and then reported, never invented:
a missing cell is visible to the harness, a fabricated one is not.
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request

URL = os.environ.get("FF_OLLAMA_URL", "http://127.0.0.1:11434") + "/api/chat"
DEFAULT_MODEL = "gpt-oss:20b"
TIMEOUT_S = 300


def _call(model: str, system: str, user: str, schema: dict,
          temperature: float | None) -> dict | None:
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "stream": False,
        "format": schema,
        "options": ({"num_ctx": 8192} if temperature is None
                    else {"temperature": temperature, "num_ctx": 8192}),
    }
    req = urllib.request.Request(
        URL, data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        print("    transport failure: %s" % exc, file=sys.stderr)
        return None

    content = ((payload.get("message") or {}).get("content") or "").strip()
    if not content:
        return None
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        start, end = content.find("{"), content.rfind("}")
        if start != -1 and end > start:
            try:
                return json.loads(content[start:end + 1])
            except json.JSONDecodeError:
                return None
        return None


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print(__doc__)
        return 2
    prompts_path, out_path = argv[1], argv[2]
    model = argv[3] if len(argv) > 3 else DEFAULT_MODEL

    spec = json.load(open(prompts_path, encoding="utf-8"))
    schema = spec["schema"]
    step = spec.get("step", "?")
    system = spec["dispatch_instruction"] % (step, json.dumps(schema)) \
        if "%s" in spec.get("dispatch_instruction", "") else spec.get("dispatch_instruction", "")
    prompts = spec["prompts"]

    answers, failed = [], []
    t0 = time.time()
    for i, p in enumerate(prompts, 1):
        action = _call(model, system, p["prompt"], schema, None)
        if action is None:
            action = _call(model, system, p["prompt"], schema, 0.2)
        if action is None:
            failed.append(p["id"])
            continue
        answers.append({"id": p["id"], "action": action})
        if i % 4 == 0 or i == len(prompts):
            print("    %d/%d  (%.0fs)" % (i, len(prompts), time.time() - t0), flush=True)

    json.dump({"answers": answers}, open(out_path, "w", encoding="utf-8"), indent=1)
    print("  step %s: %d answered, %d unanswered %s"
          % (step, len(answers), len(failed), failed if failed else ""))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
