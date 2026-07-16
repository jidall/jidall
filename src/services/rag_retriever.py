from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from models.assessment import SourceDocument, SourceSnippet, ThemeMap

_WORD_RE = re.compile(r"[A-Za-zÀ-ÿ0-9]{3,}")
STOPWORDS = {"para", "com", "uma", "que", "das", "dos", "por", "aula", "tema", "como", "mais", "ser", "são", "não", "seu", "sua", "nas", "nos", "entre"}


@dataclass(frozen=True)
class RetrievalPlan:
    snippets_by_question: list[list[SourceSnippet]]
    concepts: list[str]
    possible_student_errors: list[str]


class RagRetriever:
    def build_plan(self, documents: list[SourceDocument], theme_map: ThemeMap, question_count: int, snippets_per_question: int = 4) -> RetrievalPlan:
        snippets = self._snippets(documents)
        concepts = self._concepts(snippets)
        errors = [f"Confundir {concept} com conceitos próximos do material" for concept in concepts[:6]]
        queries = theme_map.themes or concepts or [theme_map.aula]
        snippets_by_question: list[list[SourceSnippet]] = []
        for index in range(question_count):
            query = queries[index % len(queries)]
            snippets_by_question.append(self.retrieve(snippets, query, snippets_per_question))
        return RetrievalPlan(snippets_by_question, concepts, errors)

    def retrieve(self, snippets: list[SourceSnippet], query: str, limit: int = 4) -> list[SourceSnippet]:
        query_terms = self._terms(query)
        ranked = []
        for snippet in snippets:
            terms = self._terms(snippet.text + " " + (snippet.theme or ""))
            score = sum(terms.get(term, 0) for term in query_terms)
            if snippet.theme and any(term in snippet.theme.lower() for term in query_terms):
                score += 2
            ranked.append(SourceSnippet(snippet.document_name, snippet.document_type, snippet.aula, snippet.theme, snippet.page_number, snippet.text, float(score)))
        ranked.sort(key=lambda item: item.score, reverse=True)
        return ranked[:limit]

    def _snippets(self, documents: list[SourceDocument], max_chars: int = 1400) -> list[SourceSnippet]:
        snippets: list[SourceSnippet] = []
        for doc in documents:
            for page in doc.pages:
                text = re.sub(r"\s+", " ", page.text).strip()
                for start in range(0, max(len(text), 1), max_chars):
                    chunk = text[start:start + max_chars].strip()
                    if chunk:
                        snippets.append(SourceSnippet(page.file_name, page.document_type, page.aula, page.theme, page.page_number, chunk))
        return snippets

    def _concepts(self, snippets: list[SourceSnippet], limit: int = 20) -> list[str]:
        counts: Counter[str] = Counter()
        for snippet in snippets:
            counts.update(self._terms(snippet.text))
        return [term.title() for term, _ in counts.most_common(limit)]

    def _terms(self, text: str) -> Counter[str]:
        words = [word.lower() for word in _WORD_RE.findall(text)]
        return Counter(word for word in words if word not in STOPWORDS)
