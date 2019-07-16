from dataclasses import dataclass
from typing import Tuple, Dict
import re

## Constants
STRING = r'([^\\\n]|\\.)*?'
TOKENS = {
    'OPERATOR': r'[-+@&|^~.]|[<>!=]?=|[*/<>]{1,2}',
    'COLON': r':',
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
                raise CompilerError(f'unmatched bracket: `{value}` @ {linenum}:{column}')
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
