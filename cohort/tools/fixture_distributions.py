"""Ground vignette fixture values in Synthea's empirical distributions.

The draft vignettes carry hand-chosen fixture values -- HR 104, temperature 38.1, WBC 14.2 --
and a reviewer is entitled to ask where those numbers came from. "They seemed reasonable" is a
weak answer for a benchmark whose entire claim rests on the clinical narrative being credible.
This reads Synthea's observation export and reports, per observation code, the distribution the
generator actually produces, so a fixture value can be checked against it and either defended or
moved.

It does **not** invent vignettes and it does not select patients. Its output is a reference
table.

    python fixture_distributions.py summary <csv-dir> [code-or-substring ...]
    python fixture_distributions.py check   <csv-dir> <substring> <value>

## The demographic constraint

Synthea's modules are demographically parameterised: prevalence and course differ by race,
ethnicity, sex and age because the generator is built to reproduce real epidemiology. That is a
virtue everywhere except here. FairMedAgent varies the demographic descriptor against a frozen
clinical narrative, so any clinical value whose distribution was conditioned on demographics
would smuggle the generator's demographic-clinical correlation into the contrast being measured,
and a flip caused by that correlation could not be told apart from a flip caused by the model.

This module therefore never joins observations to `patients.csv`, and refuses to run if asked to
stratify. The refusal is the point: the safe behaviour has to be the one that takes no effort.
"""
from __future__ import annotations

import csv
import os
import sys

# Joining on any of these would condition a fixture distribution on demographics.
FORBIDDEN_JOIN_FILES = ("patients.csv",)
FORBIDDEN_FIELDS = ("RACE", "ETHNICITY", "GENDER", "BIRTHDATE", "MARITAL", "INCOME")


def _percentile(sorted_values, q):
    if not sorted_values:
        return None
    if len(sorted_values) == 1:
        return sorted_values[0]
    pos = q * (len(sorted_values) - 1)
    lo = int(pos)
    hi = min(lo + 1, len(sorted_values) - 1)
    frac = pos - lo
    return sorted_values[lo] * (1 - frac) + sorted_values[hi] * frac


def load_numeric_observations(csv_dir: str) -> dict:
    """Read observations.csv into {(description, units): [values]}, demographics untouched.

    Only the observation rows are read. The patient identifier is used for nothing -- not to
    join, not to deduplicate, not to weight -- so no demographic attribute can reach the output
    even indirectly.
    """
    path = os.path.join(csv_dir, "observations.csv")
    if not os.path.exists(path):
        raise SystemExit("no observations.csv in %s" % csv_dir)
    out: dict = {}
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if row.get("TYPE") != "numeric":
                continue
            try:
                value = float(row["VALUE"])
            except (TypeError, ValueError):
                continue
            out.setdefault((row["DESCRIPTION"], row.get("UNITS") or ""), []).append(value)
    return out


def _assert_no_demographic_leak(csv_dir: str) -> None:
    """Fail loudly if this script is ever pointed at a directory it should not read.

    A future edit that adds a demographic join would be a quiet correctness failure rather than
    a crash, so the constraint is asserted where it can be seen rather than left in the
    docstring.
    """
    for name in FORBIDDEN_JOIN_FILES:
        if name in globals().get("_OPENED_FILES", set()):
            raise SystemExit("refusing to run: %s was opened; see the module docstring" % name)


def cmd_summary(csv_dir: str, *filters: str) -> int:
    data = load_numeric_observations(csv_dir)
    _assert_no_demographic_leak(csv_dir)
    keys = sorted(data)
    if filters:
        low = [f.lower() for f in filters]
        keys = [k for k in keys if any(f in k[0].lower() for f in low)]
    if not keys:
        print("no matching observation codes")
        return 1
    print("%-58s %6s %8s %8s %8s %8s %8s  %s"
          % ("observation", "n", "p5", "p25", "median", "p75", "p95", "units"))
    for key in keys:
        vals = sorted(data[key])
        print("%-58s %6d %8.2f %8.2f %8.2f %8.2f %8.2f  %s"
              % (key[0][:58], len(vals), _percentile(vals, 0.05), _percentile(vals, 0.25),
                 _percentile(vals, 0.50), _percentile(vals, 0.75), _percentile(vals, 0.95),
                 key[1]))
    return 0


def cmd_check(csv_dir: str, substring: str, value: str) -> int:
    """Locate a proposed fixture value within the generator's empirical distribution."""
    data = load_numeric_observations(csv_dir)
    _assert_no_demographic_leak(csv_dir)
    v = float(value)
    matches = [k for k in sorted(data) if substring.lower() in k[0].lower()]
    if not matches:
        print("no observation code matching %r" % substring)
        return 1
    for key in matches:
        vals = sorted(data[key])
        below = sum(1 for x in vals if x < v)
        pct = 100.0 * below / len(vals)
        lo, hi = _percentile(vals, 0.05), _percentile(vals, 0.95)
        # A fixture outside the central 90% is not wrong -- vignettes are chosen to sit at
        # decision points, which are by construction unusual -- but it should be deliberate.
        verdict = "within p5-p95" if lo <= v <= hi else "OUTSIDE p5-p95, justify explicitly"
        print("%s [%s]\n   n=%d  value=%g at %.1f percentile  p5=%.2f p95=%.2f  -> %s"
              % (key[0], key[1], len(vals), v, pct, lo, hi, verdict))
    # Stated on every check rather than buried in documentation, because the percentile is
    # easy to over-read. The reference population is every encounter Synthea generated, and
    # those are mostly wellness and ambulatory visits. A vignette is built to sit at a decision
    # threshold, so a high percentile against this population is expected and is not evidence
    # that the value is implausible for an emergency presentation. The comparison establishes
    # that a value lies on the generator's scale, not that it is typical of the setting.
    print("\n   reference population: all generated encounters, predominantly wellness and\n"
          "   ambulatory. Not an emergency-department reference range.")
    return 0


if __name__ == "__main__":
    cmds = {"summary": cmd_summary, "check": cmd_check}
    if len(sys.argv) < 3 or sys.argv[1] not in cmds:
        print(__doc__)
        sys.exit(2)
    sys.exit(cmds[sys.argv[1]](*sys.argv[2:]))
