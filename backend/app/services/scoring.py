"""Risk scoring methodology.

Pure functions only: no database access, no framework types. Every number the
platform reports about risk originates here, so the methodology can be unit
tested in isolation and explained without reference to the web layer.

Methodology summary
-------------------
Inherent risk    likelihood (1-5) x impact (1-5), giving 1-25
Rating bands     1-4 Low, 5-9 Medium, 10-16 High, 17-25 Critical
Control effect.  0.00-1.00 per control, constrained by implementation status
Aggregation      complementary product across all linked controls
Residual risk    inherent x (1 - aggregate effectiveness), floored at 1
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from app.models.enums import ImplementationStatus, RiskRating

MIN_SCALE = 1
MAX_SCALE = 5

# Upper bound on aggregate control effectiveness. No combination of controls
# can reduce a risk to zero: residual risk always remains. Capping at 0.95
# encodes that principle numerically instead of leaving it as a footnote.
MAX_AGGREGATE_EFFECTIVENESS = Decimal("0.95")

# Effectiveness a single control may be credited with, given its assessed
# implementation status. An assessor cannot record a control as Not
# Implemented and simultaneously claim it is 90% effective.
STATUS_EFFECTIVENESS_BOUNDS: dict[ImplementationStatus, tuple[Decimal, Decimal] | None] = {
    ImplementationStatus.IMPLEMENTED: (Decimal("0.70"), Decimal("1.00")),
    ImplementationStatus.PARTIALLY_IMPLEMENTED: (Decimal("0.10"), Decimal("0.69")),
    ImplementationStatus.NOT_IMPLEMENTED: (Decimal("0.00"), Decimal("0.00")),
    # Not Applicable is excluded from aggregation entirely rather than scored
    # as zero. Scoring it zero would penalise a risk for a control that was
    # correctly judged irrelevant to it.
    ImplementationStatus.NOT_APPLICABLE: None,
}

RATING_BANDS: tuple[tuple[int, int, RiskRating], ...] = (
    (1, 4, RiskRating.LOW),
    (5, 9, RiskRating.MEDIUM),
    (10, 16, RiskRating.HIGH),
    (17, 25, RiskRating.CRITICAL),
)


class ScoringError(ValueError):
    """Raised when inputs fall outside the defined methodology."""


@dataclass(frozen=True)
class ControlContribution:
    """One control's mitigating contribution to one specific risk.

    effectiveness  how well the control works, from its latest assessment
    weight         how much of THIS risk the control addresses (0-1)

    The two are separate on purpose. A control can be highly effective in
    general and only marginally relevant to a particular risk.
    """

    effectiveness: Decimal
    weight: Decimal = Decimal("1.00")

    @property
    def contribution(self) -> Decimal:
        return self.effectiveness * self.weight


def _validate_scale(value: int, name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ScoringError(f"{name} must be an integer")
    if not MIN_SCALE <= value <= MAX_SCALE:
        raise ScoringError(f"{name} must be between {MIN_SCALE} and {MAX_SCALE}, got {value}")


def inherent_risk_score(likelihood: int, impact: int) -> int:
    """Inherent risk: the exposure before any control credit is applied."""
    _validate_scale(likelihood, "likelihood")
    _validate_scale(impact, "impact")
    return likelihood * impact


def rating_for_score(score: int) -> RiskRating:
    """Map a 1-25 score onto its severity band.

    Ratings are always derived, never stored. Persisting both a score and a
    rating invites the two to disagree, and a compliance tool whose own
    numbers contradict each other is worse than no tool.
    """
    if not MIN_SCALE <= score <= MAX_SCALE * MAX_SCALE:
        raise ScoringError(f"Score must be between 1 and 25, got {score}")
    for lower, upper, rating in RATING_BANDS:
        if lower <= score <= upper:
            return rating
    raise ScoringError(f"No rating band covers score {score}")


def validate_effectiveness(
    status: ImplementationStatus, effectiveness: Decimal
) -> None:
    """Reject effectiveness values that contradict the implementation status."""
    if not Decimal("0") <= effectiveness <= Decimal("1"):
        raise ScoringError("Effectiveness must be between 0.00 and 1.00")

    bounds = STATUS_EFFECTIVENESS_BOUNDS[status]
    if bounds is None:
        return

    lower, upper = bounds
    if not lower <= effectiveness <= upper:
        raise ScoringError(
            f"Effectiveness {effectiveness} is inconsistent with status "
            f"'{status.value}' (expected {lower} to {upper})"
        )


def aggregate_effectiveness(contributions: list[ControlContribution]) -> Decimal:
    """Combine several controls into one effectiveness figure.

    Uses the complementary product:

        E = 1 - product(1 - e_i * w_i)

    Averaging would be wrong, since adding a weak control would lower the
    protection already provided by a strong one. Taking the maximum would be
    wrong too, since it discards defence in depth entirely. The complementary
    product treats each control as reducing the risk that survives the
    previous ones, which is how layered controls actually behave.

    Two controls at 0.70 and 0.50 give 1 - (0.30 x 0.50) = 0.85: better than
    either alone, and less than their sum.
    """
    if not contributions:
        return Decimal("0.00")

    surviving = Decimal("1.00")
    for item in contributions:
        if not Decimal("0") <= item.effectiveness <= Decimal("1"):
            raise ScoringError("Effectiveness must be between 0.00 and 1.00")
        if not Decimal("0") <= item.weight <= Decimal("1"):
            raise ScoringError("Weight must be between 0.00 and 1.00")
        surviving *= Decimal("1.00") - item.contribution

    effectiveness = Decimal("1.00") - surviving
    effectiveness = min(effectiveness, MAX_AGGREGATE_EFFECTIVENESS)
    return effectiveness.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def residual_risk_score(inherent_score: int, aggregate: Decimal) -> int:
    """Apply control credit to inherent risk.

        residual = inherent x (1 - aggregate effectiveness)

    Floored at 1. A risk that still exists cannot score zero, and a zero would
    also fall outside every rating band.

    ROUND_HALF_UP is used rather than Python's default banker's rounding so
    that a residual of 10.5 always becomes 11. Predictable, explainable
    rounding matters more here than statistical neutrality: a client
    recalculating by hand should get the same answer.
    """
    if not MIN_SCALE <= inherent_score <= MAX_SCALE * MAX_SCALE:
        raise ScoringError(f"Inherent score must be between 1 and 25, got {inherent_score}")
    if not Decimal("0") <= aggregate <= Decimal("1"):
        raise ScoringError("Aggregate effectiveness must be between 0.00 and 1.00")

    raw = Decimal(inherent_score) * (Decimal("1.00") - aggregate)
    rounded = int(raw.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    return max(1, rounded)


@dataclass(frozen=True)
class RiskCalculation:
    """The full, auditable result of scoring one risk."""

    likelihood: int
    impact: int
    inherent_score: int
    inherent_rating: RiskRating
    aggregate_effectiveness: Decimal
    residual_score: int
    residual_rating: RiskRating
    control_count: int

    @property
    def risk_reduction(self) -> int:
        return self.inherent_score - self.residual_score


def calculate_risk(
    *,
    likelihood: int,
    impact: int,
    contributions: list[ControlContribution] | None = None,
) -> RiskCalculation:
    """Score one risk end to end.

    With no linked controls the residual equals the inherent score. That is
    the correct answer, not a missing value: an unmitigated risk is carried
    at full exposure.
    """
    contributions = contributions or []
    inherent = inherent_risk_score(likelihood, impact)
    aggregate = aggregate_effectiveness(contributions)
    residual = residual_risk_score(inherent, aggregate)

    return RiskCalculation(
        likelihood=likelihood,
        impact=impact,
        inherent_score=inherent,
        inherent_rating=rating_for_score(inherent),
        aggregate_effectiveness=aggregate,
        residual_score=residual,
        residual_rating=rating_for_score(residual),
        control_count=len(contributions),
    )