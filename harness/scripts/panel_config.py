"""Selects the local-model arms (models C-F) that the analysis scripts read.

The local panel is the logged rerun: experiments/floor16v3_llama, _mistral, _qwen3, _phi3
(default sampling, R=10) and their *_t0 temperature-0 arms (R=5). FMA_PANEL may be unset or
"v3"; both select this panel. Output files carry a "_v3" suffix.

Models A and B (hosted) and the hosted Groq check do not depend on this setting.
"""
from __future__ import annotations

import os

PANEL = os.environ.get("FMA_PANEL", "v3").strip().lower() or "v3"
if PANEL != "v3":
    raise SystemExit("FMA_PANEL must be unset or 'v3' (got %r)" % PANEL)
V3 = True
SUFFIX = "_v3"

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
EXP = os.path.join(ROOT, "experiments")

LOCAL = {"C": "floor16v3_llama", "D": "floor16v3_mistral",
         "E": "floor16v3_qwen3", "F": "floor16v3_phi3"}


def local_dir(lab: str, t0: bool = False) -> str:
    """Directory name (under experiments/) of local model `lab`, default or temperature-0 arm."""
    return LOCAL[lab] + ("_t0" if t0 else "")


def out_path(stem: str, ext: str, subdir: str = "experiments") -> str:
    """ROOT/<subdir>/<stem>_v3.<ext>."""
    return os.path.join(ROOT, subdir, "%s%s.%s" % (stem, SUFFIX, ext))
