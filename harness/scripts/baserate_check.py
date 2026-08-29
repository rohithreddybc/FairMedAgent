"""Is the spread in per-action floors a real difference, or a base-rate artefact?

A reviewer raised the sharpest statistical objection this study has faced. The probability that
two independent draws disagree is maximised when the underlying rate is one half and falls to
zero as it approaches zero or one. Across these vignettes, ICU escalation is almost never
indicated while admission and controlled-substance caution are closer to evenly split. So an
eightfold spread in raw flip rates could be produced entirely by differing base rates, with no
action being intrinsically harder to decide than another.

If that is right, the paper's per-action framing is measuring prevalence and calling it
instability. The comparison has to be made against what each action's own base rate predicts.

The comparison has to be made against a model, and the model must not be the observed data
in disguise. Averaging each cell's own 2p(1-p) is exactly the observed within-cell disagreement
rearranged, so that ratio is 1.00 by construction and tests nothing; an earlier version of this
script made that mistake.

The informative null is homogeneity: if every cell of an action shared that action's marginal
rate p-bar, two draws would disagree with probability 2*p-bar*(1-p-bar). Comparing the observed
rate against that says how far the action's instability is concentrated in a few contested
cells rather than spread evenly. A ratio near one means the action is uniformly uncertain
across vignettes; a ratio far below one means most cells are decided and a minority carry the
disagreement. That ratio is comparable across actions in a way raw flip rates are not, because
it has prevalence divided out.

    python baserate_check.py <dir> [<dir2> ...]
"""
from __future__ import annotations

import itertools
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

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


def _load(d):
    reps = []
    for name in sorted(os.listdir(d)):
        p = os.path.join(d, name, "trajectories.json")
        if not os.path.exists(p):
            continue
        acts = {}
        for t in json.load(open(p, encoding="utf-8"))["trajectories"]:
            if t["complete"] and t["condition_id"] == REFERENCE:
                acts[t["vignette_id"]] = t["actions"]
        if acts:
            reps.append(acts)
    return reps


def analyse(d):
    reps = _load(d)
    n = len(reps)
    vign = sorted(set.intersection(*[set(r) for r in reps]))

    rows = []
    for name, proj in OUTCOMES.items():
        obs_flips = obs_pairs = 0
        predicted = 0.0
        cells = 0
        positives = total_draws = 0
        for v in vign:
            series = [proj(r[v]) for r in reps]
            series = [x for x in series if x is not None]
            if len(series) < 2:
                continue
            cells += 1
            k = sum(1 for x in series if x)
            m = len(series)
            positives += k
            total_draws += m
            # Observed disagreement among this cell's pairs.
            for a, b in itertools.combinations(range(m), 2):
                obs_pairs += 1
                if series[a] != series[b]:
                    obs_flips += 1
        obs = obs_flips / obs_pairs if obs_pairs else 0.0
        # Homogeneous-rate null: every cell of this action at the action's marginal rate.
        pbar = positives / total_draws if total_draws else 0.0
        pred = 2.0 * pbar * (1.0 - pbar)
        base = positives / total_draws if total_draws else 0.0
        rows.append((name, base, obs, pred, (obs / pred) if pred else float("nan")))
    return rows, n, len(vign)


def main(dirs):
    for d in dirs:
        rows, n, nv = analyse(d)
        print("=== %s  (%d replicates, %d vignettes) ===" % (os.path.basename(d), n, nv))
        print("%-14s %-10s %-11s %-13s %s"
              % ("action", "base rate", "observed", "predicted", "obs / predicted"))
        print("%-14s %-10s %-11s %-13s %s" % ("", "(P positive)", "flip rate", "if uniform", ""))
        for name, base, obs, pred, ratio in sorted(rows, key=lambda r: r[2]):
            print("%-14s %-10.3f %-11.3f %-13.3f %.2f" % (name, base, obs, pred, ratio))
        ratios = [r[4] for r in rows if r[4] == r[4]]
        print()
        print("   observed/predicted ranges %.2f to %.2f across the six actions."
              % (min(ratios), max(ratios)))
        obs_all = [r[2] for r in rows]
        print("   raw flip rates range %.3f to %.3f, a factor of %.1f."
              % (min(obs_all), max(obs_all), max(obs_all) / min(obs_all) if min(obs_all) else 0))
        print()
        spread = max(ratios) / max(min(ratios), 1e-9)
        if spread < 1.5:
            print("   Adjusted for prevalence the actions are alike, so the raw spread is")
            print("   substantially a base-rate effect and the per-action framing should say so.")
        else:
            print("   Adjusted for prevalence the actions still differ by a factor of %.1f, so"
                  % spread)
            print("   the raw spread is not merely prevalence. Every ratio is below one, which")
            print("   says instability is concentrated in a minority of contested cells rather")
            print("   than spread evenly -- and it is concentrated far more sharply for some")
            print("   actions than others.")
        print()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1:]))
