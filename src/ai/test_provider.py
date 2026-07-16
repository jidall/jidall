from __future__ import annotations

from models.assessment import Alternative, Question, SourceDocument, SourceSnippet, ThemeMap
from profiles.rules import ProfileRules


class TestQuestionProvider:
    """Local MVP provider used when the user has not configured an API key."""

    def generate_questions(self, *, documents: list[SourceDocument], theme_map: ThemeMap, rules: ProfileRules, quantity: int, operation: str, retrieved_context: list[list[SourceSnippet]] | None = None, only_selected_materials: bool = True) -> list[Question]:
        questions: list[Question] = []
        themes = theme_map.themes or [theme_map.aula]
        for index in range(quantity):
            theme = themes[index % len(themes)]
            intro = (f"Com base nos materiais selecionados para {theme_map.aula}, considere o tema {theme}. " * 6).strip()
            labels = rules.objective_labels
            alternatives = [
                Alternative(label=label, text=f"Afirmação {label} relacionada ao tema {theme} conforme os materiais analisados.", is_correct=(alt_index == index % len(labels)), justification="Justificativa de teste gerada localmente para validar o documento Word.")
                for alt_index, label in enumerate(labels)
            ]
            source_snippets = retrieved_context[index] if retrieved_context and index < len(retrieved_context) else []
            questions.append(Question(
                kind="objetiva",
                introduction=intro,
                category="disciplinar",
                command="Assinale a alternativa correta.",
                alternatives=alternatives,
                reference=f"Referência: {theme_map.aula}.",
                difficulty="média",
                bloom_taxonomy="Compreender" if rules.requires_bloom else None,
                source_snippets=source_snippets,
            ))
        return questions
