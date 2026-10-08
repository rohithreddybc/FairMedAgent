"""Exact permutation tests for every pair of models, and per-action audit sizing.

Two gaps this closes. The A-B rank correlation was tested exactly while the two cross-family
correlations that carry the non-transfer claim were reported bare, which is the wrong way round:
the claim the paper leads with deserves at least the scrutiny the supporting one got. And the
required vignette count was computed from the pooled floor, although the paper's own argument is
that a pooled floor describes no action well; the per-action range is the honest version.

    python rank_tests.py
"""
from __future__ import annotations

import itertools
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import panel_config as pc  # noqa: E402  (FMA_PANEL=v3 -> model C is floor16v3_llama)
REFERENCE = "ref_white_man_private"

OUTCOMES = {
    "high_acuity":  lambda a: (lambda e: None if e is None else e <= 2)(
        (a.get("triage") or {}).get("esi_acuity")),
    "admit":        lambda a: (a.get("reassess") or {}).get("admit"),
    "escalate_icu": lambda a: (a.get("reassess") or {}).get("escalate_icu"),
    "any_opioid":   lambda a: (lambda t: None if t is None else t >= 2)(
        (a.get("prescribe") or {}).get("analgesia_tier")),
    "cs_caution":   lambda a: (a.get("prescribe") or {}).get("controlled_substance_caution"),
    "referral":     lambda a: (a.get("document") or {}).get("referral"),
}
KEYS = sorted(OUTCOMES)


def reps(d: str) -> list[dict]:
    out = []
    root = os.path.join(ROOT, "experiments", d)
    for name in sorted(os.listdir(root)):
        p = os.path.join(root, name, "trajectories.json")
        if not os.path.exists(p):
            continue
        acts = {}
        for t in json.load(open(p, encoding="utf-8"))["trajectories"]:
            if t["complete"] and t["condition_id"] == REFERENCE:
                acts[t["vignette_id"]] = t["actions"]
        if acts:
            out.append(acts)
    return out


def rates(rs: list[dict]) -> tuple[dict, int]:
    vs = sorted(set.intersection(*[set(r) for r in rs]))
    per = {k: [0, 0] for k in OUTCOMES}
    for a, b in itertools.combinations(range(len(rs)), 2):
        for v in vs:
            for k, proj in OUTCOMES.items():
                x, y = proj(rs[a][v]), proj(rs[b][v])
                if x is None or y is None:
                    continue
                per[k][1] += 1
                if x != y:
                    per[k][0] += 1
    return per, len(vs)


def ranks(vals):
    order = sorted(range(len(vals)), key=lambda i: vals[i])
    out = [0] * len(vals)
    for pos, i in enumerate(order):
        out[i] = pos + 1
    return out


def rho(a, b):
    d2 = sum((u - v) ** 2 for u, v in zip(a, b))
    return 1 - (6.0 * d2) / (len(a) * (len(a) ** 2 - 1))


def exact_p(ra, rb):
    """Two-sided exact permutation p over all 720 relabelings of six actions."""
    obs = abs(rho(ra, rb))
    hits = tot = 0
    for perm in itertools.permutations(rb):
        tot += 1
        if abs(rho(ra, list(perm))) >= obs - 1e-12:
            hits += 1
    return hits / tot


def main() -> int:
    arms = {}
    for d, label in (("floor16", "A"), ("floor16_sonnet", "B"), (pc.local_dir("C"), "C")):
        rs = reps(d)
        per, G = rates(rs)
        arms[label] = (per, len(rs), G)
        n_pairs = len(rs) * (len(rs) - 1) // 2
        print("%s: R=%d, %d vignettes, %d pairs, %d comparisons per action"
              % (label, len(rs), G, n_pairs, per[KEYS[0]][1]))

    print("\nrank correlations, exact two-sided permutation over 720 orderings")
    for x, y in (("A", "B"), ("A", "C"), ("B", "C")):
        rx = ranks([arms[x][0][k][0] / arms[x][0][k][1] for k in KEYS])
        ry = ranks([arms[y][0][k][0] / arms[y][0][k][1] for k in KEYS])
        print("  %s-%s  rho=%.2f  p=%.3f" % (x, y, rho(rx, ry), exact_p(rx, ry)))

    print("\nvignettes needed for 25 discordant pairs, by action (model A)")
    per = arms["A"][0]
    for k in sorted(KEYS, key=lambda k: per[k][0] / per[k][1]):
        r = per[k][0] / per[k][1]
        print("  %-14s pi_d=%.3f  N=%s" % (k, r, ("%d" % round(25 / r)) if r else "undefined"))
    pooled = sum(per[k][0] for k in KEYS) / sum(per[k][1] for k in KEYS)
    print("  %-14s pi_d=%.3f  N=%d" % ("POOLED", pooled, round(25 / pooled)))
    return 0


if __name__ == "__main__":
    if pc.V3:
        import io
        buf, real = io.StringIO(), sys.stdout

        class _Tee:
            def write(self, t):
                real.write(t)
                buf.write(t)

            def flush(self):
                real.flush()

        sys.stdout = _Tee()
        try:
            rc = main()
        finally:
            sys.stdout = real
        with open(pc.out_path("rank_tests", "txt"), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(buf.getvalue())
        raise SystemExit(rc)
    raise SystemExit(main())
