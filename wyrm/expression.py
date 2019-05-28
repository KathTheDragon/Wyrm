from dataclasses import dataclass
from typing import Tuple, Dict

# Temp
@dataclass
class Expression:
    @staticmethod
    def make(line):
        return Expression()

    def evaluate(self, *contexts):
        return

@dataclass
class String(Expression):
    string: str

    def evaluate(self, *contexts):
        return self.string

@dataclass
class ArgList:
    args: Tuple[str]
    kwargs: Dict[str, Expression]

    @staticmethod
    def make(line):
        return ArgList([], {})
