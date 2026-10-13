"""Whole-panel summary: floors, intervals, and the pairwise rank-correlation matrix.

Computes, for each model in the panel, the pooled instability floor over the five defined
actions (headline) and over six outputs (adding the exploratory controlled-substance caution
flag), with 95 percent intervals, and the pairwise rank-correlation matrix of the per-action
rates. It reads every `floor16*` directory it finds, uses midranks with the Pearson form (the
1-6*sum(d^2) shortcut is wrong whenever two actions tie), and records the model attributes an
auditor could read off a model card, so the claim that no observable attribute predicts the
floor can be checked.

    python panel_summary.py [bootstrap_resamples]

With FMA_BOOT=crossed the intervals are the crossed (vignette by replicate) bootstrap intervals
stored in experiments/robustness_v3_crossed.json; otherwise they are vignette-bootstrap
intervals computed here. The output is also written to experiments/panel_summary_v3.txt.
"""
from __future__ import annotations

import itertools
import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
REFERENCE = "ref_white_man_private"

# Attributes an auditor could read off a model card, recorded here so the claim that none of
# them predicts the floor is checkable. Unknown entries stay unknown rather than guessed.
sys.path.insert(0, HERE)
import panel_config as pc  # noqa: E402  (local-arm directories)

ATTRS = {
    "floor16":         ("A", "haiku-4.5",      "vendor-1", "hosted", "undisclosed"),
    "floor16_sonnet":  ("B", "sonnet-5",       "vendor-1", "hosted", "undisclosed"),
    pc.local_dir("C"): ("C", "llama3.1:8b",    "vendor-2", "local",  "8B q4"),
    pc.local_dir("D"): ("D", "mistral:7b",     "vendor-3", "local",  "7B q4"),
    pc.local_dir("E"): ("E", "qwen3:4b",       "vendor-4", "local",  "4B q8"),
    pc.local_dir("F"): ("F", "phi3:mini",      "vendor-5", "local",  "3.8B q4"),
    "floor16_glm":     ("G", "glm-4.7-flash",  "vendor-6", "local",  "flash"),
}

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


def reps(d):
    out = []
    root = os.path.join(ROOT, "experiments", d)
    if not os.path.isdir(root):
        return out
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


def counts(rs, vignettes):
    per = {k: [0, 0] for k in OUTCOMES}
    for a, b in itertools.combinations(range(len(rs)), 2):
        for v in vignettes:
            for k, proj in OUTCOMES.items():
                if v not in rs[a] or v not in rs[b]:
                    continue
                x, y = proj(rs[a][v]), proj(rs[b][v])
                if x is None or y is None:
                    continue
                per[k][1] += 1
                if x != y:
                    per[k][0] += 1
    return per


def midranks(vals):
    order = sorted(range(len(vals)), key=lambda i: vals[i])
    out = [0.0] * len(vals)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and vals[order[j + 1]] == vals[order[i]]:
            j += 1
        avg = (i + j) / 2.0 + 1
        for k in range(i, j + 1):
            out[order[k]] = avg
        i = j + 1
    return out


def pearson(a, b):
    n = len(a)
    ma, mb = sum(a) / n, sum(b) / n
    num = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    da = sum((x - ma) ** 2 for x in a) ** 0.5
    db = sum((y - mb) ** 2 for y in b) ** 0.5
    return num / (da * db) if da and db else float("nan")


def exact_p(ra, rb):
    obs = abs(pearson(ra, rb))
    hits = tot = 0
    for perm in itertools.permutations(rb):
        tot += 1
        if abs(pearson(ra, list(perm))) >= obs - 1e-12:
            hits += 1
    return hits / tot


def build_panel(B=5000, seed=42):
    """Return one tuple per model with data present, in ATTRS order, each
    (lab, name, vendor, host, size, R, pooled_floor, ci_lo, ci_hi, per_action_rates, noisiest_key).

    Shared by the CLI below and by verify_paper_numbers.py, so both scripts run the identical
    computation (same RNG, same seed, same draw order) and cannot silently disagree.
    """
    rng = random.Random(seed)
    panel = []
    for d, (lab, name, vendor, host, size) in ATTRS.items():
        rs = reps(d)
        if not rs:
            continue
        vs = sorted(set.intersection(*[set(r) for r in rs]))
        per = counts(rs, vs)
        pooled = sum(per[k][0] for k in KEYS) / sum(per[k][1] for k in KEYS)

        draws = []
        for _ in range(B):
            samp = [rng.choice(vs) for _ in vs]
            c = counts(rs, samp)
            n = sum(c[k][1] for k in KEYS)
            if n:
                draws.append(sum(c[k][0] for k in KEYS) / n)
        draws.sort()
        if draws:
            lo = draws[int(0.025 * len(draws))]
            hi = draws[min(len(draws) - 1, int(0.975 * len(draws)))]
        else:  # B=0: floors and rates only (crossed intervals are read from JSON)
            lo = hi = float("nan")

        rates = [per[k][0] / per[k][1] for k in KEYS]
        worst = KEYS[max(range(len(KEYS)), key=lambda i: rates[i])]
        panel.append((lab, name, vendor, host, size, len(rs), pooled, lo, hi, rates, worst))

    panel.sort(key=lambda r: r[0])
    return panel


FIVE = [k for k in KEYS if k != "cs_caution"]


def five_action_panel(B=5000, seed=42):
    """Per model: (lab, five-action pooled floor, vignette-bootstrap interval).

    The five defined actions exclude the exploratory controlled-substance caution flag. The
    interval resamples vignettes only; the crossed (vignette by replicate) intervals are read
    from experiments/robustness_v3_crossed.json when FMA_BOOT=crossed.
    """
    rng = random.Random(seed)
    out = []
    for d, (lab, *_rest) in ATTRS.items():
        rs = reps(d)
        if not rs:
            continue
        vs = sorted(set.intersection(*[set(r) for r in rs]))
        per = counts(rs, vs)
        pooled = sum(per[k][0] for k in FIVE) / sum(per[k][1] for k in FIVE)
        draws = []
        for _ in range(B):
            c = counts(rs, [rng.choice(vs) for _ in vs])
            n = sum(c[k][1] for k in FIVE)
            if n:
                draws.append(sum(c[k][0] for k in FIVE) / n)
        draws.sort()
        out.append((lab, pooled, draws[int(0.025 * len(draws))],
                    draws[min(len(draws) - 1, int(0.975 * len(draws)))]))
    return {r[0]: r for r in out}


def main(argv):
    B = int(argv[1]) if len(argv) > 1 else 5000
    crossed = os.environ.get("FMA_BOOT", "vignette").strip().lower() == "crossed"
    panel = build_panel(0 if crossed else B)
    five = {} if crossed else five_action_panel(B)
    xc = None
    if crossed:
        xc = json.load(open(os.path.join(ROOT, "experiments", "robustness%s_crossed.json" % pc.SUFFIX),
                            encoding="utf-8"))["crossed"]["models"]
    kind = "crossed (vignette x replicate) bootstrap" if crossed else "vignette bootstrap"

    print("PANEL  (%d models, 16 vignettes each)" % len(panel))
    print("Headline: five-action pooled floor (admission, ICU escalation, high acuity, referral, any opioid).")
    print("Intervals: 95%%, %s%s." % (kind, ", read from experiments/robustness_v3_crossed.json" if crossed else ""))
    print("The six-action columns add the exploratory controlled-substance caution flag (cs_caution).\n")
    print("%-3s %-15s %-9s %-7s %-12s %-3s %7s  %-14s %-11s %7s  %-14s %s"
          % ("id", "model", "vendor", "host", "size", "R", "5-act", "95% interval",
             "noisiest-5", "6-act", "95% interval", "noisiest-6"))
    f5 = {}
    for lab, name, vendor, host, size, R, p6, lo6, hi6, rates, worst6 in panel:
        if crossed:
            p5 = xc[lab]["floor_5action"]
            lo5, hi5 = xc[lab]["ci_5action"]
            lo6, hi6 = xc[lab]["ci_6action"]
        else:
            _, p5, lo5, hi5 = five[lab]
        f5[lab] = p5
        worst5 = FIVE[max(range(len(FIVE)), key=lambda i: rates[KEYS.index(FIVE[i])])]
        print("%-3s %-15s %-9s %-7s %-12s %-3d %7.3f  [%.3f, %.3f]  %-11s %7.3f  [%.3f, %.3f]  %s"
              % (lab, name, vendor, host, size, R, p5, lo5, hi5, worst5, p6, lo6, hi6, worst6))

    floors = list(f5.values())
    print("\nfive-action floor range %.3f to %.3f, a factor of %.1f"
          % (min(floors), max(floors), max(floors) / min(floors) if min(floors) else 0))
    floors6 = [r[6] for r in panel]
    print("six-action floor range %.3f to %.3f, a factor of %.1f"
          % (min(floors6), max(floors6), max(floors6) / min(floors6) if min(floors6) else 0))

    print("\nPAIRWISE SPEARMAN over the six per-action rates (midranks, Pearson form); exact p over 720 orderings")
    print("%-7s %6s %7s" % ("pair", "rho", "p"))
    for i, j in itertools.combinations(range(len(panel)), 2):
        ri, rj = midranks(panel[i][9]), midranks(panel[j][9])
        print("%-7s %6.2f %7.3f"
              % ("%s-%s" % (panel[i][0], panel[j][0]), pearson(ri, rj), exact_p(ri, rj)))
    return 0


if __name__ == "__main__":
    if True:
        # The printed summary is also captured to experiments/panel_summary_v3.txt.
        import io
        buf = io.StringIO()
        real = sys.stdout

        class _Tee:
            def write(self, s):
                real.write(s)
                buf.write(s)

            def flush(self):
                real.flush()

        sys.stdout = _Tee()
        try:
            rc = main(sys.argv)
        finally:
            sys.stdout = real
        with open(pc.out_path("panel_summary", "txt"), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(buf.getvalue())
        raise SystemExit(rc)
    raise SystemExit(main(sys.argv))
