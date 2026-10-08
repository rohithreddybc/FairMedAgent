"""Single switch that selects which local-model arms (models C-F) the analysis scripts read.

    FMA_PANEL unset or "old"  -> the arms the current manuscript reports (floor16_ollama, ...).
    FMA_PANEL=v3              -> the re-run arms floor16v3_llama / _mistral / _qwen3 / _phi3
                                 (default sampling, R=10) and their *_t0 temperature-0 arms (R=5).

Models A and B (hosted) and the hosted Groq check are the same under both settings. Outputs
produced under v3 carry a "_v3" suffix, so a v3 run never overwrites a file the old manuscript
is verified against.
"""
from __future__ import annotations

import os

PANEL = os.environ.get("FMA_PANEL", "old").strip().lower()
if PANEL not in ("old", "v3"):
    raise SystemExit("FMA_PANEL must be unset, 'old' or 'v3' (got %r)" % PANEL)
V3 = PANEL == "v3"
SUFFIX = "_v3" if V3 else ""

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
EXP = os.path.join(ROOT, "experiments")

OLD_LOCAL = {"C": "floor16_ollama", "D": "floor16_mistral",
             "E": "floor16_qwen3", "F": "floor16_phi3"}
NEW_LOCAL = {"C": "floor16v3_llama", "D": "floor16v3_mistral",
             "E": "floor16v3_qwen3", "F": "floor16v3_phi3"}
LOCAL = NEW_LOCAL if V3 else OLD_LOCAL


def local_dir(lab: str, t0: bool = False) -> str:
    """Directory name (under experiments/) of local model `lab`, default or temperature-0 arm."""
    return LOCAL[lab] + ("_t0" if t0 else "")


def resolve_dir(path: str) -> str:
    """Remap an old local-arm directory argument to the v3 one when FMA_PANEL=v3.

    Used by scripts that take a directory on the command line (aggregation_curve.py,
    plateau_null.py). Any other path is returned unchanged.
    """
    if not V3:
        return path
    norm = os.path.normpath(path)
    parent, base = os.path.split(norm)
    for lab, old in OLD_LOCAL.items():
        for t0 in ("", "_t0"):
            if base == old + t0:
                return os.path.join(parent, NEW_LOCAL[lab] + t0)
    return path


def out_path(stem: str, ext: str, subdir: str = "experiments") -> str:
    """ROOT/<subdir>/<stem><suffix>.<ext>; the old panel keeps the original file name."""
    return os.path.join(ROOT, subdir, "%s%s.%s" % (stem, SUFFIX, ext))
