"""Unit tests for the risk scoring methodology.

These tests are the specification. If the methodology changes, they change
first, and the documented figures in docs/risk-methodology.md must match.
"""

from decimal import Decimal

import pytest

from app.models.enums import ImplementationStatus, RiskRating
from app.services.scoring import (
    ControlContribution,
    ScoringError,
    aggregate_effectiveness,
    calculate_risk,
    inherent_risk_score,
    rating_for_score,
    residual_risk_score,
    validate_effectiveness,
)


class TestInherentRisk:
    @pytest.mark.parametrize(
        ("likelihood", "impact", "expected"),
        [(1, 1, 1), (5, 5, 25), (4, 5, 20), (3, 3, 9), (2, 5, 10)],
    )
    def test_score_is_likelihood_times_impact(self, likelihood, impact, expected):
        assert inherent_risk_score(likelihood, impact) == expected

    @pytest.mark.parametrize(("likelihood", "impact"), [(0, 3), (6, 3), (3, 0), (3, 6), (-1, 2)])
    def test_rejects_out_of_scale_values(self, likelihood, impact):
        with pytest.raises(ScoringError):
            inherent_risk_score(likelihood, impact)

    def test_rejects_non_integer(self):
        with pytest.raises(ScoringError):
            inherent_risk_score(3.5, 2)  # type: ignore[arg-type]


class TestRatingBands:
    @pytest.mark.parametrize(
        ("score", "expected"),
        [
            (1, RiskRating.LOW),
            (4, RiskRating.LOW),
            (5, RiskRating.MEDIUM),
            (9, RiskRating.MEDIUM),
            (10, RiskRating.HIGH),
            (16, RiskRating.HIGH),
            (17, RiskRating.CRITICAL),
            (25, RiskRating.CRITICAL),
        ],
    )
    def test_boundaries(self, score, expected):
        """Every band edge is asserted: off-by-one errors here would
        silently misreport severity across the whole register."""
        assert rating_for_score(score) == expected

    @pytest.mark.parametrize("score", [0, 26, -5])
    def test_rejects_impossible_scores(self, score):
        with pytest.raises(ScoringError):
            rating_for_score(score)


class TestEffectivenessValidation:
    def test_implemented_accepts_high_effectiveness(self):
        validate_effectiveness(ImplementationStatus.IMPLEMENTED, Decimal("0.90"))

    def test_implemented_rejects_low_effectiveness(self):
        with pytest.raises(ScoringError):
            validate_effectiveness(ImplementationStatus.IMPLEMENTED, Decimal("0.30"))

    def test_partial_accepts_mid_range(self):
        validate_effectiveness(ImplementationStatus.PARTIALLY_IMPLEMENTED, Decimal("0.65"))

    def test_partial_rejects_implemented_range(self):
        with pytest.raises(ScoringError):
            validate_effectiveness(
                ImplementationStatus.PARTIALLY_IMPLEMENTED, Decimal("0.85")
            )

    def test_not_implemented_must_be_zero(self):
        validate_effectiveness(ImplementationStatus.NOT_IMPLEMENTED, Decimal("0.00"))
        with pytest.raises(ScoringError):
            validate_effectiveness(ImplementationStatus.NOT_IMPLEMENTED, Decimal("0.20"))

    def test_not_applicable_is_unconstrained(self):
        validate_effectiveness(ImplementationStatus.NOT_APPLICABLE, Decimal("0.00"))
        validate_effectiveness(ImplementationStatus.NOT_APPLICABLE, Decimal("1.00"))


class TestAggregation:
    def test_no_controls_gives_zero(self):
        assert aggregate_effectiveness([]) == Decimal("0.00")

    def test_single_control_passes_through(self):
        result = aggregate_effectiveness([ControlContribution(Decimal("0.70"))])
        assert result == Decimal("0.70")

    def test_two_controls_use_complementary_product(self):
        """0.70 and 0.50 -> 1 - (0.30 x 0.50) = 0.85."""
        result = aggregate_effectiveness(
            [ControlContribution(Decimal("0.70")), ControlContribution(Decimal("0.50"))]
        )
        assert result == Decimal("0.85")

    def test_layering_beats_the_strongest_single_control(self):
        strongest = Decimal("0.70")
        layered = aggregate_effectiveness(
            [ControlContribution(strongest), ControlContribution(Decimal("0.40"))]
        )
        assert layered > strongest

    def test_adding_a_weak_control_never_reduces_effectiveness(self):
        """The property that rules out averaging as the aggregation method."""
        strong_only = aggregate_effectiveness([ControlContribution(Decimal("0.90"))])
        with_weak = aggregate_effectiveness(
            [ControlContribution(Decimal("0.90")), ControlContribution(Decimal("0.10"))]
        )
        assert with_weak >= strong_only

    def test_weight_reduces_a_controls_contribution(self):
        full = aggregate_effectiveness([ControlContribution(Decimal("0.80"))])
        partial = aggregate_effectiveness(
            [ControlContribution(Decimal("0.80"), Decimal("0.50"))]
        )
        assert partial < full
        assert partial == Decimal("0.40")

    def test_effectiveness_is_capped_below_one(self):
        """Even three perfect controls cannot eliminate the risk."""
        result = aggregate_effectiveness(
            [ControlContribution(Decimal("1.00")) for _ in range(3)]
        )
        assert result == Decimal("0.95")

    def test_rejects_out_of_range_weight(self):
        with pytest.raises(ScoringError):
            aggregate_effectiveness([ControlContribution(Decimal("0.50"), Decimal("1.50"))])


class TestResidualRisk:
    def test_documented_worked_example(self):
        """Inherent 20 at 50% effectiveness gives 10, as stated in the docs."""
        assert residual_risk_score(20, Decimal("0.50")) == 10

    def test_no_controls_leaves_risk_unchanged(self):
        assert residual_risk_score(16, Decimal("0.00")) == 16

    def test_residual_never_reaches_zero(self):
        assert residual_risk_score(2, Decimal("0.95")) == 1

    def test_rounds_half_up_not_bankers(self):
        """21 x (1 - 0.50) = 10.5 must give 11, not Python's default 10."""
        assert residual_risk_score(21, Decimal("0.50")) == 11

    def test_rejects_effectiveness_above_one(self):
        with pytest.raises(ScoringError):
            residual_risk_score(10, Decimal("1.50"))


class TestEndToEnd:
    def test_unmitigated_critical_risk_stays_critical(self):
        result = calculate_risk(likelihood=5, impact=5)
        assert result.inherent_score == 25
        assert result.inherent_rating == RiskRating.CRITICAL
        assert result.residual_score == 25
        assert result.residual_rating == RiskRating.CRITICAL
        assert result.risk_reduction == 0

    def test_layered_controls_downgrade_the_rating(self):
        result = calculate_risk(
            likelihood=4,
            impact=5,
            contributions=[
                ControlContribution(Decimal("0.70")),
                ControlContribution(Decimal("0.50")),
            ],
        )
        assert result.inherent_score == 20
        assert result.inherent_rating == RiskRating.CRITICAL
        assert result.aggregate_effectiveness == Decimal("0.85")
        assert result.residual_score == 3
        assert result.residual_rating == RiskRating.LOW
        assert result.risk_reduction == 17

    def test_ineffective_control_barely_moves_the_score(self):
        """The central claim of the project: a control that exists but does
        not work leaves the risk substantially where it was."""
        result = calculate_risk(
            likelihood=4,
            impact=4,
            contributions=[ControlContribution(Decimal("0.10"))],
        )
        assert result.inherent_score == 16
        assert result.residual_score == 14
        assert result.residual_rating == RiskRating.HIGH