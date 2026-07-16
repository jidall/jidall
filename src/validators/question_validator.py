from __future__ import annotations

from collections import Counter
from models.assessment import Question
from profiles.rules import ProfileRules

NEGATIVE_COMMANDS = ("exceto", "incorreta", "incorreto", "não corresponde", "não é", "assinale a falsa")
CLUE_WORDS = ("sempre", "nunca", "somente", "apenas", "todos", "nenhum")
VALID_DIFFICULTIES = {"fácil", "média", "medio", "médio", "difícil"}
VALID_BLOOM = {"lembrar", "compreender", "aplicar", "analisar", "avaliar", "criar"}


class ValidationError(ValueError):
    pass


class QuestionValidator:
    def validate(self, questions: list[Question], rules: ProfileRules, expected_quantity: int | None = None) -> list[str]:
        messages: list[str] = []
        if expected_quantity is not None and len(questions) != expected_quantity:
            messages.append(f"Quantidade gerada ({len(questions)}) difere da solicitada ({expected_quantity}).")
        answers: list[str] = []
        objective_questions = [question for question in questions if question.kind == "objetiva"]
        for index, question in enumerate(questions, start=1):
            if len(question.introduction) < rules.min_introduction_chars:
                messages.append(f"Questão {index}: introdução abaixo de {rules.min_introduction_chars} caracteres.")
            if any(term in question.command.lower() for term in NEGATIVE_COMMANDS):
                messages.append(f"Questão {index}: comando negativo detectado.")
            if question.kind == "objetiva":
                self._validate_objective(index, question, rules, messages, answers)
            if question.difficulty and question.difficulty.lower() not in VALID_DIFFICULTIES:
                messages.append(f"Questão {index}: dificuldade inválida ou não padronizada.")
            if rules.requires_bloom and (not question.bloom_taxonomy or question.bloom_taxonomy.lower() not in VALID_BLOOM):
                messages.append(f"Questão {index}: Taxonomia de Bloom ausente ou inválida.")
            if rules.requires_plan_competences and (not question.competence or not question.skill):
                messages.append(f"Questão {index}: competência/habilidade obrigatória ausente.")
            if not question.source_snippets:
                messages.append(f"Questão {index}: nenhum trecho rastreável associado à questão.")
            if not question.reference:
                messages.append(f"Questão {index}: referência ausente.")
            elif rules.reference_format == "Referência: Aula X." and not question.reference.startswith("Referência: Aula"):
                messages.append(f"Questão {index}: referência fora do formato 'Referência: Aula X.'.")
        self._validate_answer_distribution(answers, rules, messages)
        self._validate_difficulty_distribution(objective_questions, rules, messages)
        return messages

    def _validate_objective(self, index: int, question: Question, rules: ProfileRules, messages: list[str], answers: list[str]) -> None:
        if len(question.alternatives) != rules.objective_alternatives:
            messages.append(f"Questão {index}: quantidade de alternativas inválida.")
        labels = [alt.label for alt in question.alternatives]
        if labels and labels != list(rules.objective_labels):
            messages.append(f"Questão {index}: alternativas devem seguir {', '.join(rules.objective_labels)}.")
        correct = [alt for alt in question.alternatives if alt.is_correct]
        if len(correct) != 1:
            messages.append(f"Questão {index}: deve haver uma única alternativa correta.")
        else:
            answers.append(correct[0].label)
        for alt in question.alternatives:
            if not alt.justification:
                messages.append(f"Questão {index}: alternativa {alt.label} sem justificativa.")
            if any(word in alt.text.lower() for word in CLUE_WORDS):
                messages.append(f"Questão {index}: alternativa {alt.label} contém possível pista óbvia ('sempre/nunca/apenas/etc.').")
        lengths = [len(alt.text) for alt in question.alternatives]
        if lengths and min(lengths) > 0 and max(lengths) / min(lengths) > 2.2:
            messages.append(f"Questão {index}: alternativas com tamanhos muito diferentes.")

    def _validate_answer_distribution(self, answers: list[str], rules: ProfileRules, messages: list[str]) -> None:
        if answers:
            counts = Counter(answers)
            values = [counts.get(label, 0) for label in rules.objective_labels]
            if max(values) - min(values) > max(2, len(answers) // 3):
                messages.append("Distribuição de gabaritos possivelmente desequilibrada.")

    def _validate_difficulty_distribution(self, questions: list[Question], rules: ProfileRules, messages: list[str]) -> None:
        if not rules.difficulty_distribution or not questions:
            return
        counts = Counter((question.difficulty or "").lower() for question in questions)
        for difficulty, expected in rules.difficulty_distribution.items():
            if counts.get(difficulty, 0) != expected:
                messages.append(f"Distribuição de dificuldade inválida para {difficulty}: esperado {expected}, obtido {counts.get(difficulty, 0)}.")
