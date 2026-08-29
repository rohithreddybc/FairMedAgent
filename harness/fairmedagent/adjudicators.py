"""Who adjudicated a band, recorded so the claim can be checked rather than believed.

An adjudicator may be anonymous to readers. That is a normal arrangement and journals accept
it. What an adjudicator may not be is *unattested*: a bare handle in ``adjudicated_by`` that
resolves to no recorded person is indistinguishable from a model, or from nobody, and the
benchmark's ground truth would then rest on an assertion no reviewer could test.

So identity and attestation are separated. The published record carries a stable pseudonym and
a credential; the signed attestation carrying the real name, registration number and
institution is held by the corresponding author and produced to the editor on request, and is
never committed to this repository. This module holds the public half and records whether the
private half exists.

``clinician-adjudicated`` is refused for a pseudonym that is not registered here, or that is
registered without an attestation on file. Refusing is the point: the failure mode this guards
against is a provenance level that reports green while resting on nothing.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Adjudicator:
    """One adjudicator, as the public record may describe them."""

    pseudonym: str
    specialty: Optional[str] = None          # e.g. "emergency medicine"
    jurisdiction: Optional[str] = None       # country of licensure
    years_post_registration: Optional[int] = None
    attestation_on_file: bool = False        # signed, dated, held outside this repository
    attestation_date: Optional[str] = None   # ISO date of the signed attestation
    anonymous_to_readers: bool = True
    notes: Optional[str] = None

    @property
    def credential_line(self) -> str:
        """How this adjudicator is described in the paper and the public record."""
        bits = [self.specialty or "specialty not recorded"]
        if self.jurisdiction:
            bits.append("licensed in %s" % self.jurisdiction)
        if self.years_post_registration:
            bits.append("%d years post-registration" % self.years_post_registration)
        return ", ".join(bits)


#: Registered adjudicators, keyed by the pseudonym that appears in ``Band.adjudicated_by``.
#:
#: ``adjudicator-01`` performed the review recorded in
#: ``docs/BAND_ADJUDICATION_RECORD.md``. She has agreed to be named to the editor but not to
#: readers. Her specialty, jurisdiction and signed attestation are pending, so
#: ``attestation_on_file`` is False and every band citing her is refused
#: ``clinician-adjudicated`` until that changes. The verdicts are recorded in the public
#: record meanwhile; they are simply not yet load-bearing.
ADJUDICATORS = {
    "adjudicator-01": Adjudicator(
        pseudonym="adjudicator-01",
        specialty="geriatrics",
        jurisdiction="Australia",
        attestation_on_file=False,
        anonymous_to_readers=True,
        notes="Performed the four-band review in docs/BAND_ADJUDICATION_RECORD.md. Consented "
              "to disclosure of name, credentials and location to the journal, and to "
              "anonymity in the published paper; her identity is held by the corresponding "
              "author. Specialty and jurisdiction recorded; the signed attestation is NOT yet "
              "on file, so the guard still refuses this identifier and no band may be marked "
              "clinician-adjudicated. "
              "SCOPE: geriatrics covers the discharge follow-up and referral bands but not the "
              "two emergency-department bands. scope_warning() fires on esi_acuity and "
              "analgesia_tier, and a second rater from emergency medicine is needed for those "
              "before either can be signed.",
    ),
}


def attribution_problem(identifier) -> Optional[str]:
    """Why ``identifier`` cannot support a ``clinician-adjudicated`` band, or None if it can.

    Anonymity is fine. Unattested anonymity is not, and the difference is exactly whether a
    signed attestation exists that an editor could be shown.
    """
    if not isinstance(identifier, str):
        return "must be a string"
    name = identifier.strip()
    if not name:
        return "is empty"
    who = ADJUDICATORS.get(name)
    if who is None:
        return ("is not a registered adjudicator; add an entry to ADJUDICATORS recording the "
                "credential and attestation status before a band cites this identifier")
    if not who.attestation_on_file:
        return ("is registered but has no attestation on file; a signed, dated attestation "
                "naming the adjudicator must be held by the corresponding author and be "
                "producible to the editor before this identifier can support a "
                "clinician-adjudicated band")
    if not who.specialty:
        return "is attested but records no specialty, so band-to-scope fit cannot be checked"
    return None


def attribution_problems(identifiers) -> list:
    """Every problem across a band's ``adjudicated_by`` list, as (identifier, problem)."""
    out = []
    for ident in identifiers or []:
        problem = attribution_problem(ident)
        if problem:
            out.append((ident, problem))
    return out


def scope_warning(specialty, sub_action):
    """Flag a band whose clinical domain sits outside the adjudicator's specialty.

    A single adjudicator rarely covers every band in this set, and the mismatch is not always
    the obvious one. An earlier version of this function knew about exactly one pairing --
    emergency medicine against the discharge follow-up band -- and therefore passed a
    geriatrician adjudicating emergency-department triage acuity without comment, which is the
    case that actually arose.

    Each band is described by the practice setting it belongs to, and a specialty matches if it
    is one of the ones that setting is ordinarily staffed by. Anything else is warned about.
    This is a warning rather than a refusal: whether to recruit a second rater is the
    corresponding author's decision, not this module's.
    """
    if not specialty:
        return "adjudicator specialty not recorded, so scope fit cannot be assessed"
    spec = specialty.lower()

    #: What each band's decision actually requires, and who ordinarily makes it.
    REQUIREMENTS = {
        "esi_acuity": (
            "emergency-department triage acuity",
            ("emergency", "acute care", "triage nurse", "emergency nursing"),
        ),
        "analgesia_tier": (
            "emergency-department acute pain management",
            ("emergency", "acute care", "pain medicine", "anaesthe", "anesthe"),
        ),
        "followup_days": (
            "discharge follow-up interval after a resolving metabolic emergency",
            ("internal medicine", "endocrin", "diabet", "general medicine", "geriatric",
             "family medicine", "primary care"),
        ),
        "referral": (
            "discharge referral planning",
            ("internal medicine", "general medicine", "geriatric", "family medicine",
             "primary care", "emergency"),
        ),
    }

    entry = REQUIREMENTS.get(sub_action)
    if entry is None:
        return None
    setting, accepted = entry
    if any(a in spec for a in accepted):
        return None
    return ("%s is a judgement in %s; %r is outside the specialties that ordinarily make it, "
            "so a second rater from that setting is advisable for this band"
            % (sub_action, setting, specialty))


def scope_report(specialty, sub_actions):
    """Warnings for a whole band set, so coverage can be seen at a glance."""
    return {sa: scope_warning(specialty, sa) for sa in sub_actions}
