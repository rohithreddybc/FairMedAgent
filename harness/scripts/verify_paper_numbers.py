"""Check every computable number in the manuscript against the artifact it came from.

Numbers drift. This manuscript has been through several rounds in which a figure was
superseded by a better measurement, and each round risked leaving a stale value behind in a
section nobody re-read. This script recomputes what can be recomputed and reports any
disagreement with the text, so the check is mechanical rather than a matter of remembering.

It deliberately does not parse the LaTeX for numbers and diff them, which would be brittle.
Each claim is named, recomputed from its source, and asserted to appear in the manuscript.

    python verify_paper_numbers.py
"""
from __future__ import annotations

import io
import itertools
import json
import os
import re
import sys
from math import comb

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "harness"))

PAPER = os.environ.get("FAIRMEDAGENT_PAPER") or os.path.join(ROOT, "paper", "main.tex")

# The manuscript source is not part of the public artifact release, so a fresh clone has
# the trajectories but no main.tex. Recomputation still works there; only the step that
# asserts each figure appears in the text is skipped. Point at a manuscript with
# FAIRMEDAGENT_PAPER=/path/to/main.tex or as the first argument to get the full check.
INST = os.path.join(ROOT, "experiments", "floor16")

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


def _reps():
    out = []
    for name in sorted(os.listdir(INST)):
        p = os.path.join(INST, name, "trajectories.json")
        if not os.path.exists(p):
            continue
        acts = {}
        for t in json.load(open(p, encoding="utf-8"))["trajectories"]:
            if t["complete"] and t["condition_id"] == REFERENCE:
                acts[t["vignette_id"]] = t["actions"]
        if acts:
            out.append(acts)
    return out


def main() -> int:
    paper = sys.argv[1] if len(sys.argv) > 1 else PAPER
    have_paper = os.path.exists(paper)
    tex = io.open(paper, encoding="utf-8").read() if have_paper else ""
    # Expand \input{name} so a manuscript split into section files is checked in full.
    if have_paper:
        base = os.path.dirname(os.path.abspath(paper))

        def _expand(m):
            name = m.group(1)
            path = os.path.join(base, name if name.endswith(".tex") else name + ".tex")
            return io.open(path, encoding="utf-8").read() if os.path.exists(path) else m.group(0)

        tex = re.sub(r"\\input\{([^}]+)\}", _expand, tex)

    # Numbers relocated out of the main manuscript (full tables, derivations, and protocol
    # detail moved to keep the main text within its page target) still need to stay
    # machine-checked, so a sibling supplementary.tex is folded into the same haystack every
    # claim below is checked against. Point at a different file with
    # FAIRMEDAGENT_SUPPLEMENT=/path/to/supplementary.tex; its absence is not an error, since
    # the public artifact release and older manuscripts do not have one.
    paper_dir_for_supp = os.path.dirname(os.path.abspath(paper)) if have_paper else None
    supp_path = os.environ.get("FAIRMEDAGENT_SUPPLEMENT") or (
        os.path.join(paper_dir_for_supp, "supplementary.tex")
        if paper_dir_for_supp else None)
    if supp_path and os.path.exists(supp_path):
        tex += "\n" + io.open(supp_path, encoding="utf-8").read()

    # Some reported numbers live only inside a standalone pgfplots figure (compiled separately
    # and \includegraphics'd in), not in the manuscript body text. Those figures are still
    # reported to the reader, so their source is checked too: fig_tex is the manuscript plus
    # every fig_*.tex found beside it, and a claim may check against either haystack.
    paper_dir = os.path.dirname(os.path.abspath(paper)) if have_paper else None
    fig_tex = tex
    if paper_dir and os.path.isdir(paper_dir):
        for name in sorted(os.listdir(paper_dir)):
            if name.startswith("fig_") and name.endswith(".tex"):
                fig_tex += "\n" + io.open(os.path.join(paper_dir, name), encoding="utf-8").read()

    checks, failures = [], 0

    def claim(label, value, needle, haystack=None):
        # needle may be a single string, or a tuple/list of alternative surface forms of the
        # same number (e.g. "$0.142$" in running prose vs plain "0.142" in a pgfplots data
        # table); the claim passes if any alternative is found.
        nonlocal failures
        hay = tex if haystack is None else haystack
        needles = (needle,) if isinstance(needle, str) else tuple(needle)
        ok = (any(n in hay for n in needles)) if have_paper else None
        checks.append((label, value, "|".join(needles), ok))
        if ok is False:
            failures += 1

    reps = _reps()
    n = len(reps)
    vignettes = sorted(set.intersection(*[set(r) for r in reps]))

    # --- pooled floor and per-action floors -------------------------------------------
    flips = total = 0
    per = {k: [0, 0] for k in OUTCOMES}
    for a, b in itertools.combinations(range(n), 2):
        for v in vignettes:
            for k, proj in OUTCOMES.items():
                x, y = proj(reps[a][v]), proj(reps[b][v])
                if x is None or y is None:
                    continue
                total += 1
                per[k][1] += 1
                if x != y:
                    flips += 1
                    per[k][0] += 1
    pooled = flips / total

    claim("replicate count", n, "ten independent replicates")
    claim("pairwise comparisons", n * (n - 1) // 2, "forty-five pairwise")
    claim("model calls", n * 80, "$800$ model calls")
    claim("pooled floor", round(pooled, 3), "$%.3f$" % pooled)
    claim("comparisons per action", per["admit"][1], "$720$ comparisons")
    claim("pooled comparisons", total, "$%d/%d$" % (flips, total))
    for k in ("escalate_icu", "referral", "any_opioid", "cs_caution", "admit", "high_acuity"):
        f, t = per[k]
        r = f / t
        # Checked against tex-or-figures, in either the "$0.142$" form running prose and the
        # summary table use, or the plain "0.142" form a pgfplots data row uses (fig_tex is
        # tex plus every fig_*.tex found beside it).
        claim("floor %s" % k, round(r, 3), ("$%.3f$" % r, "%.3f" % r), haystack=fig_tex)

    # --- aggregation curve ------------------------------------------------------------
    def vote(vals):
        vals = [v for v in vals if v is not None]
        if not vals:
            return None
        t_ = sum(1 for v in vals if v)
        return None if t_ * 2 == len(vals) else t_ * 2 > len(vals)

    def agg_rate(k_):
        fl = to = 0
        seen = set()
        for A in itertools.combinations(range(n), k_):
            rest = [i for i in range(n) if i not in A]
            for B in itertools.combinations(rest, k_):
                key = tuple(sorted([A, B]))
                if key in seen:
                    continue
                seen.add(key)
                for v in vignettes:
                    for _, proj in OUTCOMES.items():
                        x = vote([proj(reps[i][v]) for i in A])
                        y = vote([proj(reps[i][v]) for i in B])
                        if x is None or y is None:
                            continue
                        to += 1
                        if x != y:
                            fl += 1
        return fl / to if to else None

    for k_ in (3, 5):
        r = agg_rate(k_)
        claim("floor at R=%d" % k_, round(r, 3), "$%.3f$" % r)

    # --- derived design quantities ----------------------------------------------------
    n_needed = 25 / pooled
    claim("N from floor", round(n_needed), "gives $%d$" % round(n_needed))

    p3 = comb(4, 3) * pooled ** 3 * (1 - pooled) + pooled ** 4
    claim("P(>=3 of 4 | pooled)", round(p3, 3), "$%.3f$" % p3)

    cs = per["cs_caution"][0] / per["cs_caution"][1]
    p3cs = comb(4, 3) * cs ** 3 * (1 - cs) + cs ** 4
    claim("P(>=3 of 4 | cs_caution)", round(p3cs, 3), "$%.3f$" % p3cs)

    # --- full six-model panel -----------------------------------------------------------
    # The manuscript now reports the whole panel (six models; a seventh, glm-4.7-flash, never
    # produced usable runs and its directory was removed) rather than narrating models one at a
    # time. panel_summary.py is the single source of truth for the pooled floor, its bootstrap
    # interval, and the full pairwise Spearman matrix; this block imports that module directly
    # and asserts against the identical computation (same RNG, same seed, same draw order) so
    # the two scripts cannot silently disagree.
    sys.path.insert(0, HERE)
    import panel_summary as ps

    panel = ps.build_panel(B=600, seed=42)
    labels = [row[0] for row in panel]
    floors = {row[0]: row[6] for row in panel}

    for lab, name, vendor, host, size, R, pooled_m, lo, hi, rates, worst in panel:
        claim("panel floor %s" % lab, round(pooled_m, 3), "$%.3f$" % pooled_m)
        claim("panel CI %s" % lab, "[%.3f, %.3f]" % (lo, hi), "[%.3f, %.3f]" % (lo, hi))
        # Per-action rates for B-F appear only in the fig_per_action.pgfplots data table (a
        # 6x6 heatmap in the manuscript, not restated as running text or a second table), so
        # those claims are checked against the figure source too, in plain "0.150" form,
        # which is how a pgfplots data row prints a value, rather than the "$0.150$" form
        # prose and the summary table use.
        for k, r in zip(ps.KEYS, rates):
            claim("panel %s %s" % (lab, k), round(r, 3),
                  ("$%.3f$" % r, "%.3f" % r), haystack=fig_tex)

    fmin, fmax = min(floors.values()), max(floors.values())
    ratio = fmax / fmin if fmin else float("inf")
    claim("floor range low", round(fmin, 3), "$%.3f$" % fmin)
    claim("floor range high", round(fmax, 3), "$%.3f$" % fmax)
    claim("floor range factor", round(ratio, 1), "%.1f" % ratio)

    # Full pairwise Spearman matrix over the panel, midranks with the Pearson form, exact
    # permutation p over all orderings of one side. Every pair the manuscript's correlation
    # table or prose cites is asserted here against this same computation.
    matrix = {}
    for i, j in itertools.combinations(range(len(panel)), 2):
        ri, rj = ps.midranks(panel[i][9]), ps.midranks(panel[j][9])
        rho = ps.pearson(ri, rj)
        p = ps.exact_p(ri, rj)
        pair = "%s-%s" % (panel[i][0], panel[j][0])
        matrix[pair] = (rho, p)
        claim("rho %s" % pair, round(rho, 2), "%.2f" % rho)

    # The specific pairs the two-cluster narrative rests on carry their exact p-value too.
    for pair in ("A-B", "A-E", "B-E", "C-F"):
        rho, p = matrix[pair]
        claim("p %s" % pair, round(p, 3), "%.3f" % p)

    # --- superseded figures must be ABSENT ----------------------------------------------
    # The checks above confirm that current values appear. They cannot catch a stale value
    # left behind in a section nobody re-read, which is exactly how the four-vignette floor
    # survived in the first contribution bullet after Sec. IV-A had disowned it. Each entry
    # here is a figure a better measurement replaced; finding one is a failure.
    RETIRED = [
        ("13.6", "four-vignette pooled floor, superseded by 0.087"),
        ("0.136", "four-vignette pooled floor, superseded by 0.087"),
        ("$0.128$", "six-replicate pooled floor, superseded by 0.087"),
        ("two of six actions never moved", "four-vignette artifact; no action is at zero now"),
        ("$180$ comparisons", "four-vignette comparison count, superseded by 720"),
        ("N{=}120", "vignette count derived from the single-draw floor"),
        ("N{=}200", "vignette count derived from the four-vignette floor"),
        # R=6-panel figures for C, D, E, F, superseded when those four models were re-run at
        # R=10 (B stayed at R=6; A was already at R=10). The two-cluster structure computed
        # from the R=6 panel is also retired here, not because the old correlation values are
        # wrong to mention (the withdrawal narrative in Sec. IV-A cites them deliberately,
        # which the narration check below allows), but so a stale, unnarrated restatement of
        # the old pooled floors or the old 8.4x / 2.7% / 22.7% range figures cannot creep back
        # into a section nobody re-read.
        ("$0.206$", "llama3.1:8b R=6 pooled floor, superseded by 0.215 at R=10"),
        ("$0.227$", "phi3:mini R=6 pooled floor, superseded by 0.237 at R=10"),
        ("$0.091$", "mistral:7b R=6 pooled floor, superseded by 0.095 at R=10"),
        ("$0.027$", "qwen3:4b R=6 pooled floor, superseded by 0.025 at R=10"),
        ("$8.4$", "R=6 panel floor-range factor, superseded by 9.4 at R=10"),
        ("$2.7\\%$", "R=6 panel floor-range low end, superseded by 2.5% at R=10"),
        ("$22.7\\%$", "R=6 panel floor-range high end, superseded by 23.7% at R=10"),
    ]
    stale = []
    for needle, why in (RETIRED if have_paper else []):
        # Allow a figure to appear where the text is explicitly narrating its retraction.
        for m in re.finditer(re.escape(needle), tex):
            window = tex[max(0, m.start() - 260):m.end() + 260]
            narrating = any(w in window for w in
                            ("artifact", "artefact", "superseded", "retract", "withdraw",
                             "moved from", "at four vignettes", "single-draw", "earlier",
                             "wrong in the direction", "has now moved"))
            if not narrating:
                stale.append((needle, why))
                break
    for needle, why in stale:
        failures += 1
        checks.append(("STALE %s" % needle, "-", "should be absent", False))

    # --- report -----------------------------------------------------------------------
    print("%-28s %-10s %-14s %s" % ("claim", "computed", "as written", "in paper"))
    for label, value, needle, ok in checks:
        mark = "n/a" if ok is None else ("yes" if ok else "NO")
        print("%-28s %-10s %-14s %s" % (label, value, needle[:14], mark))
    print()
    if not have_paper:
        print("Recomputed %d quantities from the released trajectories." % len(checks))
        print("The manuscript source is not in this release, so the step that asserts each")
        print("figure appears in the text was skipped. To run it, pass the path to main.tex:")
        print("    python %s /path/to/main.tex" % os.path.basename(__file__))
        return 0
    if failures:
        print("%d claim(s) not found in the manuscript as computed." % failures)
        return 1
    print("all %d computable claims match the artifacts." % len(checks))
    return 0


if __name__ == "__main__":
    sys.exit(main())
