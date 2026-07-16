from __future__ import annotations

from dataclasses import dataclass
from models.assessment import Operation, ProfileName


@dataclass(frozen=True)
class ProfileRules:
    profile: ProfileName
    objective_alternatives: int
    objective_labels: tuple[str, ...]
    min_introduction_chars: int
    default_objective_count: int
    default_discursive_count: int
    requires_plan_competences: bool
    requires_bloom: bool
    difficulty_distribution: dict[str, int]
    category_distribution: dict[str, int]
    reference_format: str


GRADE_ANTIGA = ProfileRules(
    profile=ProfileName.GRADE_ANTIGA,
    objective_alternatives=5,
    objective_labels=("A", "B", "C", "D", "E"),
    min_introduction_chars=250,
    default_objective_count=10,
    default_discursive_count=5,
    requires_plan_competences=False,
    requires_bloom=True,
    difficulty_distribution={},
    category_distribution={"objetiva": 10, "discursiva": 5},
    reference_format="aula_tema_pagina",
)

MARCO_REGULATORIO = ProfileRules(
    profile=ProfileName.MARCO_REGULATORIO,
    objective_alternatives=4,
    objective_labels=("A", "B", "C", "D"),
    min_introduction_chars=250,
    default_objective_count=50,
    default_discursive_count=15,
    requires_plan_competences=True,
    requires_bloom=False,
    difficulty_distribution={"fácil": 15, "média": 20, "difícil": 15},
    category_distribution={"disciplinar": 20, "formação geral": 15, "interdisciplinar": 15, "discursiva": 15},
    reference_format="Referência: Aula X.",
)


def get_profile_rules(profile: ProfileName | str) -> ProfileRules:
    profile = ProfileName(profile)
    return GRADE_ANTIGA if profile == ProfileName.GRADE_ANTIGA else MARCO_REGULATORIO


def default_quantity(profile: ProfileName, operation: Operation) -> int:
    rules = get_profile_rules(profile)
    if operation == Operation.APENAS_OBJETIVAS:
        return rules.default_objective_count
    if operation == Operation.APENAS_DISCURSIVAS:
        return rules.default_discursive_count
    if operation == Operation.BANCO_COMPLETO and profile == ProfileName.MARCO_REGULATORIO:
        return 65
    return rules.default_objective_count + rules.default_discursive_count
