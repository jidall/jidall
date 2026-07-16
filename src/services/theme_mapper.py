from __future__ import annotations

import re
from collections import defaultdict
from models.assessment import SourceDocument, ThemeMap

_THEME_RE = re.compile(r"\b(?:tema|unidade|cap[íi]tulo|aula)\s+\d+[:\-–]?\s*(.{0,90})", re.I)


class ThemeMapper:
    def build(self, documents: list[SourceDocument], aula: str) -> ThemeMap:
        themes: list[str] = []
        page_index: dict[str, list[int]] = defaultdict(list)
        by_type: dict[str, set[str]] = defaultdict(set)
        for doc in documents:
            for page in doc.pages:
                if page.theme and page.theme not in themes:
                    themes.append(page.theme)
                    page_index[page.theme].append(page.page_number)
                    by_type[doc.document_type].add(page.theme)
                text = page.text.replace("\n", " ")
                for match in _THEME_RE.finditer(text):
                    title = match.group(0).strip()[:120]
                    if title and title not in themes:
                        themes.append(title)
                    if title:
                        page_index[title].append(page.page_number)
                        by_type[doc.document_type].add(title)
        if not themes:
            keywords = self._keywords(" ".join(p.text for d in documents for p in d.pages))
            themes = keywords or [f"Conteúdos identificados na {aula}"]
        divergences = []
        if "texto da aula" in by_type and "slides" in by_type:
            only_text = by_type["texto da aula"] - by_type["slides"]
            only_slides = by_type["slides"] - by_type["texto da aula"]
            if only_text:
                divergences.append("Temas encontrados apenas no texto: " + "; ".join(sorted(only_text)[:10]))
            if only_slides:
                divergences.append("Temas encontrados apenas nos slides: " + "; ".join(sorted(only_slides)[:10]))
        return ThemeMap(aula=aula, themes=themes[:30], divergences=divergences, page_index=dict(page_index))

    def _keywords(self, text: str) -> list[str]:
        words = re.findall(r"[A-Za-zÀ-ÿ]{5,}", text.lower())
        stop = {"sobre", "aula", "para", "como", "entre", "pode", "mais", "esta", "este", "serão", "foram", "pelos", "pelas"}
        counts: dict[str, int] = {}
        for word in words:
            if word not in stop:
                counts[word] = counts.get(word, 0) + 1
        return [w.title() for w, _ in sorted(counts.items(), key=lambda item: item[1], reverse=True)[:12]]
