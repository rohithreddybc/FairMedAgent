"""Answer one emitted step of the instability study with a model hosted on Groq.

Same contract as ollama_answerer.py: the harness emits the prompts and the step schema, this
script answers them, and the harness validates and advances its own state. It exists to test
whether the temperature-0 result on locally served models also holds on a hosted endpoint,
where batching and serving kernels are outside the auditor's control.

    FMA_TEMPERATURE=<t> python groq_answerer.py <prompts.json> <answers.json> [model]

The temperature must be given explicitly (FMA_TEMPERATURE); first calls and retries use the
same value, so a run never mixes decoding configurations. The step schema is passed as a
structured-output constraint, as the Ollama answerer does. The API key is read from
GROQ_API_KEY and is never written anywhere. Every answer file records the decoding settings
used, the system fingerprints the API reported, and any retried or failed calls.
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request

URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_MODEL = "openai/gpt-oss-20b"
REASONING_EFFORT = os.environ.get("FMA_REASONING_EFFORT", "low")
TIMEOUT_S = 120


def _call(model: str, system: str, user: str, schema: dict, temperature: float, fps: set):
    body = {
        "model": model,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "temperature": temperature,
        "max_tokens": 1500,
        "response_format": {"type": "json_schema", "json_schema": {"name": "step", "schema": schema}},
    }
    if model.startswith("openai/gpt-oss"):
        body["reasoning_effort"] = REASONING_EFFORT
    headers = {"Authorization": "Bearer " + os.environ["GROQ_API_KEY"],
               "Content-Type": "application/json", "User-Agent": "FairMedAgent-harness/0.1.4"}
    # Rate limits are waited out rather than turned into missing cells: a 429 honors the
    # provider's retry-after (the free tier's daily cap can mean hours), up to MAX_WAIT_S in
    # total per call, so an unattended run pauses instead of recording failures.
    waited = 0.0
    MAX_WAIT_S = float(os.environ.get("FMA_MAX_WAIT_S", 14 * 3600))
    for attempt in range(10000):
        req = urllib.request.Request(URL, data=json.dumps(body).encode("utf-8"), headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            break
        except urllib.error.HTTPError as exc:
            if exc.code == 429 or exc.code >= 500:
                wait = float(exc.headers.get("retry-after") or 0) or min(60, 5 * (attempt + 1))
                wait = min(max(wait, 1.0), 3600.0)
                if waited + wait > MAX_WAIT_S:
                    print("    giving up after %.0fs of rate-limit waits" % waited, file=sys.stderr)
                    return None
                if wait >= 60:
                    print("    rate limited; waiting %.0fs" % wait, file=sys.stderr, flush=True)
                time.sleep(wait)
                waited += wait
                continue
            print("    HTTP %d: %s" % (exc.code, exc.read()[:200]), file=sys.stderr)
            return None
        except (urllib.error.URLError, TimeoutError) as exc:
            print("    transport failure: %s" % exc, file=sys.stderr)
            time.sleep(5)
    else:
        return None
    if payload.get("system_fingerprint"):
        fps.add(payload["system_fingerprint"])
    content = (((payload.get("choices") or [{}])[0].get("message") or {}).get("content") or "").strip()
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
    if os.environ.get("FMA_TEMPERATURE") is None:
        print("FMA_TEMPERATURE must be set explicitly", file=sys.stderr)
        return 2
    prompts_path, out_path = argv[1], argv[2]
    model = argv[3] if len(argv) > 3 else DEFAULT_MODEL
    temperature = float(os.environ["FMA_TEMPERATURE"])

    spec = json.load(open(prompts_path, encoding="utf-8"))
    schema = spec["schema"]
    step = spec.get("step", "?")
    system = spec["dispatch_instruction"] % (step, json.dumps(schema)) \
        if "%s" in spec.get("dispatch_instruction", "") else spec.get("dispatch_instruction", "")

    answers, failed, retried, fps = [], [], [], set()
    t0 = time.time()
    for i, p in enumerate(spec["prompts"], 1):
        action = _call(model, system, p["prompt"], schema, temperature, fps)
        if action is None:
            retried.append(p["id"])
            action = _call(model, system, p["prompt"], schema, temperature, fps)
        if action is None:
            failed.append(p["id"])
            continue
        answers.append({"id": p["id"], "action": action})
        if i % 4 == 0 or i == len(spec["prompts"]):
            print("    %d/%d  (%.0fs)" % (i, len(spec["prompts"]), time.time() - t0), flush=True)

    json.dump({"answers": answers, "provenance": {
        "provider": "groq", "model": model, "temperature": temperature,
        "reasoning_effort": REASONING_EFFORT if model.startswith("openai/gpt-oss") else None,
        "system_fingerprints": sorted(fps), "retried_ids": retried, "failed_ids": failed,
        "finished_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}},
        open(out_path, "w", encoding="utf-8"), indent=1)
    print("  step %s: %d answered, %d unanswered %s" % (step, len(answers), len(failed), failed if failed else ""))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
