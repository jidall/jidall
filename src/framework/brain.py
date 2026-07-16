from __future__ import annotations

from models.assessment import GenerationRequest, ProfileName
from profiles.rules import get_profile_rules
from services.errors import MissingPlanError


class Brain:
    """BRAIN: applies high-level framework decisions before generation."""

    def decide_rules(self, request: GenerationRequest, document_types: set[str]):
        rules = get_profile_rules(request.profile)
        if request.profile == ProfileName.MARCO_REGULATORIO and rules.requires_plan_competences and "plano de ensino" not in document_types:
            raise MissingPlanError("Marco Regulatório exige Plano de Ensino para extrair competências e habilidades.")
        return rules
