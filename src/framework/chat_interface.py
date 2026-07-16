from __future__ import annotations

from framework.content_analyzer import ContentAnalysis


class ChatInterface:
    """CHAT_INTERFACE adapter used by the desktop app to present framework messages."""

    def summarize_analysis(self, analysis: ContentAnalysis) -> str:
        return analysis.summary
