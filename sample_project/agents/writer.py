"""写作 Agent：根据事实生成短文。"""
from agents.base import BaseAgent


class WriterAgent(BaseAgent):
    name = "writer"

    def run(self, state):
        return self.write(state)

    def write(self, state) -> str:
        lines = [f"# {state.topic}", ""]
        lines += [f"- {fact}" for fact in state.facts]
        return "\n".join(lines)
