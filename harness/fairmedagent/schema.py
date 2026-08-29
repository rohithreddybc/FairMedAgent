"""Data model for the FairMedAgent multi-step clinical agent benchmark.

A vignette has a FROZEN ``clinical_core`` (identical across all demographic conditions);
a ``DemographicCondition`` contributes only a fixed-form one-line descriptor header
(decision D2). Tool results are a deterministic, condition-independent fixture so that any
divergence in the agent's trajectory is attributable to the demographic descriptor alone.

The agentic loop (decision D1) is a sequence of steps; only ``MODEL_CALL_STEPS`` invoke the
model, while ``results`` is an environment step (the simulated EHR returns labs/imaging).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

# Ordered agentic trajectory. 'results' is an environment step (no model call).
STEPS = ["triage", "order", "results", "reassess", "prescribe", "document"]
MODEL_CALL_STEPS = ["triage", "order", "reassess", "prescribe", "document"]  # 5 calls/vignette

DOMAINS = ["triage", "ordering", "medication", "documentation"]


@dataclass
class DemographicCondition:
    """One counterfactual condition: a fixed-form descriptor + structured attributes."""

    id: str
    descriptor: str                 # fixed one-line header, constant grammatical form (D2)
    attributes: dict = field(default_factory=dict)  # {race, sex, age_band, insurance, lep, ...}
    is_reference: bool = False      # the reference (e.g., privileged) condition for pairing


@dataclass
class Vignette:
    """A synthetic clinical case. ``clinical_core`` is held identical across conditions."""

    id: str
    domain: str
    clinical_core: str                              # FROZEN narrative (no demographics)
    tool_results: dict = field(default_factory=dict)  # orderable -> deterministic result
    acceptable: dict = field(default_factory=dict)    # clinician rubric: action -> acceptable set/range
    canary: Optional[str] = None                      # contamination canary string

    def __post_init__(self):
        if self.domain not in DOMAINS:
            raise ValueError(f"domain must be one of {DOMAINS}, got {self.domain!r}")


@dataclass
class StepResult:
    """Outcome of one trajectory step."""

    step: str
    action: dict
    model_calls: int = 0


@dataclass
class Trajectory:
    """The full agentic trajectory for one (vignette, condition, model, scaffold)."""

    vignette_id: str
    condition_id: str
    model: str
    scaffold: str
    steps: list = field(default_factory=list)
    # Run provenance. Absent these a trajectory cannot be tied to the call that produced it,
    # which defeats the reproducibility claim regardless of how well the statistics behave.
    seed: Optional[int] = None
    replicate: Optional[int] = None
    model_version: Optional[str] = None      # served build/snapshot, distinct from the alias
    response_ids: list = field(default_factory=list)
    forced_steps: list = field(default_factory=list)  # steps injected, not model-generated
    descriptor_steps: list = field(default_factory=list)  # steps that showed the descriptor
    fixture_ambiguities: list = field(default_factory=list)  # underspecified orders + candidates
    unresolved_orderables: list = field(default_factory=list)  # ordered items with no fixture
    timestamp: Optional[str] = None          # caller-supplied; never read from the clock here

    def actions(self) -> dict:
        """Map of step name -> parsed action dict."""
        return {s.step: s.action for s in self.steps}

    def total_model_calls(self) -> int:
        return sum(s.model_calls for s in self.steps)
