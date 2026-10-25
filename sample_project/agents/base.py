"""Agent 基类。"""
from abc import ABC, abstractmethod


class BaseAgent(ABC):
    name = "base"

    @abstractmethod
    def run(self, *args, **kwargs):
        raise NotImplementedError
