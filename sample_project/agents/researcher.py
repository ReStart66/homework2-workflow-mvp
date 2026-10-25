"""研究员 Agent：整理与主题相关的事实。"""
from agents.base import BaseAgent


class ResearcherAgent(BaseAgent):
    name = "researcher"

    def run(self, state):
        return self.research(state)

    def research(self, state) -> list:
        return [f"{state.topic} 是一个研究主题。", "该主题仍在快速演进中。"]
