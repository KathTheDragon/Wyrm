from dataclasses import dataclass
from typing import Tuple, Dict
import re

## Constants
STRING = r'([^\\\n]|\\.)*?'
TOKENS = {
    'OPERATOR': r'[-+@&|^~]|[<>!=]?=|[*/<>]{1,2}',
    'COLON': r':',
    'DOT': r'\.',
    'COMMA': r',',
    'LBRACKET': r'[([{]',
    'RBRACKET': r'[}\])]',
    'IDENTIFIER': r'[a-zA-Z_]\w*',
    'STRING': fr'\'{STRING}\'|\"{STRING}\"',
    'NUMBER': r'\d+\.?\d*',
    'WHITESPACE': r' +',
    'UNKNOWN': r'.'
}
TOKEN_REGEX = re.compile('|'.join(f'(?P<{type}>{regex})' for type, regex in TOKENS.items()))
KEYWORDS = [
    'False',
    'None',
    'True',
    'and',
    'elif',
    'else',
    'for',
    'if',
    'in',
    'is',
    'lambda',
    'not',
    'only',
    'or',
    'with',
]

## Exceptions
class CompilerError(Exception):
    pass

class ExpressionError(Exception):
    pass

## Classes
@dataclass
class VarList:
    vars: Tuple[str]

    @staticmethod
    def make(tokens):
        pass

    def __iter__(self):
        return iter(self.vars)

@dataclass
class VarDict:
    vars: Dict[str, Expression]

    @staticmethod
    def make(tokens):
        pass

    def evaluate(self, *contexts):
        return {var: expr.evaluate(*contexts) for var, expr in self.vars.items()}

@dataclass
class Expression:
    @staticmethod
    def make(tokens):
        return Expression()

    def evaluate(self, *contexts):
        return

@dataclass
class Literal(Expression):
    @classmethod
    def make(cls, tokens):
        name = cls.__name__.lower()
        if len(tokens) != 1:
            raise ExpressionError(f'{name}s can only take a single token')
        token = tokens[0]
        if token.type == name.upper():
            return cls(token.value)
        else:
            raise ExpressionError(f'{name}s take a token of type {name.upper()!r}, not {token.type!r}')

@dataclass
class Identifier(Literal):
    name: str

    def evaluate(self, *contexts):
        name = self.name
        for context in contexts:
            if name in context:
                return context[name]

re_slashes = re.compile(r'(\\+)\1')
re_format = re.compile(r'(\\?){(.*?)}')

@dataclass
class String(Literal):
    string: str

    def evaluate(self, *contexts):
        strings = re_slashes.split(self.string)
        for i, string in enumerate(strings):
            strings[i] = re_format.sub(lambda m: string_format(m, *contexts), string)
        return ''.join(strings)

@dataclass
class Number(Literal):
    number: float

    def __init__(self, number):
        if '.' in number:
            self.number = float(number)
        else:
            self.number = int(number)

    def evaluate(self, *contexts):
        return self.number

@dataclass

    @staticmethod
    def make(tokens):
        pass

## Functions
def tokenise(string, linenum=0, colstart=0):  # Perhaps I might enforce expression structure here
    from .compiler import Token, CompilerError
    brackets = []
    for match in TOKEN_REGEX.finditer(string):
        type = match.lastgroup
        value = match.group()
        column = match.start() + colstart
        if type == 'COLON':
            if not brackets:  # Inline operator
                break
        elif type == 'LBRACKET':
            brackets.append(value)
        elif type == 'RBRACKET':
            if not brackets:
                raise CompilerError(f'unexpected bracket: `{value}` @ {linenum}:{column}')
            bracket = brackets.pop()
            if bracket+value not in ('()', '[]', '{}'):
                raise CompilerError(f'mismatched brackets: `{value}` @ {linenum}:{column}')
        elif type == 'IDENTIFIER':
            if value in KEYWORDS:
                type = 'KEYWORD'
        elif type == 'WHITESPACE':
            continue
        elif type == 'UNKNOWN':
            if not brackets:  # Probably a newline
                break
            raise CompilerError(f'unexpected character: `{value}` @ {linenum}:{column}')
        yield Token(type, value, linenum, column)
    else:
        if brackets:
            raise CompilerError(f'unclosed bracket `{brackets[-1]}` @ {linenum}:_')
        yield Token('END', '', linenum, match.end()+colstart)
        return
    yield Token('END', '', linenum, column)
