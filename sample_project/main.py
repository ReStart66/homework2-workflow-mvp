"""Demo agent 项目：Simple Research Assistant。

这是一个供 Homework 2 Workflow 分析的最小代码仓库，
用于演示“代码 -> 分析 -> 文档”的文档生成流程。
"""
from agents.researcher import ResearcherAgent
from agents.writer import WriterAgent
from state import WorkflowState


def run(topic: str) -> str:
    """执行一次简单的研究任务。"""
    state = WorkflowState(topic=topic)
    researcher = ResearcherAgent()
    writer = WriterAgent()

    facts = researcher.research(state)
    state.facts = facts
    return writer.write(state)


if __name__ == "__main__":
    print(run("quantum computing"))
